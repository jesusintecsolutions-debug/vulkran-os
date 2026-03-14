"""VULKRAN OS — Content Engine render router.

Endpoints for video projects, moments, templates, rendering, TTS, and transcription.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.content_engine import (
    VideoTemplate,
    VideoProject,
    VideoMoment,
    RenderJob,
    VoiceoverJob,
    TranscriptionJob,
)
from app.auth import require_admin

router = APIRouter(prefix="/api/content-engine", tags=["content-engine"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TemplateCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    category: str = "general"
    client_id: str | None = None
    fps: int = 30
    width: int = 1920
    height: int = 1080
    duration_per_moment: float = 5.0
    slots_schema: list[dict]
    sfx_defaults: dict | None = None
    tags: list[str] | None = None


class ProjectCreate(BaseModel):
    client_id: str
    title: str
    description: str | None = None
    brief: str | None = None
    template_id: str | None = None


class MomentCreate(BaseModel):
    template_id: str | None = None
    sort_order: int = 0
    slots_data: dict = {}
    duration_frames: int | None = None
    transition_type: str = "fade"
    transition_duration: int = 15
    voiceover_text: str | None = None


class MomentUpdate(BaseModel):
    slots_data: dict | None = None
    sort_order: int | None = None
    duration_frames: int | None = None
    transition_type: str | None = None
    transition_duration: int | None = None
    voiceover_text: str | None = None


class RenderRequest(BaseModel):
    quality: str = "1080p"


class VoiceoverRequest(BaseModel):
    text: str
    voice_name: str | None = None
    language_code: str | None = None
    speaking_rate: float = 1.0
    pitch: float = 0.0
    ssml: bool = False
    moment_id: str | None = None


class GenerateMomentsRequest(BaseModel):
    brief: str
    num_moments: int = 5
    tone: str = "profesional"
    language: str = "es"


class TranscribeRequest(BaseModel):
    file_path: str
    language: str = "es"
    model_size: str = "base"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@router.get("/templates")
async def list_templates(
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    query = select(VideoTemplate).where(VideoTemplate.is_active.is_(True))
    if client_id:
        # Show global + client-specific templates
        query = query.where(
            (VideoTemplate.client_id == uuid.UUID(client_id)) | (VideoTemplate.client_id.is_(None))
        )
    query = query.order_by(VideoTemplate.name)
    result = await db.execute(query)
    templates = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "description": t.description,
            "category": t.category,
            "client_id": str(t.client_id) if t.client_id else None,
            "fps": t.fps,
            "width": t.width,
            "height": t.height,
            "duration_per_moment": t.duration_per_moment,
            "slots_schema": t.slots_schema,
            "sfx_defaults": t.sfx_defaults,
            "tags": t.tags,
            "thumbnail_url": t.thumbnail_url,
        }
        for t in templates
    ]


@router.post("/templates")
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    template = VideoTemplate(
        name=body.name,
        slug=body.slug,
        description=body.description,
        category=body.category,
        client_id=uuid.UUID(body.client_id) if body.client_id else None,
        fps=body.fps,
        width=body.width,
        height=body.height,
        duration_per_moment=body.duration_per_moment,
        slots_schema=body.slots_schema,
        sfx_defaults=body.sfx_defaults,
        tags=body.tags,
    )
    db.add(template)
    await db.flush()
    return {"id": str(template.id), "slug": template.slug}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@router.get("/projects")
async def list_projects(
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    query = select(VideoProject).order_by(VideoProject.created_at.desc())
    if client_id:
        query = query.where(VideoProject.client_id == uuid.UUID(client_id))
    result = await db.execute(query)
    projects = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "client_id": str(p.client_id),
            "title": p.title,
            "description": p.description,
            "status": p.status,
            "render_url": p.render_url,
            "thumbnail_url": p.thumbnail_url,
            "created_at": p.created_at.isoformat(),
        }
        for p in projects
    ]


@router.post("/projects")
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    project = VideoProject(
        client_id=uuid.UUID(body.client_id),
        title=body.title,
        description=body.description,
        brief=body.brief,
        template_id=uuid.UUID(body.template_id) if body.template_id else None,
    )
    # Inherit template dimensions if set
    if body.template_id:
        template = await db.get(VideoTemplate, uuid.UUID(body.template_id))
        if template:
            project.fps = template.fps
            project.width = template.width
            project.height = template.height

    db.add(project)
    await db.flush()
    return {"id": str(project.id), "status": project.status}


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    project = await db.get(VideoProject, uuid.UUID(project_id))
    if not project:
        raise HTTPException(404, "Project not found")

    # Load moments
    result = await db.execute(
        select(VideoMoment)
        .where(VideoMoment.project_id == project.id)
        .order_by(VideoMoment.sort_order)
    )
    moments = result.scalars().all()

    return {
        "id": str(project.id),
        "client_id": str(project.client_id),
        "title": project.title,
        "description": project.description,
        "brief": project.brief,
        "status": project.status,
        "template_id": str(project.template_id) if project.template_id else None,
        "fps": project.fps,
        "width": project.width,
        "height": project.height,
        "render_url": project.render_url,
        "voiceover_url": project.voiceover_url,
        "created_at": project.created_at.isoformat(),
        "moments": [
            {
                "id": str(m.id),
                "sort_order": m.sort_order,
                "template_id": str(m.template_id) if m.template_id else None,
                "slots_data": m.slots_data,
                "duration_frames": m.duration_frames,
                "transition_type": m.transition_type,
                "transition_duration": m.transition_duration,
                "voiceover_text": m.voiceover_text,
                "voiceover_url": m.voiceover_url,
            }
            for m in moments
        ],
    }


# ---------------------------------------------------------------------------
# Moments
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/moments")
async def add_moment(
    project_id: str,
    body: MomentCreate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    project = await db.get(VideoProject, uuid.UUID(project_id))
    if not project:
        raise HTTPException(404, "Project not found")

    moment = VideoMoment(
        project_id=project.id,
        template_id=uuid.UUID(body.template_id) if body.template_id else project.template_id,
        sort_order=body.sort_order,
        slots_data=body.slots_data,
        duration_frames=body.duration_frames,
        transition_type=body.transition_type,
        transition_duration=body.transition_duration,
        voiceover_text=body.voiceover_text,
    )
    db.add(moment)
    await db.flush()
    return {"id": str(moment.id), "sort_order": moment.sort_order}


@router.patch("/moments/{moment_id}")
async def update_moment(
    moment_id: str,
    body: MomentUpdate,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    moment = await db.get(VideoMoment, uuid.UUID(moment_id))
    if not moment:
        raise HTTPException(404, "Moment not found")

    if body.slots_data is not None:
        moment.slots_data = body.slots_data
    if body.sort_order is not None:
        moment.sort_order = body.sort_order
    if body.duration_frames is not None:
        moment.duration_frames = body.duration_frames
    if body.transition_type is not None:
        moment.transition_type = body.transition_type
    if body.transition_duration is not None:
        moment.transition_duration = body.transition_duration
    if body.voiceover_text is not None:
        moment.voiceover_text = body.voiceover_text

    await db.flush()
    return {"id": str(moment.id), "updated": True}


@router.delete("/moments/{moment_id}")
async def delete_moment(
    moment_id: str,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    moment = await db.get(VideoMoment, uuid.UUID(moment_id))
    if not moment:
        raise HTTPException(404, "Moment not found")
    await db.delete(moment)
    await db.flush()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# AI Generation (Moment Director)
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/generate-moments")
async def generate_moments_endpoint(
    project_id: str,
    body: GenerateMomentsRequest,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    """Use Claude to auto-generate moments from a brief."""
    from app.services.moment_director_service import generate_moments

    project = await db.get(VideoProject, uuid.UUID(project_id))
    if not project:
        raise HTTPException(404, "Project not found")

    # Get template slots schema
    template_slots = []
    if project.template_id:
        template = await db.get(VideoTemplate, project.template_id)
        if template:
            template_slots = template.slots_schema

    # Get client context
    from app.models.client import Client
    client = await db.get(Client, project.client_id)
    client_context = None
    if client:
        client_context = {
            "name": client.name,
            "sector": client.sector,
        }

    project.status = "generating"
    await db.flush()

    try:
        moments_data = await generate_moments(
            brief=body.brief or project.brief or project.title,
            template_slots=template_slots,
            client_context=client_context,
            num_moments=body.num_moments,
            tone=body.tone,
            language=body.language,
        )

        # Create moment records
        created = []
        for i, m_data in enumerate(moments_data):
            moment = VideoMoment(
                project_id=project.id,
                template_id=project.template_id,
                sort_order=i,
                slots_data=m_data["slots_data"],
                transition_type=m_data.get("transition_type", "fade"),
                voiceover_text=m_data.get("voiceover_text", ""),
            )
            db.add(moment)
            created.append(moment)

        project.status = "review"
        await db.flush()

        return {
            "project_id": str(project.id),
            "moments_generated": len(created),
            "status": "review",
        }

    except Exception as e:
        project.status = "error"
        await db.flush()
        raise HTTPException(500, f"Generation failed: {e}")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/render")
async def render_project(
    project_id: str,
    body: RenderRequest,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    """Launch a render job for a video project."""
    from app.services.render_service import start_render

    try:
        job = await start_render(db, project_id, quality=body.quality)
        return {
            "job_id": str(job.id),
            "project_id": project_id,
            "status": job.status,
            "quality": body.quality,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/renders/{job_id}/status")
async def render_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    """Get render job status."""
    from app.services.render_service import get_render_status
    status = await get_render_status(db, job_id)
    if not status:
        raise HTTPException(404, "Render job not found")
    return status


@router.get("/renders/{job_id}/download")
async def download_render(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download rendered MP4."""
    from pathlib import Path
    job = await db.get(RenderJob, uuid.UUID(job_id))
    if not job or not job.output_path:
        raise HTTPException(404, "Render not found")
    if not Path(job.output_path).exists():
        raise HTTPException(404, "Output file not found on disk")
    return FileResponse(
        path=job.output_path,
        filename=job.output_filename or "render.mp4",
        media_type="video/mp4",
    )


