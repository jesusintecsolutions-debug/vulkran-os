"""VULKRAN OS — Content Engine models (video projects, templates, moments, renders, voiceovers)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class VideoTemplate(Base, TimestampMixin):
    """Remotion video template with slot schema — per-client or global."""

    __tablename__ = "video_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), index=True,
    )
    # null = global template, set = client-specific
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    # e.g. base, dossier, editorial, social, promo
    fps: Mapped[int] = mapped_column(Integer, default=30)
    width: Mapped[int] = mapped_column(Integer, default=1920)
    height: Mapped[int] = mapped_column(Integer, default=1080)
    duration_per_moment: Mapped[float] = mapped_column(Float, default=5.0)
    # default seconds per moment
    slots_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Array of SlotDefinition: [{key, type, label, required, default, options, min, max, group}]
    sfx_defaults: Mapped[dict | None] = mapped_column(JSONB)
    # {transition_sfx: "whoosh", background_music: "ambient_01"}
    tags: Mapped[list | None] = mapped_column(JSONB)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class VideoProject(Base, TimestampMixin):
    """A video project — collection of moments to be rendered."""

    __tablename__ = "video_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    brief: Mapped[str | None] = mapped_column(Text)
    # Creative brief / instructions
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft", index=True,
    )
    # draft | generating | review | rendering | done | error
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_templates.id"),
    )
    fps: Mapped[int] = mapped_column(Integer, default=30)
    width: Mapped[int] = mapped_column(Integer, default=1920)
    height: Mapped[int] = mapped_column(Integer, default=1080)
    render_url: Mapped[str | None] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    voiceover_url: Mapped[str | None] = mapped_column(String(500))
    # Final composed voiceover audio
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=None)
    # generation stats, model used, etc.

    moments: Mapped[list["VideoMoment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="VideoMoment.sort_order",
    )
    render_jobs: Mapped[list["RenderJob"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )


class VideoMoment(Base, TimestampMixin):
    """Individual moment/slide within a video project."""

    __tablename__ = "video_moments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_templates.id"),
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    slots_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Filled slot values: {headline: "...", bg_color: "#1a1a2e", ...}
    duration_frames: Mapped[int | None] = mapped_column(Integer)
    # null = use template default
    transition_type: Mapped[str] = mapped_column(String(30), default="fade")
    # fade, slide, wipe, flip, none
    transition_duration: Mapped[int] = mapped_column(Integer, default=15)
    # frames
    voiceover_text: Mapped[str | None] = mapped_column(Text)
    # Script text for this moment's voiceover
    voiceover_url: Mapped[str | None] = mapped_column(String(500))
    # Generated audio URL for this moment

    project: Mapped["VideoProject"] = relationship(back_populates="moments")


class RenderJob(Base, TimestampMixin):
    """Track render job status and output."""

    __tablename__ = "render_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending",
    )
    # pending | bundling | rendering | done | error
    progress: Mapped[int] = mapped_column(Integer, default=0)
    # 0-100
    quality: Mapped[str] = mapped_column(String(10), default="1080p")
    error_message: Mapped[str | None] = mapped_column(Text)
    output_path: Mapped[str | None] = mapped_column(String(500))
    output_filename: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["VideoProject"] = relationship(back_populates="render_jobs")


class VoiceoverJob(Base, TimestampMixin):
    """Track TTS voiceover generation jobs."""

    __tablename__ = "voiceover_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    moment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_moments.id", ondelete="SET NULL"),
    )
    # null = full project voiceover, set = per-moment
    text: Mapped[str] = mapped_column(Text, nullable=False)
    voice_name: Mapped[str] = mapped_column(String(100), nullable=False, default="es-ES-Wavenet-B")
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, default="es-ES")
    speaking_rate: Mapped[float] = mapped_column(Float, default=1.0)
    pitch: Mapped[float] = mapped_column(Float, default=0.0)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending",
    )
    # pending | generating | done | error
    error_message: Mapped[str | None] = mapped_column(Text)


class TranscriptionJob(Base, TimestampMixin):
    """Track audio/video transcription jobs."""

    __tablename__ = "transcription_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="SET NULL"),
        index=True,
    )
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # path to audio/video file
    language: Mapped[str] = mapped_column(String(10), default="es")
    model_size: Mapped[str] = mapped_column(String(20), default="base")
    # tiny, base, small, medium, large
    segments: Mapped[dict | None] = mapped_column(JSONB)
    # [{start: 0.0, end: 2.5, text: "..."}, ...]
    full_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending",
    )
    # pending | processing | done | error
    error_message: Mapped[str | None] = mapped_column(Text)
