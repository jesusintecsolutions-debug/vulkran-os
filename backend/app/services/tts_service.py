"""VULKRAN OS — Google Cloud Text-to-Speech service for voiceover generation."""

import logging
import uuid
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def generate_voiceover(
    text: str,
    voice_name: str | None = None,
    language_code: str | None = None,
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
    output_dir: str | None = None,
    ssml: bool = False,
) -> dict:
    """
    Generate audio from text using Google Cloud TTS.

    Args:
        text: Plain text or SSML markup to synthesize.
        voice_name: Google TTS voice name (e.g. "es-ES-Wavenet-B").
        language_code: Language code (e.g. "es-ES").
        speaking_rate: Speed of speech (0.25 to 4.0, default 1.0).
        pitch: Pitch adjustment in semitones (-20.0 to 20.0, default 0.0).
        output_dir: Directory to save audio file. Defaults to data_dir/voiceovers.
        ssml: Whether `text` is SSML markup.

    Returns:
        dict with keys: audio_path, duration_seconds, voice_name, language_code
    """
    from google.cloud import texttospeech

    voice_name = voice_name or settings.google_tts_default_voice
    language_code = language_code or settings.google_tts_default_language

    # Set credentials if configured
    if settings.google_tts_credentials_path:
        import os
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.google_tts_credentials_path)

    client = texttospeech.TextToSpeechClient()

    if ssml:
        synthesis_input = texttospeech.SynthesisInput(ssml=text)
    else:
        synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
        pitch=pitch,
    )

    logger.info("Generating TTS: voice=%s, lang=%s, rate=%.1f, text_len=%d",
                voice_name, language_code, speaking_rate, len(text))

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    # Save audio file
    out_dir = Path(output_dir or f"{settings.data_dir}/voiceovers")
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"vo_{uuid.uuid4().hex[:12]}.mp3"
    audio_path = out_dir / filename
    audio_path.write_bytes(response.audio_content)

    # Estimate duration from MP3 file size (approximate: 128kbps MP3)
    file_size = audio_path.stat().st_size
    duration_seconds = file_size / (128 * 1000 / 8)  # rough estimate

    # Try to get accurate duration with mutagen if available
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(audio_path))
        duration_seconds = audio.info.length
    except Exception:
        pass

    logger.info("TTS generated: %s (%.1fs)", filename, duration_seconds)

    return {
        "audio_path": str(audio_path),
        "audio_url": f"/data/voiceovers/{filename}",
        "duration_seconds": round(duration_seconds, 2),
        "voice_name": voice_name,
        "language_code": language_code,
    }


async def list_voices(language_code: str | None = None) -> list[dict]:
    """List available Google TTS voices, optionally filtered by language."""
    from google.cloud import texttospeech

    if settings.google_tts_credentials_path:
        import os
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.google_tts_credentials_path)

    client = texttospeech.TextToSpeechClient()
    response = client.list_voices(language_code=language_code or "")

    voices = []
    for voice in response.voices:
        voices.append({
            "name": voice.name,
            "language_codes": list(voice.language_codes),
            "gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
            "natural_sample_rate": voice.natural_sample_rate_hertz,
        })

    return voices
