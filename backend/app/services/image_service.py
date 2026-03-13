"""VULKRAN OS — AI image generation service via FAL.ai."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FAL_API = "https://queue.fal.run/fal-ai/flux-pro/v1.1"
FAL_STATUS = "https://queue.fal.run/fal-ai/flux-pro/v1.1/requests"


async def generate_image(
    prompt: str,
    image_size: str = "landscape_16_9",
    num_images: int = 1,
    safety_tolerance: int = 2,
) -> dict:
    """Generate an image via FAL.ai Flux Pro.

    Args:
        prompt: Text description of the image to generate.
        image_size: One of landscape_16_9, portrait_9_16, square, square_hd.
        num_images: Number of images to generate (1-4).
        safety_tolerance: 1 (strict) to 5 (permissive).

    Returns dict with "images" list containing {"url", "content_type"}.
    """
    if not settings.fal_api_key:
        logger.warning("FAL_API_KEY not set — image generation skipped")
        return {"images": [], "status": "skipped", "reason": "no_api_key"}

    headers = {
        "Authorization": f"Key {settings.fal_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "image_size": image_size,
        "num_images": num_images,
        "safety_tolerance": safety_tolerance,
        "output_format": "jpeg",
        "enable_safety_checker": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Submit to queue
        response = await client.post(FAL_API, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # If synchronous response (unlikely for flux-pro)
        if "images" in data:
            return data

        # Poll for result
        request_id = data.get("request_id")
        if not request_id:
            return {"images": [], "status": "error", "reason": "no_request_id"}

        status_url = f"{FAL_STATUS}/{request_id}/status"
        result_url = f"{FAL_STATUS}/{request_id}"

        for _ in range(60):  # Max 60 polls (2 minutes)
            import asyncio
            await asyncio.sleep(2)

            status_resp = await client.get(status_url, headers=headers)
            status_data = status_resp.json()

            if status_data.get("status") == "COMPLETED":
                result_resp = await client.get(result_url, headers=headers)
                result_resp.raise_for_status()
                return result_resp.json()

            if status_data.get("status") in ("FAILED", "CANCELLED"):
                return {"images": [], "status": "failed", "reason": str(status_data)}

    return {"images": [], "status": "timeout"}


async def generate_brand_image(
    description: str,
    brand_colors: list[str] | None = None,
    style: str = "professional",
) -> dict:
    """Generate a brand-consistent image.

    Builds an enhanced prompt with brand guidelines.
    """
    color_hint = ""
    if brand_colors:
        color_hint = f", color palette: {', '.join(brand_colors)}"

    enhanced_prompt = (
        f"{description}. "
        f"Style: {style}, high quality, professional photography{color_hint}. "
        f"Clean composition, modern design, suitable for social media marketing."
    )

    return await generate_image(enhanced_prompt)
