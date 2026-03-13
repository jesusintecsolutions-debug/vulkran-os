"""VULKRAN OS — File upload/download endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import User, Client
from app.services.file_storage import FileStorage, FileStorageError, MAX_FILE_SIZE

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload/{client_id}")
async def upload_file(
    client_id: uuid.UUID,
    category: str = Query(
        ..., regex="^(brand|content|templates|invoices)$",
        description="File category: brand, content, templates, or invoices",
    ),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Upload a file to a client's storage."""
    # Verify client exists
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Read content
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    try:
        metadata = FileStorage.upload(
            client_slug=client.slug,
            category=category,
            filename=file.filename or "unnamed",
            content=content,
            mime_type=file.content_type,
        )
    except FileStorageError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "uploaded",
        "file": metadata,
    }


@router.get("/download/{path:path}")
async def download_file(
    path: str,
    user: User = Depends(get_current_user),
):
    """Download a file by its relative path."""
    result = FileStorage.get_file(path)
    if not result:
        raise HTTPException(status_code=404, detail="File not found")

    full_path, mime_type = result
    return FileResponse(
        path=str(full_path),
        media_type=mime_type,
        filename=full_path.name,
    )


@router.get("/list/{client_id}")
async def list_client_files(
    client_id: uuid.UUID,
    category: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List files for a client, optionally filtered by category."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    files = FileStorage.list_files(client.slug, category)
    return {"client": client.slug, "category": category or "all", "files": files}


@router.delete("/{path:path}")
async def delete_file(
    path: str,
    user: User = Depends(require_admin),
):
    """Delete a file by its relative path. Admin only."""
    if not FileStorage.delete_file(path):
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "deleted", "path": path}


@router.post("/init/{client_id}")
async def init_client_storage(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Create the standard directory structure for a client."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    dirs = FileStorage.ensure_client_structure(client.slug)
    return {"status": "initialized", **dirs}
