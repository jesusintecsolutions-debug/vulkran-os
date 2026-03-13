"""VULKRAN OS — Agent chat endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
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
