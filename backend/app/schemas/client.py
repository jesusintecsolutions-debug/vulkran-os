"""VULKRAN OS — Client schemas."""

import uuid
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    slug: str
    sector: str
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    brand_config: dict | None = None
    enabled_modules: list[str] = []
    monthly_fee: Decimal | None = None
    billing_day: int | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    sector: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    brand_config: dict | None = None
    enabled_modules: list[str] | None = None
    monthly_fee: Decimal | None = None
    billing_day: int | None = None
    notes: str | None = None
    status: str | None = None


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    sector: str
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    brand_config: dict | None
    enabled_modules: list[str] | None
    monthly_fee: Decimal | None
    billing_day: int | None
    notes: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
