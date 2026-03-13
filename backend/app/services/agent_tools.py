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
from app.services.file_storage import FileStorage
from app.services.content_engine import generate_batch
from app.services.daily_briefing import generate_briefing

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
        "name": "get_system_status",
        "description": "Get system overview: number of clients, pending tasks, recent activity.",
        "input_schema": {
            "type": "object",
            "properties": {},
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
