"""VULKRAN OS — Audio/video transcription service using Faster-Whisper.

Adapted from VideoFlow v2 whisper_service.py pattern:
- Uses ProcessPoolExecutor to avoid blocking the event loop
- Outputs timestamped segments for auto-populating moment slots
"""

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)

_transcription_pool = ProcessPoolExecutor(max_workers=2, max_tasks_per_child=4)


def _transcribe_sync(
    file_path: str,
    language: str = "es",
    model_size: str = "base",
) -> dict:
    """
    Blocking transcription function — runs in a separate process.

    Returns:
        dict with keys: segments, full_text
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments_iter, info = model.transcribe(
        file_path,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments = []
    full_text_parts = []

    for seg in segments_iter:
        segment = {
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
        }
        segments.append(segment)
        full_text_parts.append(seg.text.strip())

    return {
        "segments": segments,
        "full_text": " ".join(full_text_parts),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
    }


async def transcribe_audio(
    file_path: str,
    language: str = "es",
    model_size: str = "base",
) -> dict:
    """
    Transcribe an audio/video file asynchronously.

    Args:
        file_path: Path to audio/video file
        language: Language code (e.g. "es", "en")
        model_size: Whisper model size (tiny, base, small, medium, large)

    Returns:
        dict with segments (timestamped), full_text, language, duration
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info("Starting transcription: %s (lang=%s, model=%s)", file_path, language, model_size)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _transcription_pool,
        _transcribe_sync,
        file_path,
        language,
        model_size,
    )

    logger.info(
        "Transcription complete: %d segments, %.1fs duration",
        len(result["segments"]),
        result["duration"],
    )

    return result
