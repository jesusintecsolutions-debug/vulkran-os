"""VULKRAN OS — Lead/CRM models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Text, Integer, Numeric, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class Lead(Base, TimestampMixin):
    """A potential client in the sales pipeline."""

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(30))
    source: Mapped[str | None] = mapped_column(String(100))
    # web, referral, linkedin, cold_outreach, event, other
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="new", index=True
    )  # new | contacted | meeting | proposal | negotiation | won | lost
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id")
    )
    # Linked client once converted
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[dict | None] = mapped_column(JSONB, default=None)
    # e.g. ["marketing", "pyme", "urgente"]
    lost_reason: Mapped[str | None] = mapped_column(String(500))
    next_action: Mapped[str | None] = mapped_column(String(500))
    next_action_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeadActivity(Base):
    """Activity log for a lead (calls, emails, meetings, notes)."""

    __tablename__ = "lead_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # note, email_sent, email_received, call, meeting, proposal_sent, stage_change
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=None)
    # e.g. {"from_stage": "new", "to_stage": "contacted"} or {"email_subject": "..."}
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
