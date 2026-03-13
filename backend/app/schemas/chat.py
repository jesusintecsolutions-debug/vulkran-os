"""VULKRAN OS — Chat and conversation schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None
    client_context: uuid.UUID | None = None  # active client for agent context


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message: str
    tool_calls: list[dict] | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    context: dict | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    tool_calls: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
