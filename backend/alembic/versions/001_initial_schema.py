"""Initial schema — all VULKRAN OS models.

Revision ID: 001_initial
Revises: None
Create Date: 2026-03-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="user"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Clients
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(50)),
        sa.Column("monthly_fee", sa.Numeric(10, 2)),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Client-User association
    op.create_table(
        "client_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(50), server_default="viewer"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("tool_calls", postgresql.JSONB()),
        sa.Column("tool_results", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Agent Tasks
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("due_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("action_url", sa.String(500)),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Settings
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Content Templates
    op.create_table(
        "content_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("content_type", sa.String(50)),
        sa.Column("template_data", postgresql.JSONB()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Content Batches
    op.create_table(
        "content_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("scheduled_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Content Items
    op.create_table(
        "content_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("content_batches.id"), nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("content_type", sa.String(50)),
        sa.Column("title", sa.String(255)),
        sa.Column("body", sa.Text()),
        sa.Column("media_urls", postgresql.JSONB()),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Leads
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("source", sa.String(100)),
        sa.Column("stage", sa.String(50), server_default="new"),
        sa.Column("estimated_value", sa.Numeric(10, 2)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Lead Activities
    op.create_table(
        "lead_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Invoices
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("invoice_number", sa.String(50), unique=True),
        sa.Column("concept", sa.String(500)),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), server_default="21"),
        sa.Column("total", sa.Numeric(10, 2)),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("issue_date", sa.Date()),
        sa.Column("due_date", sa.Date()),
        sa.Column("paid_date", sa.Date()),
        sa.Column("pdf_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Expenses
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id")),
        sa.Column("category", sa.String(100)),
        sa.Column("description", sa.String(500)),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), server_default="21"),
        sa.Column("deductible_pct", sa.Numeric(5, 2), server_default="100"),
        sa.Column("date", sa.Date()),
        sa.Column("receipt_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Video Templates
    op.create_table(
        "video_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("fps", sa.Integer(), server_default="30"),
        sa.Column("width", sa.Integer(), server_default="1080"),
        sa.Column("height", sa.Integer(), server_default="1920"),
        sa.Column("duration_per_moment", sa.Integer(), server_default="150"),
        sa.Column("slots_schema", postgresql.JSONB()),
        sa.Column("sfx_defaults", postgresql.JSONB()),
        sa.Column("category", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Video Projects
    op.create_table(
        "video_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("render_url", sa.String(500)),
        sa.Column("thumbnail_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Video Moments
    op.create_table(
        "video_moments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("video_projects.id"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("video_templates.id")),
        sa.Column("order", sa.Integer(), server_default="0"),
        sa.Column("slots_data", postgresql.JSONB()),
        sa.Column("duration_frames", sa.Integer(), server_default="150"),
        sa.Column("transition_type", sa.String(50), server_default="fade"),
        sa.Column("transition_duration", sa.Integer(), server_default="15"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Render Jobs
    op.create_table(
        "render_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("video_projects.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default="queued"),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("output_path", sa.String(500)),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Voiceover Jobs
    op.create_table(
        "voiceover_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("video_projects.id")),
        sa.Column("moment_id", sa.Integer(), sa.ForeignKey("video_moments.id")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("voice_name", sa.String(100)),
        sa.Column("language_code", sa.String(10)),
        sa.Column("audio_url", sa.String(500)),
        sa.Column("duration_seconds", sa.Numeric(8, 2)),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Transcription Jobs
    op.create_table(
        "transcription_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("video_projects.id")),
        sa.Column("input_url", sa.String(500), nullable=False),
        sa.Column("segments", postgresql.JSONB()),
        sa.Column("full_text", sa.Text()),
        sa.Column("language", sa.String(10)),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Fiscal Config
    op.create_table(
        "fiscal_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), unique=True, nullable=False),
        sa.Column("tax_regime", sa.String(50), server_default="autonomo"),
        sa.Column("vat_registered", sa.Boolean(), server_default="true"),
        sa.Column("irpf_rate", sa.Numeric(5, 2), server_default="15"),
        sa.Column("activity_code", sa.String(20)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        if_not_exists=True,
    )

    # Tax Obligations
    op.create_table(
        "tax_obligations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("period", sa.String(10)),
        sa.Column("year", sa.Integer()),
        sa.Column("quarter", sa.Integer()),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("amount", sa.Numeric(10, 2)),
        sa.Column("due_date", sa.Date()),
        sa.Column("filed_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Recurring Invoices
    op.create_table(
        "recurring_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("template_data", postgresql.JSONB()),
        sa.Column("frequency", sa.String(20), server_default="monthly"),
        sa.Column("next_issue_date", sa.Date()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Lead Scores
    op.create_table(
        "lead_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), unique=True, nullable=False),
        sa.Column("score", sa.Integer(), server_default="0"),
        sa.Column("factors", postgresql.JSONB()),
        sa.Column("calculated_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Activities (CRM)
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("date", sa.DateTime()),
        sa.Column("outcome", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Drip Campaigns
    op.create_table(
        "drip_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id")),
        sa.Column("steps", postgresql.JSONB()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Drip Enrollments
    op.create_table(
        "drip_enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("drip_campaigns.id"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("current_step", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("next_action_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Email Templates
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subject_template", sa.String(500)),
        sa.Column("body_html", sa.Text()),
        sa.Column("variables", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Email Sequences
    op.create_table(
        "email_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("drip_campaigns.id")),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("email_templates.id")),
        sa.Column("delay_hours", sa.Integer(), server_default="24"),
        sa.Column("conditions", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        if_not_exists=True,
    )

    # Email Logs
    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("email_templates.id")),
        sa.Column("subject", sa.String(500)),
        sa.Column("status", sa.String(50), server_default="sent"),
        sa.Column("sent_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("metadata", postgresql.JSONB()),
        if_not_exists=True,
    )


def downgrade() -> None:
    tables = [
        "email_logs", "email_sequences", "email_templates",
        "drip_enrollments", "drip_campaigns", "activities", "lead_scores",
        "recurring_invoices", "tax_obligations", "fiscal_configs",
        "transcription_jobs", "voiceover_jobs", "render_jobs",
        "video_moments", "video_projects", "video_templates",
        "expenses", "invoices", "lead_activities", "leads",
        "content_items", "content_batches", "content_templates",
        "settings", "notifications", "agent_tasks",
        "messages", "conversations", "client_users", "clients", "users",
    ]
    for table in tables:
        op.drop_table(table, if_exists=True)
