"""VULKRAN OS — Agent tool definitions and executor.

Each tool has:
- A Claude API tool definition (JSON schema)
- An executor function that runs the actual logic
"""

import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, Conversation, AgentTask, Notification
from app.models.content import ContentBatch, ContentItem
from app.models.lead import Lead, LeadActivity
from app.models.accounting import Invoice, Expense
from app.services.file_storage import FileStorage
from app.services.content_engine import generate_batch
from app.services.daily_briefing import generate_briefing
from app.services.email_service import send_email, render_lead_intro_email, render_notification_email
from app.services.research_service import research_company, research_topic
from app.services.image_service import generate_image

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Tool definitions (sent to Claude API)
# ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_client_list",
        "description": "Get a list of all active clients with their basic info (name, sector, monthly fee, status).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_client_context",
        "description": "Get full context for a specific client: brand config, sector, enabled modules, contact info, notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "UUID of the client",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "create_task",
        "description": "Create a new task/to-do item for tracking work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title",
                },
                "task_type": {
                    "type": "string",
                    "description": "Type: content_batch, research, email_draft, general",
                },
                "client_id": {
                    "type": "string",
                    "description": "Optional client UUID this task relates to",
                },
            },
            "required": ["title", "task_type"],
        },
    },
    {
        "name": "get_pending_tasks",
        "description": "Get all pending and in-progress tasks.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "notify_user",
        "description": "Send a notification to the user (shows up in the PWA notification bell).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Notification title",
                },
                "body": {
                    "type": "string",
                    "description": "Notification body text",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_client_files",
        "description": "List files stored for a client. Optionally filter by category (brand, content, templates, invoices).",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "UUID of the client",
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category: brand, content, templates, invoices. Leave empty for all.",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "create_content_batch",
        "description": "Create and generate a content batch for a client. Uses Claude to generate marketing content (posts, carousels, etc.) based on client brand config and brief.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "UUID of the client",
                },
                "title": {
                    "type": "string",
                    "description": "Batch title (e.g. 'Instagram posts March week 2')",
                },
                "brief": {
                    "type": "string",
                    "description": "Creative brief / instructions for content generation",
                },
                "platform": {
                    "type": "string",
                    "description": "Target platform: instagram, youtube, linkedin, blog, email, twitter",
                },
                "item_count": {
                    "type": "integer",
                    "description": "Number of content pieces to generate (default 5)",
                },
                "tone": {
                    "type": "string",
                    "description": "Tone: formal, casual, energetic, professional",
                },
                "language": {
                    "type": "string",
                    "description": "Language code (default 'es')",
                },
            },
            "required": ["client_id", "title", "brief"],
        },
    },
    {
        "name": "get_content_status",
        "description": "Get content generation status: recent batches, items pending review, content stats per client.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Optional: filter by client UUID. Leave empty for all clients.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_lead",
        "description": "Create a new lead in the CRM pipeline. Use when a potential client is identified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Lead contact name",
                },
                "company": {
                    "type": "string",
                    "description": "Company name",
                },
                "email": {
                    "type": "string",
                    "description": "Contact email",
                },
                "phone": {
                    "type": "string",
                    "description": "Contact phone",
                },
                "source": {
                    "type": "string",
                    "description": "Lead source: web, referral, linkedin, cold_outreach, event, other",
                },
                "estimated_value": {
                    "type": "number",
                    "description": "Estimated monthly value in EUR",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes about this lead",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_pipeline_status",
        "description": "Get CRM pipeline overview: leads by stage, total value, recent activity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stage": {
                    "type": "string",
                    "description": "Optional: filter by stage (new, contacted, meeting, proposal, negotiation, won, lost)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "update_lead_stage",
        "description": "Move a lead to a new pipeline stage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "string",
                    "description": "UUID of the lead",
                },
                "stage": {
                    "type": "string",
                    "description": "New stage: new, contacted, meeting, proposal, negotiation, won, lost",
                },
                "notes": {
                    "type": "string",
                    "description": "Notes about this stage change",
                },
            },
            "required": ["lead_id", "stage"],
        },
    },
    {
        "name": "get_daily_briefing",
        "description": "Generate today's executive daily briefing with business metrics, pipeline status, content activity, and priority actions.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_financial_summary",
        "description": "Get financial summary: invoiced, paid, pending, expenses, net income for current or specified month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Year (default: current year)",
                },
                "month": {
                    "type": "integer",
                    "description": "Month 1-12 (default: current month)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_system_status",
        "description": "Get system overview: number of clients, pending tasks, recent activity.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # ── New agentic tools ──────────────────────────
    {
        "name": "send_email",
        "description": "Send an email to a lead, client or any recipient. Can use a custom message or auto-generate an intro email for a lead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body_html": {
                    "type": "string",
                    "description": "Email body in HTML. If not provided, use lead_id to auto-generate.",
                },
                "lead_id": {
                    "type": "string",
                    "description": "Optional lead UUID — if provided, auto-generates an outreach email using lead info.",
                },
                "message": {
                    "type": "string",
                    "description": "Plain text message to include in the lead outreach template (used with lead_id).",
                },
            },
            "required": ["to", "subject"],
        },
    },
    {
        "name": "research_company",
        "description": "Research a company online for lead enrichment. Returns sector, activity, recent news.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name of the company to research",
                },
            },
            "required": ["company_name"],
        },
    },
    {
        "name": "research_topic",
        "description": "Research a topic on the web. Used for content briefs, market research, or gathering background info before generating content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to research",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context to refine the search (e.g. 'for a LinkedIn post about AI in healthcare')",
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "generate_image",
        "description": "Generate an image using AI (FAL.ai Flux Pro). Returns the image URL. Use for marketing visuals, social media, brand content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed image description / prompt",
                },
                "image_size": {
                    "type": "string",
                    "description": "Size: landscape_16_9, portrait_9_16, square, square_hd (default: landscape_16_9)",
                },
                "style": {
                    "type": "string",
                    "description": "Optional style hint: photographic, illustration, 3d_render, flat_design",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_video",
        "description": "Generate a short marketing video using Remotion templates. Returns a job ID to track progress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "description": "Template family: IB (editorial), BR (brutalist), SW (swiss), CV (constructivist), CX (codex)",
                },
                "title": {
                    "type": "string",
                    "description": "Video title text",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Video subtitle text",
                },
                "scenes": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of scene objects with text, image_url, duration_seconds",
                },
                "client_id": {
                    "type": "string",
                    "description": "Optional client UUID to apply brand colors",
                },
            },
            "required": ["template", "title"],
        },
    },
    {
        "name": "create_invoice_pdf",
        "description": "Generate a PDF invoice for a client. Creates the invoice record and returns a download URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "UUID of the client",
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                        },
                    },
                    "description": "Line items: [{description, quantity, unit_price}]",
                },
                "due_days": {
                    "type": "integer",
                    "description": "Days until due (default 30)",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes to include on invoice",
                },
            },
            "required": ["client_id", "items"],
        },
    },
    {
        "name": "schedule_content",
        "description": "Schedule a content item for publication at a specific date/time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content_item_id": {
                    "type": "string",
                    "description": "UUID of the content item to schedule",
                },
                "publish_at": {
                    "type": "string",
                    "description": "ISO 8601 datetime for publication (e.g. '2026-03-15T10:00:00Z')",
                },
                "platform": {
                    "type": "string",
                    "description": "Target platform: instagram, linkedin, twitter, blog",
                },
            },
            "required": ["content_item_id", "publish_at"],
        },
    },
    {
        "name": "propose_actions",
        "description": "Analyze current business metrics and propose priority actions. The agent uses this to proactively suggest improvements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus_area": {
                    "type": "string",
                    "description": "Optional focus: revenue, leads, content, operations, all (default: all)",
                },
            },
            "required": [],
        },
    },
    # ── Content Engine tools ──────────────────────
    {
        "name": "generate_video_project",
        "description": "Create a full video project: generates moments from a creative brief using AI, optionally with voiceover. Returns project with editable moments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "UUID of the client"},
                "title": {"type": "string", "description": "Project title"},
                "brief": {"type": "string", "description": "Creative brief / instructions for video content"},
                "template_id": {"type": "string", "description": "Optional template UUID to use"},
                "num_moments": {"type": "integer", "description": "Number of moments/slides (default 5)"},
                "tone": {"type": "string", "description": "Tone: profesional, casual, energetico, inspirador"},
                "language": {"type": "string", "description": "Language code (default 'es')"},
                "generate_voiceover": {"type": "boolean", "description": "Auto-generate TTS voiceover for each moment"},
            },
            "required": ["client_id", "title", "brief"],
        },
    },
    {
        "name": "start_render",
        "description": "Launch video rendering for a project. Returns job ID to track progress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "UUID of the video project"},
                "quality": {"type": "string", "description": "Quality: 720p, 1080p, 2k, 4k, 9:16 (default 1080p)"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "get_render_status",
        "description": "Check the status and progress of a render job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "UUID of the render job"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "generate_voiceover",
        "description": "Generate audio voiceover from text using Google Cloud TTS. Supports Spanish and English voices with adjustable speed and pitch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert to speech (plain text or SSML)"},
                "voice_name": {"type": "string", "description": "Google TTS voice (e.g. 'es-ES-Wavenet-B', 'en-US-Neural2-D')"},
                "language_code": {"type": "string", "description": "Language code (default 'es-ES')"},
                "speaking_rate": {"type": "number", "description": "Speed: 0.25 to 4.0 (default 1.0)"},
                "pitch": {"type": "number", "description": "Pitch adjustment: -20.0 to 20.0 (default 0.0)"},
                "project_id": {"type": "string", "description": "Optional: link to video project"},
                "moment_id": {"type": "string", "description": "Optional: link to specific moment"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "list_available_voices",
        "description": "List available Google TTS voices. Filter by language to see options.",
        "input_schema": {
            "type": "object",
            "properties": {
                "language_code": {"type": "string", "description": "Filter by language (e.g. 'es-ES', 'en-US'). Leave empty for all."},
            },
            "required": [],
        },
    },
    {
        "name": "transcribe_audio",
        "description": "Transcribe audio/video file to text with timestamps. Useful for generating subtitles or auto-populating video moment text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to audio/video file"},
                "language": {"type": "string", "description": "Language code (default 'es')"},
                "model_size": {"type": "string", "description": "Whisper model: tiny, base, small, medium (default 'base')"},
            },
            "required": ["file_path"],
        },
    },
    # ── Fiscal / Accounting tools ─────────────────
    {
        "name": "calculate_tax_obligations",
        "description": "Calculate quarterly tax obligations for a client (Modelo 303 IVA, Modelo 130 IRPF). Spanish tax system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "UUID of the client"},
                "year": {"type": "integer", "description": "Tax year"},
                "quarter": {"type": "integer", "description": "Quarter 1-4"},
            },
            "required": ["client_id", "year", "quarter"],
        },
    },
    {
        "name": "get_tax_calendar",
        "description": "Get upcoming tax filing deadlines and obligations for a client.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "UUID of the client"},
                "year": {"type": "integer", "description": "Tax year (default current)"},
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "create_expense",
        "description": "Register a business expense for tax deduction tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Expense description"},
                "category": {"type": "string", "description": "Category: hosting, software, marketing, tools, freelancer, office, travel, other"},
                "amount": {"type": "number", "description": "Amount in EUR"},
                "date": {"type": "string", "description": "Expense date (YYYY-MM-DD)"},
                "vendor": {"type": "string", "description": "Vendor/supplier name"},
                "tax_deductible": {"type": "boolean", "description": "Is this expense tax deductible? (default true)"},
                "client_id": {"type": "string", "description": "Optional: link to specific client"},
            },
            "required": ["description", "category", "amount", "date"],
        },
    },
    {
        "name": "get_cashflow_projection",
        "description": "Project cash flow for upcoming months based on invoices, expenses, and tax obligations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "UUID of the client"},
                "months": {"type": "integer", "description": "Number of months to project (default 6)"},
            },
            "required": ["client_id"],
        },
    },
    # ── Playwright / Web Automation tools ─────────
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot of any web page. Returns image URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to capture"},
                "full_page": {"type": "boolean", "description": "Capture full page (default true)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "scrape_website",
        "description": "Extract data from a web page. Optionally specify CSS selectors to extract specific elements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
                "selectors": {"type": "object", "description": "Optional: {field_name: css_selector} mapping"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "analyze_seo",
        "description": "Perform a comprehensive SEO audit of a web page: title, meta, headings, images, performance, structured data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to analyze"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "enrich_lead",
        "description": "Enrich a lead's data by scraping their company website for contact info, social links, and company details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_url": {"type": "string", "description": "Company website URL"},
                "lead_id": {"type": "string", "description": "Optional: UUID of lead to update with enriched data"},
            },
            "required": ["company_url"],
        },
    },
    # ── Advanced CRM tools ────────────────────────
    {
        "name": "score_leads",
        "description": "Calculate/recalculate lead scores based on engagement, value, recency, and source quality.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "Optional: score specific lead. If empty, scores all active leads."},
            },
            "required": [],
        },
    },
    {
        "name": "get_lead_insights",
        "description": "Get detailed analysis of a lead with AI-powered recommendations for next steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "UUID of the lead"},
            },
            "required": ["lead_id"],
        },
    },
    {
        "name": "log_activity",
        "description": "Log a CRM activity (call, email, meeting, note) for a lead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string", "description": "UUID of the lead"},
                "activity_type": {"type": "string", "description": "Type: call, email, meeting, note, task, follow_up"},
                "description": {"type": "string", "description": "Activity description"},
                "outcome": {"type": "string", "description": "Outcome: positive, neutral, negative, no_answer"},
            },
            "required": ["lead_id", "activity_type", "description"],
        },
    },
    {
        "name": "get_stale_leads",
        "description": "Find leads without recent activity. Returns leads that haven't been contacted in X days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_inactive": {"type": "integer", "description": "Days without activity to consider stale (default 7)"},
            },
            "required": [],
        },
    },
    # ── Email System tools ────────────────────────
    {
        "name": "send_templated_email",
        "description": "Send an email using a saved template with variable substitution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "template_id": {"type": "string", "description": "UUID of the email template"},
                "to": {"type": "string", "description": "Recipient email"},
                "variables": {"type": "object", "description": "Template variables: {nombre: '...', empresa: '...'}"},
                "lead_id": {"type": "string", "description": "Optional: link to lead for tracking"},
            },
            "required": ["template_id", "to", "variables"],
        },
    },
    {
        "name": "create_email_template",
        "description": "Create a reusable email template with variable placeholders ({{variable}}).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Template name"},
                "subject_template": {"type": "string", "description": "Subject with {{variables}}"},
                "body_html": {"type": "string", "description": "HTML body with {{variables}}"},
                "variables": {"type": "object", "description": "Variable definitions: {var_name: 'description'}"},
                "category": {"type": "string", "description": "Category: outreach, follow_up, proposal, invoice, report, notification"},
            },
            "required": ["name", "subject_template", "body_html"],
        },
    },
    {
        "name": "get_email_analytics",
        "description": "Get email analytics: sent, delivered, opened, clicked, bounced counts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Look back N days (default 30)"},
                "lead_id": {"type": "string", "description": "Optional: filter by lead"},
            },
            "required": [],
        },
    },
    # ── Research tools ────────────────────────────
    {
        "name": "deep_research",
        "description": "Perform deep research on a topic: multiple web searches synthesized into a structured report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Research topic"},
                "depth": {"type": "string", "description": "Depth: quick, standard, deep (default standard)"},
                "language": {"type": "string", "description": "Output language (default 'es')"},
            },
            "required": ["topic"],
        },
    },
]


