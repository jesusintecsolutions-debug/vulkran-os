"""VULKRAN OS — Email system models (templates, sequences, tracking)."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class EmailTemplate(Base, TimestampMixin):
    """Reusable email template with variable placeholders."""

    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), index=True,
    )
    # null = global template
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_template: Mapped[str] = mapped_column(String(500), nullable=False)
    # e.g. "{{empresa}} - Propuesta de colaboracion"
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    # HTML with {{variable}} placeholders
    variables: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {nombre: "Contact name", empresa: "Company name", propuesta_url: "Proposal URL"}
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general",
    )
    # outreach | follow_up | proposal | invoice | report | notification
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EmailSequence(Base, TimestampMixin):
    """Step in an automated email sequence (linked to drip campaigns)."""

    __tablename__ = "email_sequences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drip_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id"),
        nullable=False,
    )
    delay_hours: Mapped[int] = mapped_column(Integer, default=0)
    # Hours after previous step
    conditions: Mapped[dict | None] = mapped_column(JSONB)
    # {skip_if_replied: true, skip_if_opened: false}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EmailLog(Base, TimestampMixin):
    """Track sent emails and their delivery/engagement status."""

    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    to_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    from_email: Mapped[str] = mapped_column(String(320), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id"),
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_preview: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="sent",
    )
    # sent | delivered | opened | clicked | bounced | failed
    resend_id: Mapped[str | None] = mapped_column(String(100))
    # Resend API message ID
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"),
    )
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drip_enrollments.id", ondelete="SET NULL"),
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
