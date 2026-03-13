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
