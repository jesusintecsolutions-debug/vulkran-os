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


class WorkerSettings:
    functions = [health_check]
    cron_jobs = [
        cron(health_check, minute={0, 30}),  # every 30 min
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300  # 5 min per job
