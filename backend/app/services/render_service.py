"""VULKRAN OS — Remotion render pipeline service.

Adapted from VideoFlow v2 render pattern:
- Serializes project props to JSON temp file
- Launches `npx remotion render` via subprocess
- Parses progress from CLI output via regex
- Reports progress via callback (for WebSocket/SSE)
- Runs in ThreadPoolExecutor (Windows-safe, non-blocking)
"""

import asyncio
import json
import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.content_engine import VideoProject, VideoMoment, RenderJob

logger = logging.getLogger(__name__)
settings = get_settings()

_render_pool = ThreadPoolExecutor(
    max_workers=settings.render_max_workers,
    thread_name_prefix="remotion-render",
)

REMOTION_DIR = Path(settings.remotion_path)
RENDERS_DIR = Path(settings.data_dir) / "renders"


def _parse_progress(line: str) -> int | None:
    """Extract percentage from Remotion CLI output line."""
    m = re.search(r"(\d{1,3})%", line)
    if m:
        val = int(m.group(1))
        if 0 <= val <= 100:
            return val
    return None


def _run_render_sync(
    job_id: str,
    composition_id: str,
    output_path: str,
    props: dict,
    progress_callback=None,
) -> dict:
    """
    Blocking render function — runs in a thread.

    Args:
        job_id: Unique render job ID
        composition_id: Remotion composition to render (e.g. "MomentRenderer")
        output_path: Full path for output MP4
        props: Remotion input props dict
        progress_callback: Optional callable(job_id, data_dict) for real-time updates

    Returns:
        dict with status, output_path, error
    """
    import subprocess

    def notify(data: dict):
        if progress_callback:
            try:
                progress_callback(job_id, data)
            except Exception:
                pass

    notify({"type": "progress", "stage": "bundling", "progress": 0, "status": "bundling"})

    # Write props to temp JSON file
    output_path_abs = Path(output_path).resolve()
    output_path_abs.parent.mkdir(parents=True, exist_ok=True)
    props_file = output_path_abs.parent / f"props_{job_id[:8]}.json"
    props_file.write_text(json.dumps(props), encoding="utf-8")

    # Build command — forward slashes for cross-platform
    props_file_str = str(props_file).replace("\\", "/")
    output_path_str = str(output_path_abs).replace("\\", "/")

    cmd = (
        f'npx remotion render "{composition_id}" "{output_path_str}"'
        f' --props="{props_file_str}"'
        f' --overwrite --concurrency {settings.render_concurrency} --log=verbose'
    )

    all_logs: list[str] = []
    result = {"status": "error", "progress": 0, "error": None}

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(REMOTION_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )

        for raw_line in iter(proc.stdout.readline, ""):
            line = raw_line.strip()
            if not line:
                continue
            all_logs.append(line)

            pct = _parse_progress(line)
            if pct is not None:
                result["progress"] = pct
                notify({"type": "progress", "stage": "rendering", "progress": pct, "status": "rendering"})
            elif any(kw in line.lower() for kw in ("bundle", "bundl")):
                notify({"type": "progress", "stage": "bundling", "progress": 0, "status": "bundling"})

        proc.wait()

        # Cleanup props file
        try:
            props_file.unlink(missing_ok=True)
        except Exception:
            pass

        if proc.returncode == 0 and Path(output_path).exists():
            result["status"] = "done"
            result["progress"] = 100
            notify({"type": "progress", "stage": "done", "progress": 100, "status": "done"})
        else:
            tail = "\n".join(all_logs[-20:]) if all_logs else "(no output)"
            result["error"] = f"Remotion CLI exited with code {proc.returncode}\n\n{tail}"
            notify({"type": "error", "status": "error", "message": result["error"]})

    except Exception as exc:
        result["error"] = str(exc)
        notify({"type": "error", "status": "error", "message": result["error"]})

    return result


async def start_render(
    db: AsyncSession,
    project_id: str,
    quality: str = "1080p",
    progress_callback=None,
) -> RenderJob:
    """
    Launch a render job for a video project.

    1. Loads project + moments from DB
    2. Serializes props for Remotion
    3. Creates RenderJob record
    4. Submits to thread pool
    5. Updates RenderJob on completion
    """
    from app.models.content_engine import VideoProject, VideoMoment, VideoTemplate

    project = await db.get(VideoProject, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Load moments
    result = await db.execute(
        select(VideoMoment)
        .where(VideoMoment.project_id == project.id)
        .order_by(VideoMoment.sort_order)
    )
    moments = result.scalars().all()
    if not moments:
        raise ValueError("No moments to render")

    # Load template for slot schema defaults
    template = None
    if project.template_id:
        template = await db.get(VideoTemplate, project.template_id)

    # Resolution
    res_map = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "2k": (2560, 1440),
        "4k": (3840, 2160),
        "9:16": (1080, 1920),
    }
    width, height = res_map.get(quality, (1920, 1080))

    # Build props
    moments_data = []
    for m in moments:
        moment_dict = {
            "id": str(m.id),
            "template_id": template.slug if template else "default",
            "slot_data": m.slots_data or {},
            "duration": m.duration_frames or int((template.duration_per_moment if template else 5.0) * project.fps),
            "transition_type": m.transition_type,
            "transition_duration": m.transition_duration,
        }
        if m.voiceover_url:
            moment_dict["voiceover_url"] = m.voiceover_url
        moments_data.append(moment_dict)

    composition_id = "MomentRendererVertical" if quality == "9:16" else "MomentRenderer"

    props = {
        "moments": moments_data,
        "fps": project.fps,
        "width": width,
        "height": height,
    }
    if project.voiceover_url:
        props["audioSrc"] = project.voiceover_url

    # Create RenderJob
    job = RenderJob(
        project_id=project.id,
        status="pending",
        quality=quality,
        started_at=datetime.now(timezone.utc),
    )
    output_filename = f"project_{str(project.id)[:8]}_{str(job.id)[:8]}.mp4"
    output_path = str(RENDERS_DIR / output_filename)
    job.output_path = output_path
    job.output_filename = output_filename

    db.add(job)
    await db.flush()

    # Update project status
    project.status = "rendering"
    await db.flush()

    job_id = str(job.id)

    # Submit to thread pool
    loop = asyncio.get_event_loop()

    def _on_complete(future):
        """Update DB when render completes (runs in main thread via callback)."""
        async def _update():
            from app.database import async_session
            async with async_session() as session:
                render_job = await session.get(RenderJob, uuid.UUID(job_id))
                proj = await session.get(VideoProject, project.id)
                if render_job:
                    result = future.result()
                    render_job.status = result["status"]
                    render_job.progress = result["progress"]
                    render_job.error_message = result.get("error")
                    render_job.completed_at = datetime.now(timezone.utc)
                    if result["status"] == "done" and proj:
                        proj.status = "done"
                        proj.render_url = f"/data/renders/{output_filename}"
                    elif result["status"] == "error" and proj:
                        proj.status = "error"
                    await session.commit()

        asyncio.run_coroutine_threadsafe(_update(), loop)

    future = _render_pool.submit(
        _run_render_sync,
        job_id,
        composition_id,
        output_path,
        props,
        progress_callback,
    )
    future.add_done_callback(_on_complete)

    await db.commit()

    return job


async def get_render_status(db: AsyncSession, job_id: str) -> dict | None:
    """Get current status of a render job."""
    job = await db.get(RenderJob, job_id)
    if not job:
        return None
    return {
        "id": str(job.id),
        "project_id": str(job.project_id),
        "status": job.status,
        "progress": job.progress,
        "quality": job.quality,
        "error_message": job.error_message,
        "output_filename": job.output_filename,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
