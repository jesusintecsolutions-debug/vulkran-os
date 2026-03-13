"""VULKRAN OS — Client and ClientUser models."""

import uuid
from decimal import Decimal

from sqlalchemy import String, Integer, Numeric, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(30))
    brand_config: Mapped[dict | None] = mapped_column(JSONB, default=None)
    enabled_modules: Mapped[list | None] = mapped_column(ARRAY(String), default=[])
    monthly_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    billing_day: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active | paused | churned


class ClientUser(Base):
    __tablename__ = "client_users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), primary_key=True
    )
    permissions: Mapped[list | None] = mapped_column(ARRAY(String), default=[])
