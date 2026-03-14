"""VULKRAN OS — Advanced CRM models (scoring, activities, drip campaigns)."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class LeadScore(Base, TimestampMixin):
    """Calculated lead score with factor breakdown."""

    __tablename__ = "lead_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 0-100
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {sector_match: 20, budget: 15, interactions: 10, recency: 25, source_quality: 10}
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Activity(Base, TimestampMixin):
    """CRM activity log (calls, emails, meetings, notes)."""

    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    activity_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )
    # call | email | meeting | note | task | follow_up
    description: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(50))
    # positive | neutral | negative | no_answer
    performed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DripCampaign(Base, TimestampMixin):
    """Automated drip campaign definition."""

    __tablename__ = "drip_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"),
    )
    trigger_stage: Mapped[str | None] = mapped_column(String(30))
    # When lead enters this stage, auto-enroll
    steps: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # [{step: 1, type: "email", template_id: "...", delay_hours: 0},
    #  {step: 2, type: "task", description: "Call lead", delay_hours: 48},
    #  {step: 3, type: "email", template_id: "...", delay_hours: 120}]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DripEnrollment(Base, TimestampMixin):
    """Track individual lead enrollment in a drip campaign."""

    __tablename__ = "drip_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drip_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active",
    )
    # active | paused | completed | cancelled
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
