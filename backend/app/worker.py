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


class WorkerSettings:
    functions = [health_check, daily_briefing_job]
    cron_jobs = [
        cron(health_check, minute={0, 30}),  # every 30 min
        cron(daily_briefing_job, hour={7}, minute={0}),  # daily at 07:00 UTC (08:00 Madrid)
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 min per job
