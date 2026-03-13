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

    async def _tool_get_system_status(self, _input: dict) -> dict:
        clients_count = await self.db.scalar(
            select(func.count()).select_from(Client).where(Client.status == "active")
        )
        pending_tasks = await self.db.scalar(
            select(func.count())
            .select_from(AgentTask)
            .where(AgentTask.status.in_(["pending", "running"]))
        )
        return {
            "active_clients": clients_count or 0,
            "pending_tasks": pending_tasks or 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
