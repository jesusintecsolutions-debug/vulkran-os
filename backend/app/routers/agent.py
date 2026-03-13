"""VULKRAN OS — Agent chat endpoints (standard + SSE streaming)."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Conversation, Message
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.agent_core import process_message
from app.services.agent_core import _load_system_prompt, _new_conversation
from app.services.agent_tools import TOOLS, ToolExecutor
from app.services.llm_bridge import call_claude_stream

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a message to the agent and get a response."""
    try:
        conversation_id, reply, tool_calls = await process_message(
            db=db,
            user_id=user.id,
            message=body.message,
            conversation_id=body.conversation_id,
            client_context_id=body.client_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}") from e

    return ChatResponse(
        conversation_id=conversation_id,
        message=reply,
        tool_calls=tool_calls if tool_calls else None,
    )


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stream agent response via SSE.

    Events:
      data: {"type":"text_delta","text":"..."}
      data: {"type":"tool_call","name":"...","input":{}}
      data: {"type":"tool_result","name":"...","result":{}}
      data: {"type":"done","conversation_id":"...","full_text":"..."}
      data: {"type":"error","message":"..."}
    """

    async def event_generator():
        try:
            # 1. Get or create conversation
            if body.conversation_id:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == body.conversation_id)
                )
                conversation = result.scalar_one_or_none()
                if not conversation:
                    conversation = _new_conversation(user.id, body.client_context)
                    db.add(conversation)
                    await db.flush()
            else:
                conversation = _new_conversation(user.id, body.client_context)
                db.add(conversation)
                await db.flush()

            # 2. Load history
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(20)
            )
            history = list(reversed(result.scalars().all()))

            claude_messages = [
                {"role": msg.role, "content": msg.content} for msg in history
            ]
            claude_messages.append({"role": "user", "content": body.message})

            # Save user message
            db.add(Message(
                conversation_id=conversation.id,
                role="user",
                content=body.message,
            ))
            await db.flush()

            system_prompt = _load_system_prompt()
            executor = ToolExecutor(db, user.id)
            all_tool_calls = []
            full_text = ""

            # Multi-turn tool loop with streaming
            for _round in range(10):
                tool_calls_this_round = []

                async for event in call_claude_stream(
                    messages=claude_messages,
                    system=system_prompt,
                    tools=TOOLS,
                ):
                    if event["type"] == "text_delta":
                        full_text += event["text"]
                        yield f"data: {json.dumps(event)}\n\n"

                    elif event["type"] == "tool_use":
                        tool_calls_this_round.append(event)
                        yield f"data: {json.dumps({'type': 'tool_call', 'name': event['name'], 'input': event['input']})}\n\n"

                    elif event["type"] == "message_stop":
                        pass  # handled below

                # If no tools were called, we're done
                if not tool_calls_this_round:
                    break

                # Execute tools and feed results back
                all_tool_calls.extend(tool_calls_this_round)
                assistant_content = []
                if full_text:
                    assistant_content.append({"type": "text", "text": full_text})
                for tc in tool_calls_this_round:
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                    })

                claude_messages.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for tc in tool_calls_this_round:
                    result_data = await executor.execute(tc["name"], tc["input"])
                    result_str = result_data if isinstance(result_data, str) else json.dumps(result_data)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": result_str,
                    })
                    yield f"data: {json.dumps({'type': 'tool_result', 'name': tc['name'], 'result': result_data})}\n\n"

                claude_messages.append({"role": "user", "content": tool_results})
                full_text = ""  # Reset for next round

            # Save assistant message
            db.add(Message(
                conversation_id=conversation.id,
                role="assistant",
                content=full_text,
                tool_calls=all_tool_calls if all_tool_calls else None,
            ))

            if not conversation.title and len(history) == 0:
                conversation.title = body.message[:80]

            await db.flush()

            yield f"data: {json.dumps({'type': 'done', 'conversation_id': str(conversation.id), 'full_text': full_text})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 20,
):
    """List user's recent conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
):
    """Get messages for a conversation."""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()
