"""VULKRAN OS — Lead/CRM schemas."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class LeadCreate(BaseModel):
    name: str
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    source: str | None = None
    estimated_value: Decimal | None = None
    notes: str | None = None
    tags: list[str] | None = None


class LeadUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    source: str | None = None
    stage: str | None = None
    estimated_value: Decimal | None = None
    notes: str | None = None
    tags: list[str] | None = None
    lost_reason: str | None = None
    next_action: str | None = None
    next_action_date: datetime | None = None


class LeadResponse(BaseModel):
    id: uuid.UUID
    name: str
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    source: str | None = None
    stage: str
    owner_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    estimated_value: Decimal | None = None
    notes: str | None = None
    tags: dict | None = None
    lost_reason: str | None = None
    next_action: str | None = None
    next_action_date: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class StageChangeRequest(BaseModel):
    stage: str
    notes: str | None = None


class ActivityCreate(BaseModel):
    activity_type: str
    description: str
    metadata: dict | None = None


class ActivityResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    activity_type: str
    description: str
    metadata_: dict | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineStats(BaseModel):
    total_leads: int
    by_stage: dict[str, int]
    total_value: Decimal | None = None
    won_this_month: int
    lost_this_month: int
