"""VULKRAN OS — Content Engine service.

Generates content batches using Claude API, leveraging client brand config,
content templates, and user briefs to produce platform-ready content.
"""

import uuid
import logging
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, ContentTemplate, ContentBatch, ContentItem
from app.services.llm_bridge import call_claude, extract_text
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_generation_prompt(
    client: Client,
    template: ContentTemplate | None,
    brief: str | None,
    item_count: int,
    tone: str | None,
    language: str,
) -> str:
    """Build the content generation prompt from all available context."""

    parts = []

    # Brand context
    brand = client.brand_config or {}
    parts.append(f"## Cliente: {client.name}")
    parts.append(f"- Sector: {client.sector}")
    if brand.get("voice"):
        parts.append(f"- Voz de marca: {brand['voice']}")
    if brand.get("colors"):
        parts.append(f"- Colores: {brand['colors']}")
    if brand.get("values"):
        parts.append(f"- Valores: {brand['values']}")
    if brand.get("target_audience"):
        parts.append(f"- Público objetivo: {brand['target_audience']}")
    if client.notes:
        parts.append(f"- Notas: {client.notes}")

    # Template context
    if template:
        parts.append(f"\n## Plantilla: {template.name}")
        parts.append(f"- Plataforma: {template.platform}")
        parts.append(f"- Tipo: {template.content_type}")
        parts.append(f"\n### Instrucciones de la plantilla:\n{template.prompt_template}")
        if template.schema_fields:
            parts.append(f"\n### Campos requeridos por pieza:")
            parts.append(json.dumps(template.schema_fields, ensure_ascii=False, indent=2))

    # Brief
    if brief:
        parts.append(f"\n## Brief del usuario:\n{brief}")

    # Tone
    tone_str = tone or "profesional"
    parts.append(f"\n## Tono: {tone_str}")
    parts.append(f"## Idioma: {language}")

    # Output instructions
    schema_hint = ""
    if template and template.schema_fields:
        schema_hint = f"Cada item debe tener exactamente estos campos: {list(template.schema_fields.keys())}"
    else:
        schema_hint = (
            "Cada item debe tener al menos: headline, body, cta (call to action). "
            "Si es para redes sociales, incluye también: hashtags (array de strings)."
        )

    parts.append(f"""
## Instrucciones de salida:
Genera exactamente {item_count} piezas de contenido.
{schema_hint}

Responde SOLO con un JSON array válido. Sin texto adicional, sin markdown, sin ```json.
Cada elemento es un objeto con los campos indicados.
El contenido debe ser original, específico para la marca, y listo para publicar.
""")

    return "\n".join(parts)


async def generate_batch(
    db: AsyncSession,
    batch: ContentBatch,
    template_id: uuid.UUID | None = None,
    brief: str | None = None,
    item_count: int = 5,
    tone: str | None = None,
    language: str = "es",
    user_id: uuid.UUID | None = None,
) -> ContentBatch:
    """Generate content items for a batch using Claude.

    1. Load client brand config + optional template
    2. Build prompt
    3. Call Claude
    4. Parse JSON response into ContentItem records
    5. Update batch status
    """
    # Load client
    result = await db.execute(
        select(Client).where(Client.id == batch.client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        batch.status = "failed"
        batch.metadata_ = {"error": "Client not found"}
        return batch

    # Load template (optional)
    template = None
    tid = template_id or (batch.metadata_ or {}).get("template_id")
    if tid:
        result = await db.execute(
            select(ContentTemplate).where(ContentTemplate.id == uuid.UUID(str(tid)))
        )
        template = result.scalar_one_or_none()

    # Update batch status
    batch.status = "generating"
    batch.generated_by = user_id
    if brief:
        batch.brief = brief
    await db.flush()

    # Build prompt and call Claude
    prompt = _build_generation_prompt(
        client=client,
        template=template,
        brief=brief or batch.brief,
        item_count=item_count,
        tone=tone,
        language=language,
    )

    start_time = datetime.now(timezone.utc)

    try:
        response = await call_claude(
            messages=[{"role": "user", "content": prompt}],
            system=(
                "Eres un experto en marketing digital y creación de contenido. "
                "Generas contenido de alta calidad, específico para cada marca, "
                "listo para publicar en sus plataformas. "
                "SIEMPRE respondes con JSON válido, sin texto adicional."
            ),
            max_tokens=4096,
        )

        raw_text = extract_text(response)
        generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Parse JSON — handle potential markdown wrapping
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            # Remove ```json ... ``` wrapping
            lines = clean_text.split("\n")
            clean_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            clean_text = clean_text.strip()

        items_data = json.loads(clean_text)

        if not isinstance(items_data, list):
            items_data = [items_data]

        # Create ContentItem records
        for i, item_data in enumerate(items_data):
            item = ContentItem(
                batch_id=batch.id,
                template_id=template.id if template else None,
                position=i,
                content_data=item_data,
                status="generated",
            )
            db.add(item)

        batch.status = "review"
        batch.item_count = len(items_data)
        batch.metadata_ = {
            "model": response.get("model", settings.default_model),
            "input_tokens": response.get("usage", {}).get("input_tokens", 0),
            "output_tokens": response.get("usage", {}).get("output_tokens", 0),
            "generation_time_s": generation_time,
            "template_id": str(template.id) if template else None,
        }

        logger.info(
            "Generated %d items for batch %s (client: %s) in %.1fs",
            len(items_data), batch.id, client.name, generation_time,
        )

    except json.JSONDecodeError as e:
        logger.error("Failed to parse content JSON: %s | raw: %s", e, raw_text[:500])
        batch.status = "failed"
        batch.metadata_ = {"error": f"JSON parse error: {e}", "raw_output": raw_text[:2000]}

    except Exception as e:
        logger.exception("Content generation failed for batch %s", batch.id)
        batch.status = "failed"
        batch.metadata_ = {"error": str(e)}

    await db.flush()
    return batch


async def regenerate_item(
    db: AsyncSession,
    item: ContentItem,
    feedback: str | None = None,
) -> ContentItem:
    """Regenerate a single content item with optional feedback."""

    # Load batch and client for context
    result = await db.execute(
        select(ContentBatch).where(ContentBatch.id == item.batch_id)
    )
    batch = result.scalar_one()

    result = await db.execute(
        select(Client).where(Client.id == batch.client_id)
    )
    client = result.scalar_one()

    # Load template
    template = None
    if item.template_id:
        result = await db.execute(
            select(ContentTemplate).where(ContentTemplate.id == item.template_id)
        )
        template = result.scalar_one_or_none()

    prompt_parts = [
        f"Contenido original:\n{json.dumps(item.content_data, ensure_ascii=False, indent=2)}",
        f"\nCliente: {client.name} ({client.sector})",
    ]
    if feedback:
        prompt_parts.append(f"\nFeedback del usuario: {feedback}")
    prompt_parts.append(
        "\nRegenera esta pieza de contenido mejorándola según el feedback. "
        "Responde SOLO con el JSON del item (un objeto, no array)."
    )

    try:
        response = await call_claude(
            messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
            system=(
                "Eres un experto en marketing digital. "
                "Mejoras contenido existente según feedback. "
                "Responde SOLO con JSON válido."
            ),
            max_tokens=2048,
        )

        raw_text = extract_text(response)
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            clean_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        new_data = json.loads(clean_text)
        item.content_data = new_data
        item.status = "generated"
        item.edit_notes = feedback
        await db.flush()

    except Exception as e:
        logger.exception("Item regeneration failed for %s", item.id)
        item.edit_notes = f"Regeneration failed: {e}"

    return item