# ──────────────────────────────────────────────
# Tool executor
# ──────────────────────────────────────────────


class ToolExecutor:
    """Executes agent tool calls against the database."""

    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def execute(self, tool_name: str, tool_input: dict) -> str | dict:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return f"Error: unknown tool '{tool_name}'"
        try:
            return await handler(tool_input)
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return f"Error executing {tool_name}: {e}"

    async def _tool_get_client_list(self, _input: dict) -> dict:
        result = await self.db.execute(
            select(Client)
            .where(Client.status == "active")
            .order_by(Client.name)
        )
        clients = result.scalars().all()
        return {
            "clients": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "sector": c.sector,
                    "monthly_fee": str(c.monthly_fee) if c.monthly_fee else None,
                    "status": c.status,
                }
                for c in clients
            ]
        }

    async def _tool_get_client_context(self, _input: dict) -> dict:
        client_id = _input["client_id"]
        result = await self.db.execute(
            select(Client).where(Client.id == uuid.UUID(client_id))
        )
        c = result.scalar_one_or_none()
        if not c:
            return {"error": f"Client {client_id} not found"}
        return {
            "id": str(c.id),
            "name": c.name,
            "slug": c.slug,
            "sector": c.sector,
            "contact_name": c.contact_name,
            "contact_email": c.contact_email,
            "brand_config": c.brand_config,
            "enabled_modules": c.enabled_modules,
            "monthly_fee": str(c.monthly_fee) if c.monthly_fee else None,
            "notes": c.notes,
            "status": c.status,
        }

    async def _tool_create_task(self, _input: dict) -> dict:
        task = AgentTask(
            task_type=_input["task_type"],
            status="pending",
            input_data={
                "title": _input["title"],
                "client_id": _input.get("client_id"),
            },
        )
        self.db.add(task)
        await self.db.flush()
        return {"task_id": str(task.id), "status": "created"}

    async def _tool_get_pending_tasks(self, _input: dict) -> dict:
        result = await self.db.execute(
            select(AgentTask)
            .where(AgentTask.status.in_(["pending", "running"]))
            .order_by(AgentTask.created_at.desc())
            .limit(20)
        )
        tasks = result.scalars().all()
        return {
            "tasks": [
                {
                    "id": str(t.id),
                    "type": t.task_type,
                    "status": t.status,
                    "title": (t.input_data or {}).get("title", ""),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ]
        }

    async def _tool_notify_user(self, _input: dict) -> dict:
        notif = Notification(
            user_id=self.user_id,
            title=_input["title"],
            body=_input.get("body"),
        )
        self.db.add(notif)
        await self.db.flush()
        return {"notification_id": str(notif.id), "status": "sent"}

    async def _tool_list_client_files(self, _input: dict) -> dict:
        client_id = _input["client_id"]
        result = await self.db.execute(
            select(Client).where(Client.id == uuid.UUID(client_id))
        )
        client = result.scalar_one_or_none()
        if not client:
            return {"error": f"Client {client_id} not found"}
        category = _input.get("category", "")
        files = FileStorage.list_files(client.slug, category)
        return {
            "client": client.name,
            "category": category or "all",
            "file_count": len(files),
            "files": files[:20],  # Limit to avoid token overflow
        }

    async def _tool_create_content_batch(self, _input: dict) -> dict:
        client_id = _input["client_id"]
        result = await self.db.execute(
            select(Client).where(Client.id == uuid.UUID(client_id))
        )
        client = result.scalar_one_or_none()
        if not client:
            return {"error": f"Client {client_id} not found"}

        # Create batch
        batch = ContentBatch(
            client_id=client.id,
            title=_input["title"],
            brief=_input.get("brief"),
            platform=_input.get("platform"),
            status="draft",
            item_count=0,
        )
        self.db.add(batch)
        await self.db.flush()

        # Generate content
        batch = await generate_batch(
            db=self.db,
            batch=batch,
            brief=_input.get("brief"),
            item_count=_input.get("item_count", 5),
            tone=_input.get("tone"),
            language=_input.get("language", "es"),
            user_id=self.user_id,
        )

        return {
            "batch_id": str(batch.id),
            "status": batch.status,
            "item_count": batch.item_count,
            "client": client.name,
            "title": batch.title,
        }

    async def _tool_get_content_status(self, _input: dict) -> dict:
        query = select(ContentBatch).order_by(ContentBatch.created_at.desc()).limit(10)
        client_id = _input.get("client_id")
        if client_id:
            query = query.where(ContentBatch.client_id == uuid.UUID(client_id))

        result = await self.db.execute(query)
        batches = result.scalars().all()

        # Count items pending review
        review_count = await self.db.scalar(
            select(func.count())
            .select_from(ContentItem)
            .where(ContentItem.status == "generated")
        ) or 0

        return {
            "recent_batches": [
                {
                    "id": str(b.id),
                    "title": b.title,
                    "status": b.status,
                    "platform": b.platform,
                    "item_count": b.item_count,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
                for b in batches
            ],
            "items_pending_review": review_count,
        }

    async def _tool_create_lead(self, _input: dict) -> dict:
        from decimal import Decimal

        lead = Lead(
            name=_input["name"],
            company=_input.get("company"),
            email=_input.get("email"),
            phone=_input.get("phone"),
            source=_input.get("source"),
            estimated_value=Decimal(str(_input["estimated_value"])) if _input.get("estimated_value") else None,
            notes=_input.get("notes"),
            owner_id=self.user_id,
            stage="new",
        )
        self.db.add(lead)
        await self.db.flush()

        activity = LeadActivity(
            lead_id=lead.id,
            activity_type="note",
            description=f"Lead creado via agente: {lead.name}" + (f" ({lead.company})" if lead.company else ""),
            created_by=self.user_id,
        )
        self.db.add(activity)
        await self.db.flush()

        return {
            "lead_id": str(lead.id),
            "name": lead.name,
            "company": lead.company,
            "stage": lead.stage,
            "status": "created",
        }

    async def _tool_get_pipeline_status(self, _input: dict) -> dict:
        stage_filter = _input.get("stage")

        query = select(Lead).order_by(Lead.created_at.desc())
        if stage_filter:
            query = query.where(Lead.stage == stage_filter)
        query = query.limit(20)

        result = await self.db.execute(query)
        leads = result.scalars().all()

        # Count by stage
        stage_result = await self.db.execute(
            select(Lead.stage, func.count()).group_by(Lead.stage)
        )
        by_stage = {row[0]: row[1] for row in stage_result.all()}

        total_value = await self.db.scalar(
            select(func.sum(Lead.estimated_value)).where(
                Lead.stage.notin_(["won", "lost"])
            )
        )

        return {
            "pipeline": by_stage,
            "total_active_value": str(total_value) if total_value else "0",
            "leads": [
                {
                    "id": str(l.id),
                    "name": l.name,
                    "company": l.company,
                    "stage": l.stage,
                    "estimated_value": str(l.estimated_value) if l.estimated_value else None,
                    "next_action": l.next_action,
                }
                for l in leads
            ],
        }

    async def _tool_update_lead_stage(self, _input: dict) -> dict:
        lead_id = _input["lead_id"]
        new_stage = _input["stage"]

        result = await self.db.execute(
            select(Lead).where(Lead.id == uuid.UUID(lead_id))
        )
        lead = result.scalar_one_or_none()
        if not lead:
            return {"error": f"Lead {lead_id} not found"}

        old_stage = lead.stage
        lead.stage = new_stage

        activity = LeadActivity(
            lead_id=lead.id,
            activity_type="stage_change",
            description=f"Etapa: {old_stage} → {new_stage}" + (f" | {_input.get('notes', '')}" if _input.get("notes") else ""),
            metadata_={"from_stage": old_stage, "to_stage": new_stage},
            created_by=self.user_id,
        )
        self.db.add(activity)
        await self.db.flush()

        return {
            "lead_id": str(lead.id),
            "name": lead.name,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "status": "updated",
        }

    async def _tool_get_daily_briefing(self, _input: dict) -> dict:
        result = await generate_briefing(self.db)
        return result

    async def _tool_get_financial_summary(self, _input: dict) -> dict:
        from datetime import datetime as dt, timezone as tz
        from sqlalchemy import extract as sql_extract
        from decimal import Decimal

        now = dt.now(tz.utc)
        y = _input.get("year") or now.year
        m = _input.get("month") or now.month

        total_invoiced = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                sql_extract("year", Invoice.issue_date) == y,
                sql_extract("month", Invoice.issue_date) == m,
            )
        ) or Decimal("0")

        total_paid = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.status == "paid",
                sql_extract("year", Invoice.issue_date) == y,
                sql_extract("month", Invoice.issue_date) == m,
            )
        ) or Decimal("0")

        total_expenses = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                sql_extract("year", Expense.date) == y,
                sql_extract("month", Expense.date) == m,
            )
        ) or Decimal("0")

        return {
            "period": f"{y}-{m:02d}",
            "total_invoiced": str(total_invoiced),
            "total_paid": str(total_paid),
            "total_pending": str(total_invoiced - total_paid),
            "total_expenses": str(total_expenses),
            "net_income": str(total_paid - total_expenses),
        }

    async def _tool_get_system_status(self, _input: dict) -> dict:
        clients_count = await self.db.scalar(
            select(func.count()).select_from(Client).where(Client.status == "active")
        )
        pending_tasks = await self.db.scalar(
            select(func.count())
            .select_from(AgentTask)
            .where(AgentTask.status.in_(["pending", "running"]))
        )
        leads_count = await self.db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.stage.notin_(["won", "lost"])
            )
        )
        return {
            "active_clients": clients_count or 0,
            "pending_tasks": pending_tasks or 0,
            "active_leads": leads_count or 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── New agentic tool executors ─────────────────

    async def _tool_send_email(self, _input: dict) -> dict:
        to = _input["to"]
        subject = _input["subject"]

        # If lead_id provided, auto-generate outreach email
        if _input.get("lead_id"):
            result = await self.db.execute(
                select(Lead).where(Lead.id == uuid.UUID(_input["lead_id"]))
            )
            lead = result.scalar_one_or_none()
            if not lead:
                return {"error": f"Lead {_input['lead_id']} not found"}
            html = render_lead_intro_email(
                lead_name=lead.name,
                company=lead.company,
                message=_input.get("message", ""),
            )
            to = lead.email or to
        elif _input.get("body_html"):
            html = _input["body_html"]
        else:
            html = render_notification_email(
                title=subject,
                body=_input.get("message", ""),
            )

        result = await send_email(to=to, subject=subject, html=html)

        # Log activity if lead
        if _input.get("lead_id"):
            activity = LeadActivity(
                lead_id=uuid.UUID(_input["lead_id"]),
                activity_type="email",
                description=f"Email enviado: {subject}",
                created_by=self.user_id,
            )
            self.db.add(activity)
            await self.db.flush()

        return {"status": "sent", "to": to, "email_id": result.get("id")}

    async def _tool_research_company(self, _input: dict) -> dict:
        return await research_company(_input["company_name"])

    async def _tool_research_topic(self, _input: dict) -> dict:
        return await research_topic(
            topic=_input["topic"],
            context=_input.get("context"),
        )

    async def _tool_generate_image(self, _input: dict) -> dict:
        prompt = _input["prompt"]
        style = _input.get("style")
        if style:
            prompt = f"{prompt}, {style} style"
        result = await generate_image(
            prompt=prompt,
            image_size=_input.get("image_size", "landscape_16_9"),
        )
        return result

    async def _tool_generate_video(self, _input: dict) -> dict:
        # Placeholder — Remotion rendering will be integrated in Fase E
        template = _input["template"]
        title = _input["title"]
        logger.info("Video generation requested: %s / %s", template, title)
        return {
            "status": "queued",
            "message": f"Video '{title}' con plantilla {template} en cola de renderizado.",
            "job_id": str(uuid.uuid4()),
            "template": template,
            "title": title,
        }

    async def _tool_create_invoice_pdf(self, _input: dict) -> dict:
        from decimal import Decimal

        client_id = _input["client_id"]
        result = await self.db.execute(
            select(Client).where(Client.id == uuid.UUID(client_id))
        )
        client = result.scalar_one_or_none()
        if not client:
            return {"error": f"Client {client_id} not found"}

        items = _input.get("items", [])
        subtotal = sum(
            Decimal(str(i.get("quantity", 1))) * Decimal(str(i.get("unit_price", 0)))
            for i in items
        )
        tax_rate = Decimal("0.21")  # 21% IVA
        tax = subtotal * tax_rate
        total = subtotal + tax

        due_days = _input.get("due_days", 30)
        now = datetime.now(timezone.utc)
        due_date = now + __import__("datetime").timedelta(days=due_days)

        # Generate invoice number
        count = await self.db.scalar(
            select(func.count()).select_from(Invoice)
        ) or 0
        invoice_number = f"VK-{now.year}-{count + 1:04d}"

        invoice = Invoice(
            client_id=client.id,
            number=invoice_number,
            issue_date=now.date(),
            due_date=due_date.date(),
            subtotal=subtotal,
            tax=tax,
            total=total,
            status="pending",
            notes=_input.get("notes"),
            items=items,
        )
        self.db.add(invoice)
        await self.db.flush()

        return {
            "invoice_id": str(invoice.id),
            "number": invoice_number,
            "client": client.name,
            "subtotal": str(subtotal),
            "tax": str(tax),
            "total": str(total),
            "due_date": due_date.date().isoformat(),
            "status": "created",
        }

    async def _tool_schedule_content(self, _input: dict) -> dict:
        content_item_id = _input["content_item_id"]
        result = await self.db.execute(
            select(ContentItem).where(ContentItem.id == uuid.UUID(content_item_id))
        )
        item = result.scalar_one_or_none()
        if not item:
            return {"error": f"Content item {content_item_id} not found"}

        publish_at = datetime.fromisoformat(_input["publish_at"])
        item.status = "scheduled"
        item.metadata_ = item.metadata_ or {}
        item.metadata_["scheduled_at"] = publish_at.isoformat()
        item.metadata_["platform"] = _input.get("platform", item.metadata_.get("platform"))
        await self.db.flush()

        return {
            "content_item_id": str(item.id),
            "status": "scheduled",
            "publish_at": publish_at.isoformat(),
            "platform": _input.get("platform"),
        }

    async def _tool_propose_actions(self, _input: dict) -> dict:
        focus = _input.get("focus_area", "all")

        # Gather key metrics
        clients_count = await self.db.scalar(
            select(func.count()).select_from(Client).where(Client.status == "active")
        ) or 0

        leads_by_stage = {}
        stage_result = await self.db.execute(
            select(Lead.stage, func.count()).group_by(Lead.stage)
        )
        for row in stage_result.all():
            leads_by_stage[row[0]] = row[1]

        pending_tasks = await self.db.scalar(
            select(func.count()).select_from(AgentTask)
            .where(AgentTask.status.in_(["pending", "running"]))
        ) or 0

        review_count = await self.db.scalar(
            select(func.count()).select_from(ContentItem)
            .where(ContentItem.status == "generated")
        ) or 0

        # Financial snapshot (current month)
        now = datetime.now(timezone.utc)
        from sqlalchemy import extract as sql_extract
        monthly_invoiced = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                sql_extract("year", Invoice.issue_date) == now.year,
                sql_extract("month", Invoice.issue_date) == now.month,
            )
        )
        monthly_paid = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.status == "paid",
                sql_extract("year", Invoice.issue_date) == now.year,
                sql_extract("month", Invoice.issue_date) == now.month,
            )
        )

        return {
            "focus": focus,
            "metrics": {
                "active_clients": clients_count,
                "leads_pipeline": leads_by_stage,
                "pending_tasks": pending_tasks,
                "content_pending_review": review_count,
                "monthly_invoiced": str(monthly_invoiced),
                "monthly_paid": str(monthly_paid),
            },
            "instruction": (
                "Based on these metrics, propose 3-5 priority actions the user should take. "
                "Be specific: mention lead names, client names, amounts. "
                "Focus on revenue-generating and pipeline-advancing actions."
            ),
        }

    # ── Content Engine tool executors ─────────────

    async def _tool_generate_video_project(self, _input: dict) -> dict:
        from app.models.content_engine import VideoProject, VideoMoment, VideoTemplate
        from app.services.moment_director_service import generate_moments
        from app.services.tts_service import generate_voiceover

        client_id = _input["client_id"]
        title = _input["title"]
        brief = _input["brief"]
        template_id = _input.get("template_id")
        num_moments = _input.get("num_moments", 5)
        tone = _input.get("tone", "profesional")
        language = _input.get("language", "es")
        do_voiceover = _input.get("generate_voiceover", False)

        # Create project
        project = VideoProject(
            client_id=uuid.UUID(client_id),
            title=title,
            brief=brief,
            template_id=uuid.UUID(template_id) if template_id else None,
            status="generating",
        )
        self.db.add(project)
        await self.db.flush()

        # Get template slots
        template_slots = []
        if template_id:
            template = await self.db.get(VideoTemplate, uuid.UUID(template_id))
            if template:
                template_slots = template.slots_schema
                project.fps = template.fps
                project.width = template.width
                project.height = template.height

        # Get client context
        result = await self.db.execute(
            select(Client).where(Client.id == uuid.UUID(client_id))
        )
        client = result.scalar_one_or_none()
        client_context = {"name": client.name, "sector": client.sector} if client else None

        try:
            moments_data = await generate_moments(
                brief=brief,
                template_slots=template_slots,
                client_context=client_context,
                num_moments=num_moments,
                tone=tone,
                language=language,
            )

            created_moments = []
            for i, m in enumerate(moments_data):
                moment = VideoMoment(
                    project_id=project.id,
                    template_id=project.template_id,
                    sort_order=i,
                    slots_data=m["slots_data"],
                    transition_type=m.get("transition_type", "fade"),
                    voiceover_text=m.get("voiceover_text", ""),
                )
                self.db.add(moment)
                created_moments.append(moment)

            await self.db.flush()

            # Generate voiceovers if requested
            if do_voiceover:
                for moment in created_moments:
                    if moment.voiceover_text:
                        try:
                            vo_result = await generate_voiceover(
                                text=moment.voiceover_text,
                                language_code="es-ES" if language == "es" else "en-US",
                            )
                            moment.voiceover_url = vo_result["audio_url"]
                        except Exception as e:
                            logger.warning("Voiceover failed for moment: %s", e)
                await self.db.flush()

            project.status = "review"
            await self.db.flush()

            return {
                "project_id": str(project.id),
                "title": title,
                "moments_generated": len(created_moments),
                "voiceovers_generated": sum(1 for m in created_moments if m.voiceover_url) if do_voiceover else 0,
                "status": "review",
            }

        except Exception as e:
            project.status = "error"
            await self.db.flush()
            return {"error": f"Video project generation failed: {e}"}

    async def _tool_start_render(self, _input: dict) -> dict:
        from app.services.render_service import start_render
        try:
            job = await start_render(self.db, _input["project_id"], _input.get("quality", "1080p"))
            return {
                "job_id": str(job.id),
                "project_id": _input["project_id"],
                "status": job.status,
                "quality": _input.get("quality", "1080p"),
            }
        except ValueError as e:
            return {"error": str(e)}

    async def _tool_get_render_status(self, _input: dict) -> dict:
        from app.services.render_service import get_render_status
        result = await get_render_status(self.db, _input["job_id"])
        return result or {"error": "Render job not found"}

    async def _tool_generate_voiceover(self, _input: dict) -> dict:
        from app.services.tts_service import generate_voiceover
        from app.models.content_engine import VoiceoverJob, VideoMoment, VideoProject

        try:
            result = await generate_voiceover(
                text=_input["text"],
                voice_name=_input.get("voice_name"),
                language_code=_input.get("language_code"),
                speaking_rate=_input.get("speaking_rate", 1.0),
                pitch=_input.get("pitch", 0.0),
            )

            # Create tracking record
            vo_job = VoiceoverJob(
                project_id=uuid.UUID(_input["project_id"]) if _input.get("project_id") else None,
                moment_id=uuid.UUID(_input["moment_id"]) if _input.get("moment_id") else None,
                text=_input["text"],
                voice_name=result["voice_name"],
                language_code=result["language_code"],
                audio_url=result["audio_url"],
                duration_seconds=result["duration_seconds"],
                status="done",
            )
            self.db.add(vo_job)

            # Link to moment if specified
            if _input.get("moment_id"):
                moment = await self.db.get(VideoMoment, uuid.UUID(_input["moment_id"]))
                if moment:
                    moment.voiceover_url = result["audio_url"]

            await self.db.flush()

            return {
                "audio_url": result["audio_url"],
                "duration_seconds": result["duration_seconds"],
                "voice_name": result["voice_name"],
                "status": "done",
            }
        except Exception as e:
            return {"error": f"TTS generation failed: {e}"}

    async def _tool_list_available_voices(self, _input: dict) -> dict:
        from app.services.tts_service import list_voices
        try:
            voices = await list_voices(_input.get("language_code"))
            return {"voices": voices[:20]}  # Limit to avoid token overflow
        except Exception as e:
            return {"error": f"Failed to list voices: {e}"}

    async def _tool_transcribe_audio(self, _input: dict) -> dict:
        from app.services.transcription_service import transcribe_audio
        try:
            result = await transcribe_audio(
                file_path=_input["file_path"],
                language=_input.get("language", "es"),
                model_size=_input.get("model_size", "base"),
            )
            return {
                "full_text": result["full_text"],
                "segments": result["segments"][:20],  # Limit segments
                "duration": result["duration"],
                "language": result["language"],
            }
        except Exception as e:
            return {"error": f"Transcription failed: {e}"}

    # ── Fiscal / Accounting tool executors ─────────

    async def _tool_calculate_tax_obligations(self, _input: dict) -> dict:
        from app.services.fiscal_service import calculate_modelo_303, calculate_modelo_130
        client_id = _input["client_id"]
        year = _input["year"]
        quarter = _input["quarter"]

        modelo_303 = await calculate_modelo_303(self.db, client_id, year, quarter)
        modelo_130 = await calculate_modelo_130(self.db, client_id, year, quarter)

        return {
            "modelo_303": modelo_303,
            "modelo_130": modelo_130,
            "summary": (
                f"Q{quarter} {year}: IVA a ingresar {modelo_303['a_ingresar']:.2f}€, "
                f"IRPF pago fraccionado {modelo_130['resultado']:.2f}€"
            ),
        }

    async def _tool_get_tax_calendar(self, _input: dict) -> dict:
        from app.services.fiscal_service import get_tax_calendar
        calendar = await get_tax_calendar(
            self.db, _input["client_id"], _input.get("year")
        )
        return {"calendar": calendar}

    async def _tool_create_expense(self, _input: dict) -> dict:
        from datetime import date as d
        expense = Expense(
            description=_input["description"],
            category=_input["category"],
            amount=__import__("decimal").Decimal(str(_input["amount"])),
            date=d.fromisoformat(_input["date"]),
            vendor=_input.get("vendor"),
            tax_deductible=_input.get("tax_deductible", True),
            client_id=uuid.UUID(_input["client_id"]) if _input.get("client_id") else None,
        )
        self.db.add(expense)
        await self.db.flush()
        return {
            "expense_id": str(expense.id),
            "description": expense.description,
            "amount": str(expense.amount),
            "status": "created",
        }

    async def _tool_get_cashflow_projection(self, _input: dict) -> dict:
        from app.services.fiscal_service import get_cashflow_projection
        projection = await get_cashflow_projection(
            self.db, _input["client_id"], _input.get("months", 6)
        )
        return {"projection": projection}

    # ── Playwright / Web Automation tool executors ─

    async def _tool_take_screenshot(self, _input: dict) -> dict:
        from app.services.playwright_service import take_screenshot
        return await take_screenshot(
            url=_input["url"],
            full_page=_input.get("full_page", True),
        )

    async def _tool_scrape_website(self, _input: dict) -> dict:
        from app.services.playwright_service import scrape_page
        return await scrape_page(
            url=_input["url"],
            selectors=_input.get("selectors"),
        )

    async def _tool_analyze_seo(self, _input: dict) -> dict:
        from app.services.playwright_service import analyze_seo
        return await analyze_seo(url=_input["url"])

    async def _tool_enrich_lead(self, _input: dict) -> dict:
        from app.services.playwright_service import enrich_lead
        data = await enrich_lead(company_url=_input["company_url"])

        # Update lead record if provided
        if _input.get("lead_id") and data.get("scraped"):
            result = await self.db.execute(
                select(Lead).where(Lead.id == uuid.UUID(_input["lead_id"]))
            )
            lead = result.scalar_one_or_none()
            if lead:
                if data.get("email") and not lead.email:
                    lead.email = data["email"]
                if data.get("phone") and not lead.phone:
                    lead.phone = data["phone"]
                lead.notes = (lead.notes or "") + f"\n[Auto-enriched] {data.get('title', '')}"
                await self.db.flush()
                data["lead_updated"] = True

        return data

    # ── Advanced CRM tool executors ───────────────

    async def _tool_score_leads(self, _input: dict) -> dict:
        from app.models.crm_advanced import LeadScore, Activity
        from datetime import datetime as dt, timezone as tz, timedelta

        lead_id = _input.get("lead_id")
        now = dt.now(tz.utc)

        if lead_id:
            leads = [await self.db.get(Lead, uuid.UUID(lead_id))]
            leads = [l for l in leads if l]
        else:
            result = await self.db.execute(
                select(Lead).where(Lead.stage.notin_(["won", "lost"]))
            )
            leads = result.scalars().all()

        scores = []
        for lead in leads:
            factors = {}
            score = 0

            # Source quality (0-20)
            source_scores = {"referral": 20, "web": 15, "linkedin": 12, "event": 10, "cold_outreach": 5, "other": 3}
            factors["source_quality"] = source_scores.get(lead.source or "other", 3)
            score += factors["source_quality"]

            # Estimated value (0-25)
            if lead.estimated_value:
                val = float(lead.estimated_value)
                factors["budget"] = min(int(val / 100), 25)
            else:
                factors["budget"] = 0
            score += factors["budget"]

            # Activity count (0-20)
            activity_count = await self.db.scalar(
                select(func.count()).select_from(LeadActivity)
                .where(LeadActivity.lead_id == lead.id)
            ) or 0
            factors["interactions"] = min(activity_count * 4, 20)
            score += factors["interactions"]

            # Recency (0-20)
            days_since_created = (now - lead.created_at.replace(tzinfo=tz.utc)).days if lead.created_at else 30
            factors["recency"] = max(20 - days_since_created, 0)
            score += factors["recency"]

            # Pipeline stage (0-15)
            stage_scores = {"new": 5, "contacted": 8, "meeting": 12, "proposal": 14, "negotiation": 15}
            factors["stage_progress"] = stage_scores.get(lead.stage, 0)
            score += factors["stage_progress"]

            score = min(score, 100)

            # Upsert LeadScore
            existing = await self.db.execute(
                select(LeadScore).where(LeadScore.lead_id == lead.id)
            )
            lead_score = existing.scalar_one_or_none()
            if lead_score:
                lead_score.score = score
                lead_score.factors = factors
                lead_score.calculated_at = now
            else:
                lead_score = LeadScore(
                    lead_id=lead.id, score=score, factors=factors, calculated_at=now
                )
                self.db.add(lead_score)

            scores.append({"lead_id": str(lead.id), "name": lead.name, "score": score, "factors": factors})

        await self.db.flush()
        return {"scored_leads": scores}

    async def _tool_get_lead_insights(self, _input: dict) -> dict:
        lead = await self.db.get(Lead, uuid.UUID(_input["lead_id"]))
        if not lead:
            return {"error": "Lead not found"}

        # Get activities
        result = await self.db.execute(
            select(LeadActivity)
            .where(LeadActivity.lead_id == lead.id)
            .order_by(LeadActivity.created_at.desc())
            .limit(10)
        )
        activities = result.scalars().all()

        return {
            "lead": {
                "id": str(lead.id),
                "name": lead.name,
                "company": lead.company,
                "email": lead.email,
                "stage": lead.stage,
                "source": lead.source,
                "estimated_value": str(lead.estimated_value) if lead.estimated_value else None,
                "days_in_pipeline": (datetime.now(timezone.utc) - lead.created_at.replace(tzinfo=timezone.utc)).days if lead.created_at else 0,
            },
            "recent_activities": [
                {
                    "type": a.activity_type,
                    "description": a.description,
                    "date": a.created_at.isoformat() if a.created_at else None,
                }
                for a in activities
            ],
            "instruction": "Analyze this lead and suggest specific next steps based on their stage, activity history, and value.",
        }

    async def _tool_log_activity(self, _input: dict) -> dict:
        from app.models.crm_advanced import Activity
        activity = Activity(
            lead_id=uuid.UUID(_input["lead_id"]),
            activity_type=_input["activity_type"],
            description=_input["description"],
            outcome=_input.get("outcome"),
            performed_by=self.user_id,
            performed_at=datetime.now(timezone.utc),
        )
        self.db.add(activity)
        await self.db.flush()
        return {"activity_id": str(activity.id), "status": "logged"}

    async def _tool_get_stale_leads(self, _input: dict) -> dict:
        from datetime import timedelta
        days = _input.get("days_inactive", 7)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Leads where last activity is before cutoff
        from sqlalchemy import and_
        result = await self.db.execute(
            select(Lead)
            .where(
                Lead.stage.notin_(["won", "lost"]),
                Lead.created_at < cutoff,
            )
            .order_by(Lead.created_at.asc())
            .limit(20)
        )
        leads = result.scalars().all()

        stale = []
        for lead in leads:
            last_activity = await self.db.execute(
                select(LeadActivity)
                .where(LeadActivity.lead_id == lead.id)
                .order_by(LeadActivity.created_at.desc())
                .limit(1)
            )
            last = last_activity.scalar_one_or_none()
            last_date = last.created_at if last else lead.created_at
            if last_date and last_date.replace(tzinfo=timezone.utc) < cutoff:
                stale.append({
                    "id": str(lead.id),
                    "name": lead.name,
                    "company": lead.company,
                    "stage": lead.stage,
                    "days_since_activity": (datetime.now(timezone.utc) - last_date.replace(tzinfo=timezone.utc)).days,
                })

        return {"stale_leads": stale, "threshold_days": days}

    # ── Email System tool executors ───────────────

    async def _tool_send_templated_email(self, _input: dict) -> dict:
        from app.models.email_system import EmailTemplate as ET, EmailLog
        import re

        template = await self.db.get(ET, uuid.UUID(_input["template_id"]))
        if not template:
            return {"error": "Email template not found"}

        variables = _input.get("variables", {})

        # Replace variables in subject and body
        subject = template.subject_template
        body = template.body_html
        for key, val in variables.items():
            pattern = "{{" + key + "}}"
            subject = subject.replace(pattern, str(val))
            body = body.replace(pattern, str(val))

        result = await send_email(to=_input["to"], subject=subject, html=body)

        # Log
        log = EmailLog(
            to_email=_input["to"],
            from_email="noreply@vulkran.es",
            template_id=template.id,
            subject=subject,
            body_preview=re.sub(r"<[^>]+>", "", body)[:500],
            status="sent",
            resend_id=result.get("id"),
            lead_id=uuid.UUID(_input["lead_id"]) if _input.get("lead_id") else None,
            sent_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.flush()

        return {"status": "sent", "to": _input["to"], "subject": subject}

    async def _tool_create_email_template(self, _input: dict) -> dict:
        from app.models.email_system import EmailTemplate as ET
        template = ET(
            name=_input["name"],
            subject_template=_input["subject_template"],
            body_html=_input["body_html"],
            variables=_input.get("variables", {}),
            category=_input.get("category", "general"),
        )
        self.db.add(template)
        await self.db.flush()
        return {"template_id": str(template.id), "name": template.name, "status": "created"}

    async def _tool_get_email_analytics(self, _input: dict) -> dict:
        from app.models.email_system import EmailLog
        from datetime import timedelta
        days = _input.get("days", 30)
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(EmailLog.status, func.count()).where(
            EmailLog.sent_at >= since
        ).group_by(EmailLog.status)

        if _input.get("lead_id"):
            query = query.where(EmailLog.lead_id == uuid.UUID(_input["lead_id"]))

        result = await self.db.execute(query)
        stats = {row[0]: row[1] for row in result.all()}

        total = sum(stats.values())
        return {
            "period_days": days,
            "total_sent": total,
            "by_status": stats,
            "open_rate": f"{stats.get('opened', 0) / total * 100:.1f}%" if total > 0 else "0%",
        }

    # ── Research tool executors ───────────────────

    async def _tool_deep_research(self, _input: dict) -> dict:
        topic = _input["topic"]
        depth = _input.get("depth", "standard")
        num_searches = {"quick": 1, "standard": 3, "deep": 5}.get(depth, 3)

        # Multiple searches with different angles
        results = []
        search_queries = [topic]
        if num_searches >= 3:
            search_queries.extend([
                f"{topic} tendencias 2026",
                f"{topic} mejores practicas",
            ])
        if num_searches >= 5:
            search_queries.extend([
                f"{topic} estadisticas datos",
                f"{topic} casos de exito",
            ])

        for query in search_queries[:num_searches]:
            try:
                r = await research_topic(topic=query, context=_input.get("language", "es"))
                results.append(r)
            except Exception as e:
                logger.warning("Research query failed: %s - %s", query, e)

        return {
            "topic": topic,
            "depth": depth,
            "searches_performed": len(results),
            "results": results,
            "instruction": "Synthesize all research results into a structured, actionable report in Spanish.",
        }
