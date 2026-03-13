"""VULKRAN OS — Content Engine schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Templates ──

class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    platform: str
    content_type: str
    prompt_template: str
    schema_fields: dict | None = None
    visual_template: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str
    slug: str
    platform: str
    content_type: str
    prompt_template: str
    schema_fields: dict | None = None
    visual_template: str | None = None


# ── Batches ──

class BatchCreate(BaseModel):
    client_id: uuid.UUID
    title: str
    brief: str | None = None
    platform: str | None = None
    template_id: uuid.UUID | None = None
    item_count: int = 5


class BatchGenerateRequest(BaseModel):
    """Request to generate content for an existing batch."""
    template_id: uuid.UUID | None = None
    brief: str | None = None
    item_count: int = 5
    tone: str | None = None  # formal, casual, energetic, professional
    language: str = "es"


class BatchResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    brief: str | None = None
    status: str
    platform: str | None = None
    item_count: int
    scheduled_for: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Items ──

class ItemResponse(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    template_id: uuid.UUID | None = None
    position: int
    content_data: dict
    visual_url: str | None = None
    status: str
    edit_notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ItemUpdate(BaseModel):
    content_data: dict | None = None
    status: str | None = None
    edit_notes: str | None = None
