"""VULKRAN OS — Content Engine models."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class ContentTemplate(Base, TimestampMixin):
    """Reusable content template (e.g. 'Instagram carousel', 'Blog post')."""

    __tablename__ = "content_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # instagram, youtube, linkedin, blog, email, twitter
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # post, carousel, reel_script, story, article, newsletter
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    schema_fields: Mapped[dict | None] = mapped_column(JSONB, default=None)
    # e.g. {"headline": "string", "body": "string", "cta": "string", "hashtags": "array"}
    visual_template: Mapped[str | None] = mapped_column(String(100))
    # Reference to Remotion/static template slug
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ContentBatch(Base, TimestampMixin):
    """A batch of content items generated for a client."""

    __tablename__ = "content_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    brief: Mapped[str | None] = mapped_column(Text)
    # User instructions / creative brief for this batch
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", index=True
    )  # draft | generating | review | approved | scheduled | published | failed
    platform: Mapped[str | None] = mapped_column(String(50))
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # user who triggered generation
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=None)
    # tokens used, model, generation time, etc.
    item_count: Mapped[int] = mapped_column(Integer, default=0)


class ContentItem(Base, TimestampMixin):
    """Individual content piece within a batch."""

    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_templates.id"),
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Order within batch (e.g. slide 1, 2, 3 in a carousel)
    content_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # The generated content: {"headline": "...", "body": "...", "cta": "...", ...}
    visual_url: Mapped[str | None] = mapped_column(String(500))
    # Path to generated image/video asset
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="generated"
    )  # generated | edited | approved | rejected
    edit_notes: Mapped[str | None] = mapped_column(Text)
    # User feedback on this specific item
