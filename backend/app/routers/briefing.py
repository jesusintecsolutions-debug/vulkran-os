"""VULKRAN OS — Daily Briefing endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.services.daily_briefing import generate_briefing, gather_metrics

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.get("")
async def get_briefing(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Generate and return today's daily briefing."""
    return await generate_briefing(db)


@router.get("/metrics")
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get raw business metrics without AI summary."""
    return await gather_metrics(db)
