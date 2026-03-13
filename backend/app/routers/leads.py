"""VULKRAN OS — Leads/CRM API endpoints."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.lead import Lead, LeadActivity
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    StageChangeRequest,
    ActivityCreate,
    ActivityResponse,
    PipelineStats,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])

VALID_STAGES = ["new", "contacted", "meeting", "proposal", "negotiation", "won", "lost"]


# ──────────────────────────────────────────────
# Leads CRUD
# ──────────────────────────────────────────────


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    stage: str | None = None,
    source: str | None = None,
    search: str | None = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List leads with optional filters."""
    query = select(Lead).order_by(Lead.created_at.desc())
    if stage:
        query = query.where(Lead.stage == stage)
    if source:
        query = query.where(Lead.source == source)
    if search:
        query = query.where(
            Lead.name.ilike(f"%{search}%") | Lead.company.ilike(f"%{search}%")
        )
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    body: LeadCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new lead."""
    lead = Lead(
        name=body.name,
        company=body.company,
        email=body.email,
        phone=body.phone,
        source=body.source,
        estimated_value=body.estimated_value,
        notes=body.notes,
        tags=body.tags,
        owner_id=user.id,
        stage="new",
    )
    db.add(lead)
    await db.flush()

    # Log creation activity
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type="note",
        description=f"Lead creado: {lead.name}" + (f" ({lead.company})" if lead.company else ""),
        created_by=user.id,
    )
    db.add(activity)
    await db.flush()

    return lead


@router.get("/pipeline", response_model=PipelineStats)
async def pipeline_stats(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get pipeline overview stats."""
    now = datetime.now(timezone.utc)

    total = await db.scalar(select(func.count()).select_from(Lead)) or 0

    # Count by stage
    result = await db.execute(
        select(Lead.stage, func.count()).group_by(Lead.stage)
    )
    by_stage = {row[0]: row[1] for row in result.all()}

    # Total estimated value of active leads
    total_value = await db.scalar(
        select(func.sum(Lead.estimated_value)).where(
            Lead.stage.notin_(["won", "lost"])
        )
    )

    # Won/lost this month
    won_this_month = await db.scalar(
        select(func.count()).select_from(Lead).where(
            Lead.stage == "won",
            extract("month", Lead.updated_at) == now.month,
            extract("year", Lead.updated_at) == now.year,
        )
    ) or 0

    lost_this_month = await db.scalar(
        select(func.count()).select_from(Lead).where(
            Lead.stage == "lost",
            extract("month", Lead.updated_at) == now.month,
            extract("year", Lead.updated_at) == now.year,
        )
    ) or 0

    return PipelineStats(
        total_leads=total,
        by_stage=by_stage,
        total_value=total_value,
        won_this_month=won_this_month,
        lost_this_month=lost_this_month,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Update lead fields."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "stage" and value not in VALID_STAGES:
            raise HTTPException(400, f"Invalid stage: {value}")
        setattr(lead, field, value)

    await db.flush()
    return lead


@router.post("/{lead_id}/stage", response_model=LeadResponse)
async def change_stage(
    lead_id: uuid.UUID,
    body: StageChangeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Move lead to a new pipeline stage."""
    if body.stage not in VALID_STAGES:
        raise HTTPException(400, f"Invalid stage: {body.stage}")

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    old_stage = lead.stage
    lead.stage = body.stage

    # Log stage change
    activity = LeadActivity(
        lead_id=lead.id,
        activity_type="stage_change",
        description=f"Etapa: {old_stage} → {body.stage}" + (f" | {body.notes}" if body.notes else ""),
        metadata_={"from_stage": old_stage, "to_stage": body.stage},
        created_by=user.id,
    )
    db.add(activity)
    await db.flush()

    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    await db.delete(lead)
    await db.flush()


# ──────────────────────────────────────────────
# Activities
# ──────────────────────────────────────────────


@router.get("/{lead_id}/activities", response_model=list[ActivityResponse])
async def list_activities(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(
        select(LeadActivity)
        .where(LeadActivity.lead_id == lead_id)
        .order_by(LeadActivity.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.post("/{lead_id}/activities", response_model=ActivityResponse, status_code=201)
async def add_activity(
    lead_id: uuid.UUID,
    body: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Log an activity for a lead."""
    # Verify lead exists
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Lead not found")

    activity = LeadActivity(
        lead_id=lead_id,
        activity_type=body.activity_type,
        description=body.description,
        metadata_=body.metadata,
        created_by=user.id,
    )
    db.add(activity)
    await db.flush()
    return activity
