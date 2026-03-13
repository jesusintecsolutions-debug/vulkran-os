"""VULKRAN OS — Content Engine API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models import Client
from app.models.content import ContentTemplate, ContentBatch, ContentItem
from app.schemas.content import (
    TemplateCreate,
    TemplateResponse,
    BatchCreate,
    BatchGenerateRequest,
    BatchResponse,
    ItemResponse,
    ItemUpdate,
)
from app.services.content_engine import generate_batch, regenerate_item
from app.seeds.content_templates import SEED_TEMPLATES

router = APIRouter(prefix="/api/content", tags=["content"])


# ──────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List all active content templates, optionally filtered by platform."""
    query = select(ContentTemplate).where(ContentTemplate.is_active.is_(True))
    if platform:
        query = query.where(ContentTemplate.platform == platform)
    query = query.order_by(ContentTemplate.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin),
):
    """Create a new content template (admin only)."""
    template = ContentTemplate(**body.model_dump())
    db.add(template)
    await db.flush()
    return template


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(
        select(ContentTemplate).where(ContentTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(404, "Template not found")
    return template


# ──────────────────────────────────────────────
# Batches
# ──────────────────────────────────────────────


@router.get("/batches", response_model=list[BatchResponse])
async def list_batches(
    client_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List content batches, optionally filtered by client or status."""
    query = select(ContentBatch).order_by(ContentBatch.created_at.desc())
    if client_id:
        query = query.where(ContentBatch.client_id == client_id)
    if status:
        query = query.where(ContentBatch.status == status)
    query = query.limit(50)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/batches", response_model=BatchResponse, status_code=201)
async def create_batch(
    body: BatchCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new content batch (draft)."""
    # Verify client exists
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Client not found")

    batch = ContentBatch(
        client_id=body.client_id,
        title=body.title,
        brief=body.brief,
        platform=body.platform,
        status="draft",
        item_count=0,
    )
    db.add(batch)
    await db.flush()
    return batch


@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(
        select(ContentBatch).where(ContentBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")
    return batch


@router.post("/batches/{batch_id}/generate", response_model=BatchResponse)
async def generate_batch_content(
    batch_id: uuid.UUID,
    body: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Trigger content generation for a batch using Claude."""
    result = await db.execute(
        select(ContentBatch).where(ContentBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch.status not in ("draft", "failed"):
        raise HTTPException(400, f"Cannot generate: batch is '{batch.status}'")

    batch = await generate_batch(
        db=db,
        batch=batch,
        template_id=body.template_id,
        brief=body.brief,
        item_count=body.item_count,
        tone=body.tone,
        language=body.language,
        user_id=user.id,
    )

    return batch


@router.post("/batches/{batch_id}/approve", response_model=BatchResponse)
async def approve_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Approve a batch for publishing."""
    result = await db.execute(
        select(ContentBatch).where(ContentBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch.status != "review":
        raise HTTPException(400, f"Cannot approve: batch is '{batch.status}'")

    from datetime import datetime, timezone

    batch.status = "approved"
    batch.approved_by = user.id
    batch.approved_at = datetime.now(timezone.utc)

    # Also approve all items
    result = await db.execute(
        select(ContentItem).where(ContentItem.batch_id == batch.id)
    )
    for item in result.scalars().all():
        if item.status != "rejected":
            item.status = "approved"

    await db.flush()
    return batch


# ──────────────────────────────────────────────
# Items
# ──────────────────────────────────────────────


@router.get("/batches/{batch_id}/items", response_model=list[ItemResponse])
async def list_batch_items(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get all content items in a batch."""
    result = await db.execute(
        select(ContentItem)
        .where(ContentItem.batch_id == batch_id)
        .order_by(ContentItem.position)
    )
    return result.scalars().all()


@router.patch("/items/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: uuid.UUID,
    body: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Update a content item (edit content, change status, add notes)."""
    result = await db.execute(
        select(ContentItem).where(ContentItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")

    if body.content_data is not None:
        item.content_data = body.content_data
        item.status = "edited"
    if body.status is not None:
        item.status = body.status
    if body.edit_notes is not None:
        item.edit_notes = body.edit_notes

    await db.flush()
    return item


@router.post("/items/{item_id}/regenerate", response_model=ItemResponse)
async def regenerate_content_item(
    item_id: uuid.UUID,
    feedback: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Regenerate a single content item with optional feedback."""
    result = await db.execute(
        select(ContentItem).where(ContentItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")

    item = await regenerate_item(db=db, item=item, feedback=feedback)
    return item


# ──────────────────────────────────────────────
# Seed
# ──────────────────────────────────────────────


@router.post("/seed-templates", status_code=201)
async def seed_templates(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin),
):
    """Load seed content templates (admin only). Skips existing slugs."""
    created = 0
    for tpl_data in SEED_TEMPLATES:
        result = await db.execute(
            select(ContentTemplate).where(ContentTemplate.slug == tpl_data["slug"])
        )
        if result.scalar_one_or_none():
            continue
        db.add(ContentTemplate(**tpl_data))
        created += 1
    await db.flush()
    return {"created": created, "total_seeds": len(SEED_TEMPLATES)}
