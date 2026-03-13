"""VULKRAN OS — Seed content templates."""

SEED_TEMPLATES = [
    {
        "name": "Post Instagram",
        "slug": "instagram-post",
        "platform": "instagram",
        "content_type": "post",
        "prompt_template": (
            "Genera un post de Instagram para la marca. "
            "Debe ser visual, con un copy atractivo que invite a la interacción. "
            "Incluye un call-to-action claro y hashtags relevantes del sector."
        ),
        "schema_fields": {
            "headline": "string",
            "body": "string",
            "cta": "string",
            "hashtags": "array",
            "visual_description": "string",
        },
    },
    {
        "name": "Carousel Instagram",
        "slug": "instagram-carousel",
        "platform": "instagram",
        "content_type": "carousel",
        "prompt_template": (
            "Genera las slides de un carousel de Instagram educativo/informativo. "
            "Slide 1: gancho visual que capte atención. "
            "Slides 2-N: contenido de valor, una idea por slide. "
            "Última slide: CTA claro. "
            "Cada slide debe tener headline corto y texto conciso."
        ),
        "schema_fields": {
            "slide_number": "integer",
            "headline": "string",
            "body": "string",
            "visual_description": "string",
        },
    },
    {
        "name": "Post LinkedIn",
        "slug": "linkedin-post",
        "platform": "linkedin",
        "content_type": "post",
        "prompt_template": (
            "Genera un post de LinkedIn profesional para la marca. "
            "Tono experto pero accesible. Estructura: hook en primera línea, "
            "desarrollo con insights de valor, cierre con pregunta o CTA. "
            "Máximo 1300 caracteres. Sin hashtags excesivos (máximo 3-5)."
        ),
        "schema_fields": {
            "hook": "string",
            "body": "string",
            "cta": "string",
            "hashtags": "array",
        },
    },
    {
        "name": "Artículo Blog",
        "slug": "blog-article",
        "platform": "blog",
        "content_type": "article",
        "prompt_template": (
            "Genera un artículo de blog SEO-optimizado para la marca. "
            "Incluye: título H1 con keyword, meta description, "
            "estructura con H2s, introducción engaging, "
            "desarrollo con datos/ejemplos, conclusión con CTA. "
            "Extensión: 800-1200 palabras."
        ),
        "schema_fields": {
            "title": "string",
            "meta_description": "string",
            "sections": "array",
            "cta": "string",
            "keywords": "array",
        },
    },
    {
        "name": "Script Reel/Short",
        "slug": "reel-script",
        "platform": "instagram",
        "content_type": "reel_script",
        "prompt_template": (
            "Genera un guión para un Reel/Short de 30-60 segundos. "
            "Estructura: hook (primeros 3 seg), desarrollo (mostrar valor), "
            "cierre (CTA). Incluye indicaciones visuales y de texto en pantalla."
        ),
        "schema_fields": {
            "hook": "string",
            "scenes": "array",
            "on_screen_text": "array",
            "cta": "string",
            "audio_notes": "string",
        },
    },
    {
        "name": "Newsletter Email",
        "slug": "email-newsletter",
        "platform": "email",
        "content_type": "newsletter",
        "prompt_template": (
            "Genera un email de newsletter para suscriptores de la marca. "
            "Subject line que genere apertura (máx 50 chars). "
            "Preheader complementario. "
            "Cuerpo: saludo personalizable, contenido de valor, CTA principal. "
            "Tono cercano pero profesional."
        ),
        "schema_fields": {
            "subject": "string",
            "preheader": "string",
            "greeting": "string",
            "body": "string",
            "cta_text": "string",
            "cta_url_placeholder": "string",
        },
    },
]
