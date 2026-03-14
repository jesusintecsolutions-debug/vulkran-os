"""VULKRAN OS — Moment Director: LLM-driven video moment generation.

Adapted from VideoFlow v2 moment_director.py pattern:
- Uses Claude tool_use with `create_moment` tool to generate structured moments
- Takes client context, template, and creative brief as input
- Outputs array of moments with filled slot values
- Tracks user corrections to improve future generation
"""

import json
import logging
import uuid

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


CREATE_MOMENT_TOOL = {
    "name": "create_moment",
    "description": "Create a video moment/slide with specific content for each slot. Call this once per moment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {
                "type": "string",
                "description": "Main headline/title text for this moment",
            },
            "body": {
                "type": "string",
                "description": "Body/supporting text content",
            },
            "voiceover_text": {
                "type": "string",
                "description": "Narration script for voiceover (will be converted to speech via TTS)",
            },
            "bg_color": {
                "type": "string",
                "description": "Background color hex code (e.g. '#1a1a2e')",
            },
            "accent_color": {
                "type": "string",
                "description": "Accent/highlight color hex code",
            },
            "image_prompt": {
                "type": "string",
                "description": "Prompt for generating a background/featured image (if needed)",
            },
            "transition_type": {
                "type": "string",
                "enum": ["fade", "slide", "wipe", "flip", "none"],
                "description": "Transition to next moment",
            },
            "extra_slots": {
                "type": "object",
                "description": "Additional slot values specific to the template",
            },
        },
        "required": ["headline", "voiceover_text"],
    },
}


async def generate_moments(
    brief: str,
    template_slots: list[dict],
    client_context: dict | None = None,
    num_moments: int = 5,
    tone: str = "profesional",
    language: str = "es",
    corrections: list[dict] | None = None,
) -> list[dict]:
    """
    Generate video moments using Claude API with tool_use.

    Args:
        brief: Creative brief / instructions
        template_slots: List of SlotDefinition dicts from the template
        client_context: Client info (name, sector, brand_colors, etc.)
        num_moments: Number of moments to generate
        tone: Communication tone (profesional, casual, energetico, inspirador)
        language: Content language
        corrections: Previous user corrections for learning

    Returns:
        List of moment dicts with filled slot values
    """
    # Build slot description for the prompt
    slot_descriptions = []
    for slot in template_slots:
        desc = f"- {slot['key']} ({slot['type']}): {slot.get('label', slot['key'])}"
        if slot.get('required'):
            desc += " [REQUIRED]"
        if slot.get('options'):
            desc += f" Options: {', '.join(slot['options'])}"
        slot_descriptions.append(desc)

    slots_text = "\n".join(slot_descriptions) if slot_descriptions else "No specific slots defined."

    # Build context section
    context_text = ""
    if client_context:
        context_text = f"""
CONTEXTO DEL CLIENTE:
- Nombre: {client_context.get('name', 'N/A')}
- Sector: {client_context.get('sector', 'N/A')}
- Tono de marca: {client_context.get('tone', tone)}
- Colores de marca: {client_context.get('brand_colors', 'N/A')}
- Audiencia objetivo: {client_context.get('audience', 'N/A')}
"""

    # Build corrections section
    corrections_text = ""
    if corrections:
        corrections_text = "\nCORRECCIONES PREVIAS DEL USUARIO (aprende de ellas):\n"
        for c in corrections[-5:]:  # Last 5 corrections
            corrections_text += f"- Original: {c.get('original', '?')} → Corregido: {c.get('corrected', '?')}\n"

    system_prompt = f"""Eres un director creativo de vídeo para una agencia de marketing digital.
Tu trabajo es generar {num_moments} momentos/slides para un vídeo.

{context_text}

SLOTS DISPONIBLES EN LA PLANTILLA:
{slots_text}

INSTRUCCIONES:
- Genera exactamente {num_moments} momentos llamando a la herramienta `create_moment` una vez por momento
- Cada momento debe tener un texto de voiceover que suene natural al ser leído en voz alta
- Mantén un tono {tone} y coherente entre todos los momentos
- Idioma: {language}
- Los momentos deben contar una historia progresiva (introducción → desarrollo → cierre/CTA)
{corrections_text}

BRIEF DEL PROYECTO:
{brief}"""

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.fast_model,
                "max_tokens": 4096,
                "system": system_prompt,
                "tools": [CREATE_MOMENT_TOOL],
                "tool_choice": {"type": "any"},
                "messages": [
                    {
                        "role": "user",
                        "content": f"Genera {num_moments} momentos para este vídeo. Usa la herramienta create_moment para cada uno.",
                    }
                ],
            },
        )

    if response.status_code != 200:
        logger.error("Claude API error: %d %s", response.status_code, response.text[:500])
        raise RuntimeError(f"Claude API error: {response.status_code}")

    data = response.json()
    moments = []

    for block in data.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "create_moment":
            input_data = block.get("input", {})
            moment = {
                "slots_data": {
                    "headline": input_data.get("headline", ""),
                    "body": input_data.get("body", ""),
                    "bg_color": input_data.get("bg_color", "#1a1a2e"),
                    "accent_color": input_data.get("accent_color", "#7c3aed"),
                    **(input_data.get("extra_slots", {})),
                },
                "voiceover_text": input_data.get("voiceover_text", ""),
                "transition_type": input_data.get("transition_type", "fade"),
                "image_prompt": input_data.get("image_prompt"),
            }
            moments.append(moment)

    logger.info("Generated %d moments from brief (requested %d)", len(moments), num_moments)

    return moments
