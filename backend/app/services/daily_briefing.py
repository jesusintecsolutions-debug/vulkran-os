"""VULKRAN OS — Daily Briefing service.

Gathers business metrics and generates a daily executive summary using Claude.
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, AgentTask, Notification
from app.models.content import ContentBatch, ContentItem
from app.models.lead import Lead, LeadActivity
from app.services.llm_bridge import call_claude, extract_text
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def gather_metrics(db: AsyncSession) -> dict:
    """Collect all business metrics for the briefing."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    # Clients
    active_clients = await db.scalar(
        select(func.count()).select_from(Client).where(Client.status == "active")
    ) or 0

    total_mrr = await db.scalar(
        select(func.sum(Client.monthly_fee)).where(Client.status == "active")
    )

    # Leads pipeline
    lead_stages = await db.execute(
        select(Lead.stage, func.count()).group_by(Lead.stage)
    )
    pipeline = {row[0]: row[1] for row in lead_stages.all()}

    pipeline_value = await db.scalar(
        select(func.sum(Lead.estimated_value)).where(
            Lead.stage.notin_(["won", "lost"])
        )
    )

    # Recent lead activity (last 24h)
    recent_lead_activities = await db.scalar(
        select(func.count()).select_from(LeadActivity).where(
            LeadActivity.created_at >= yesterday
        )
    ) or 0

    # Leads with pending next actions
    leads_needing_action = await db.execute(
        select(Lead.name, Lead.company, Lead.next_action, Lead.next_action_date, Lead.stage)
        .where(
            Lead.next_action_date.isnot(None),
            Lead.next_action_date <= now + timedelta(days=1),
            Lead.stage.notin_(["won", "lost"]),
        )
        .order_by(Lead.next_action_date)
        .limit(10)
    )
    upcoming_actions = [
        {
            "name": row[0],
            "company": row[1],
            "action": row[2],
            "date": row[3].isoformat() if row[3] else None,
            "stage": row[4],
        }
        for row in leads_needing_action.all()
    ]

    # Content
    content_batches_total = await db.scalar(
        select(func.count()).select_from(ContentBatch)
    ) or 0

    batches_in_review = await db.scalar(
        select(func.count()).select_from(ContentBatch).where(
            ContentBatch.status == "review"
        )
    ) or 0

    items_generated_24h = await db.scalar(
        select(func.count()).select_from(ContentItem).where(
            ContentItem.created_at >= yesterday
        )
    ) or 0

    # Tasks
    pending_tasks = await db.scalar(
        select(func.count()).select_from(AgentTask).where(
            AgentTask.status.in_(["pending", "running"])
        )
    ) or 0

    return {
        "timestamp": now.isoformat(),
        "clients": {
            "active": active_clients,
            "mrr": str(total_mrr) if total_mrr else "0",
        },
        "leads": {
            "pipeline": pipeline,
            "pipeline_value": str(pipeline_value) if pipeline_value else "0",
            "activities_24h": recent_lead_activities,
            "upcoming_actions": upcoming_actions,
        },
        "content": {
            "total_batches": content_batches_total,
            "in_review": batches_in_review,
            "items_generated_24h": items_generated_24h,
        },
        "tasks": {
            "pending": pending_tasks,
        },
    }


async def generate_briefing(db: AsyncSession) -> dict:
    """Generate a daily briefing using Claude Haiku for speed/cost."""
    metrics = await gather_metrics(db)

    prompt = f"""Aquí tienes las métricas de negocio de hoy para VULKRAN OS (agencia de transformación digital):

```json
{json.dumps(metrics, ensure_ascii=False, indent=2)}
```

Genera un briefing ejecutivo diario con estas secciones:
1. **Resumen** (2-3 frases del estado general)
2. **Clientes** (MRR, estado)
3. **Pipeline de ventas** (leads por etapa, valor, acciones pendientes)
4. **Contenido** (batches en revisión, producción últimas 24h)
5. **Acciones prioritarias** (máximo 3 tareas concretas para hoy)

Sé conciso, directo y orientado a la acción. Usa español.
"""

    try:
        response = await call_claude(
            messages=[{"role": "user", "content": prompt}],
            system=(
                "Eres el asistente ejecutivo de una agencia digital. "
                "Generas briefings diarios concisos y accionables. "
                "Siempre en español, tono profesional pero directo."
            ),
            model=settings.fast_model,  # Use Haiku for speed/cost
            max_tokens=1500,
        )
        briefing_text = extract_text(response)

        return {
            "briefing": briefing_text,
            "metrics": metrics,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": settings.fast_model,
        }

    except Exception as e:
        logger.exception("Failed to generate daily briefing")
        return {
            "briefing": f"Error generating briefing: {e}",
            "metrics": metrics,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": True,
        }