# ---------------------------------------------------------------------------
# TTS / Voiceover
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/voiceover")
async def generate_voiceover_endpoint(
    project_id: str,
    body: VoiceoverRequest,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    """Generate voiceover audio using Google Cloud TTS."""
    from app.services.tts_service import generate_voiceover

    project = await db.get(VideoProject, uuid.UUID(project_id))
    if not project:
        raise HTTPException(404, "Project not found")

    # Create job record
    vo_job = VoiceoverJob(
        project_id=project.id,
        moment_id=uuid.UUID(body.moment_id) if body.moment_id else None,
        text=body.text,
        voice_name=body.voice_name or "es-ES-Wavenet-B",
        language_code=body.language_code or "es-ES",
        speaking_rate=body.speaking_rate,
        pitch=body.pitch,
        status="generating",
    )
    db.add(vo_job)
    await db.flush()

    try:
        result = await generate_voiceover(
            text=body.text,
            voice_name=body.voice_name,
            language_code=body.language_code,
            speaking_rate=body.speaking_rate,
            pitch=body.pitch,
            ssml=body.ssml,
        )

        vo_job.audio_url = result["audio_url"]
        vo_job.duration_seconds = result["duration_seconds"]
        vo_job.status = "done"

        # Update moment or project with voiceover URL
        if body.moment_id:
            moment = await db.get(VideoMoment, uuid.UUID(body.moment_id))
            if moment:
                moment.voiceover_url = result["audio_url"]
        else:
            project.voiceover_url = result["audio_url"]

        await db.flush()

        return {
            "id": str(vo_job.id),
            "audio_url": result["audio_url"],
            "duration_seconds": result["duration_seconds"],
            "voice_name": result["voice_name"],
            "status": "done",
        }

    except Exception as e:
        vo_job.status = "error"
        vo_job.error_message = str(e)
        await db.flush()
        raise HTTPException(500, f"TTS generation failed: {e}")


@router.get("/voices")
async def list_voices(
    language: str | None = None,
    _ = Depends(require_admin),
):
    """List available Google TTS voices."""
    from app.services.tts_service import list_voices
    try:
        voices = await list_voices(language)
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(500, f"Failed to list voices: {e}")


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

@router.post("/transcribe")
async def transcribe_endpoint(
    body: TranscribeRequest,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin),
):
    """Transcribe an audio/video file."""
    from app.services.transcription_service import transcribe_audio

    job = TranscriptionJob(
        source_path=body.file_path,
        language=body.language,
        model_size=body.model_size,
        status="processing",
    )
    db.add(job)
    await db.flush()

    try:
        result = await transcribe_audio(
            file_path=body.file_path,
            language=body.language,
            model_size=body.model_size,
        )

        job.segments = result["segments"]
        job.full_text = result["full_text"]
        job.status = "done"
        await db.flush()

        return {
            "id": str(job.id),
            "segments": result["segments"],
            "full_text": result["full_text"],
            "duration": result["duration"],
            "language": result["language"],
            "status": "done",
        }

    except Exception as e:
        job.status = "error"
        job.error_message = str(e)
        await db.flush()
        raise HTTPException(500, f"Transcription failed: {e}")
