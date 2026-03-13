"""VULKRAN OS — Agent Core orchestrator.

Receives user messages, loads context, calls Claude with tools,
persists conversation history, and returns the final response.
"""

import uuid
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message
from app.models.base import utcnow
from app.services.llm_bridge import chat_with_tools, call_claude, extract_text
from app.services.agent_tools import TOOLS, ToolExecutor

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_system_prompt() -> str:
    path = PROMPTS_DIR / "agent_system.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "You are VULKRAN OS, an AI business operating system assistant. "
        "You help manage clients, generate content, track leads, and handle "
        "daily operations for a digital transformation agency. "
        "Always respond in the same language the user writes in. "
        "Be concise, professional, and action-oriented."
    )


async def process_message(
    db: AsyncSession,
    user_id: uuid.UUID,
    message: str,
    conversation_id: uuid.UUID | None = None,
    client_context_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, str, list[dict]]:
    """Process a user message through the agent pipeline.

    Returns (conversation_id, assistant_reply, tool_calls_made).
    """
    # 1. Get or create conversation
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            conversation = _new_conversation(user_id, client_context_id)
            db.add(conversation)
            await db.flush()
    else:
        conversation = _new_conversation(user_id, client_context_id)
        db.add(conversation)
        await db.flush()

    # 2. Load message history (last 20 messages for context window)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    history = list(reversed(result.scalars().all()))

    # 3. Build messages for Claude
    claude_messages = []
    for msg in history:
        claude_messages.append({"role": msg.role, "content": msg.content})
    claude_messages.append({"role": "user", "content": message})

    # 4. Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=message,
    )
    db.add(user_msg)

    # 5. Call Claude with tools
    system_prompt = _load_system_prompt()
    executor = ToolExecutor(db, user_id)

    reply, tool_calls = await chat_with_tools(
        messages=claude_messages,
        system=system_prompt,
        tools=TOOLS,
        tool_executor=executor.execute,
    )

    # 6. Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
        tool_calls=tool_calls if tool_calls else None,
    )
    db.add(assistant_msg)

    # 7. Auto-title conversation on first exchange
    if not conversation.title and len(history) == 0:
        conversation.title = message[:80]

    await db.flush()

    return conversation.id, reply, tool_calls


def _new_conversation(
    user_id: uuid.UUID, client_context_id: uuid.UUID | None
) -> Conversation:
    ctx = {}
    if client_context_id:
        ctx["active_client_id"] = str(client_context_id)
    return Conversation(
        user_id=user_id,
        context=ctx if ctx else None,
    )
