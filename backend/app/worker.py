"""VULKRAN OS — ARQ async task worker."""

import logging

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def startup(ctx: dict) -> None:
    logger.info("VULKRAN worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("VULKRAN worker shutting down")


async def health_check(ctx: dict) -> str:
    """Periodic health check task."""
    logger.info("Worker health check OK")
    return "ok"


async def daily_briefing_job(ctx: dict) -> str:
    """Generate daily briefing and send notification to admin."""
    from app.database import async_session
    from app.services.daily_briefing import generate_briefing
    from app.models import User, Notification
    from sqlalchemy import select

    logger.info("Generating daily briefing...")

    try:
        async with async_session() as db:
            result = await generate_briefing(db)

            admins = await db.execute(
                select(User).where(User.role == "admin", User.is_active.is_(True))
            )
            for admin in admins.scalars().all():
                notif = Notification(
                    user_id=admin.id,
                    title="Briefing Diario",
                    body=result["briefing"][:500] if result.get("briefing") else "Briefing generado",
                    action_url="/briefing",
                )
                db.add(notif)

            await db.commit()
            logger.info("Daily briefing generated and notifications sent")
            return "ok"

    except Exception as e:
        logger.exception("Daily briefing job failed: %s", e)
        return f"error: {e}"


async def process_recurring_invoices(ctx: dict) -> str:
    """Generate recurring invoices that are due."""
    from app.database import async_session
    from app.models.fiscal import RecurringInvoice
    from app.models.accounting import Invoice
    from sqlalchemy import select
    from datetime import date, timedelta
    import json

    logger.info("Processing recurring invoices...")

    try:
        async with async_session() as db:
            today = date.today()
            result = await db.execute(
                select(RecurringInvoice).where(
                    RecurringInvoice.is_active.is_(True),
                    RecurringInvoice.next_issue_date <= today,
                )
            )
            recurring = result.scalars().all()

            count = 0
            for rec in recurring:
                template = rec.template_data or {}
                invoice = Invoice(
                    client_id=rec.client_id,
                    concept=template.get("concept", "Servicio recurrente"),
                    amount=template.get("amount", 0),
                    vat_rate=template.get("vat_rate", 21),
                    status="draft",
                )
                db.add(invoice)

                # Advance next_issue_date
                freq = rec.frequency or "monthly"
                if freq == "monthly":
                    rec.next_issue_date = today + timedelta(days=30)
                elif freq == "quarterly":
                    rec.next_issue_date = today + timedelta(days=90)
                elif freq == "yearly":
                    rec.next_issue_date = today + timedelta(days=365)
                else:
                    rec.next_issue_date = today + timedelta(days=30)

                count += 1

            await db.commit()
            logger.info("Generated %d recurring invoices", count)
            return f"ok: {count} invoices"

    except Exception as e:
        logger.exception("Recurring invoices job failed: %s", e)
        return f"error: {e}"


async def recalculate_lead_scores(ctx: dict) -> str:
    """Recalculate lead scores based on activity and pipeline data."""
    from app.database import async_session
    from app.models.crm import Lead
    from app.models.crm_advanced import LeadScore, Activity
    from sqlalchemy import select, func
    from datetime import datetime, timedelta

    logger.info("Recalculating lead scores...")

    try:
        async with async_session() as db:
            leads = await db.execute(select(Lead).where(Lead.stage != "lost"))
            count = 0

            for lead in leads.scalars().all():
                score = 30  # base score
                factors = {}

                # Stage progression bonus
                stage_scores = {
                    "new": 0, "contacted": 10, "meeting": 25,
                    "proposal": 40, "negotiation": 55, "won": 100,
                }
                stage_bonus = stage_scores.get(lead.stage, 0)
                score += stage_bonus
                factors["stage"] = stage_bonus

                # Activity recency
                recent = await db.execute(
                    select(func.count(Activity.id)).where(
                        Activity.lead_id == lead.id,
                        Activity.created_at >= datetime.utcnow() - timedelta(days=14),
                    )
                )
                activity_count = recent.scalar() or 0
                activity_bonus = min(activity_count * 5, 20)
                score += activity_bonus
                factors["recent_activity"] = activity_bonus

                # Estimated value bonus
                if lead.estimated_value:
                    try:
                        val = float(lead.estimated_value)
                        value_bonus = min(int(val / 500), 15)
                        score += value_bonus
                        factors["estimated_value"] = value_bonus
                    except (ValueError, TypeError):
                        pass

                score = min(score, 100)

                # Upsert score
                existing = await db.execute(
                    select(LeadScore).where(LeadScore.lead_id == lead.id)
                )
                ls = existing.scalar_one_or_none()
                if ls:
                    ls.score = score
                    ls.factors = factors
                else:
                    db.add(LeadScore(lead_id=lead.id, score=score, factors=factors))

                count += 1

            await db.commit()
            logger.info("Recalculated scores for %d leads", count)
            return f"ok: {count} leads"

    except Exception as e:
        logger.exception("Lead scoring job failed: %s", e)
        return f"error: {e}"


async def process_drip_campaigns(ctx: dict) -> str:
    """Process drip campaign enrollments and trigger next steps."""
    from app.database import async_session
    from app.models.crm_advanced import DripEnrollment, DripCampaign
    from app.models.email_system import EmailTemplate, EmailLog
    from sqlalchemy import select
    from datetime import datetime

    logger.info("Processing drip campaigns...")

    try:
        async with async_session() as db:
            now = datetime.utcnow()
            result = await db.execute(
                select(DripEnrollment).where(
                    DripEnrollment.status == "active",
                    DripEnrollment.next_action_at <= now,
                )
            )
            enrollments = result.scalars().all()

            count = 0
            for enrollment in enrollments:
                campaign_result = await db.execute(
                    select(DripCampaign).where(DripCampaign.id == enrollment.campaign_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                if not campaign or not campaign.is_active:
                    enrollment.status = "paused"
                    continue

                steps = campaign.steps or []
                if enrollment.current_step >= len(steps):
                    enrollment.status = "completed"
                    continue

                step = steps[enrollment.current_step]
                # Move to next step
                enrollment.current_step += 1
                if enrollment.current_step >= len(steps):
                    enrollment.status = "completed"
                else:
                    next_step = steps[enrollment.current_step]
                    delay_hours = next_step.get("delay_hours", 24)
                    enrollment.next_action_at = datetime.utcnow() + __import__("datetime").timedelta(hours=delay_hours)

                count += 1

            await db.commit()
            logger.info("Processed %d drip enrollments", count)
            return f"ok: {count} enrollments"

    except Exception as e:
        logger.exception("Drip campaigns job failed: %s", e)
        return f"error: {e}"


class WorkerSettings:
    functions = [
        health_check,
        daily_briefing_job,
        process_recurring_invoices,
        recalculate_lead_scores,
        process_drip_campaigns,
    ]
    cron_jobs = [
        cron(health_check, minute={0, 30}),  # every 30 min
        cron(daily_briefing_job, hour={7}, minute={0}),  # daily at 07:00 UTC (08:00 Madrid)
        cron(process_recurring_invoices, hour={6}, minute={0}),  # daily at 06:00 UTC
        cron(recalculate_lead_scores, hour={3}, minute={0}),  # daily at 03:00 UTC
        cron(process_drip_campaigns, minute={0, 15, 30, 45}),  # every 15 min
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 min per job
