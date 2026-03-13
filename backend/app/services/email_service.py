"""VULKRAN OS — Email service via Resend API."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RESEND_API = "https://api.resend.com/emails"


async def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    from_email: str | None = None,
    reply_to: str | None = None,
    tags: list[dict] | None = None,
) -> dict:
    """Send an email via Resend API.

    Returns {"id": "email_id"} on success.
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — email not sent to %s", to)
        return {"id": None, "status": "skipped", "reason": "no_api_key"}

    recipients = [to] if isinstance(to, str) else to
    payload: dict = {
        "from": from_email or settings.email_from,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    if tags:
        payload["tags"] = tags

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(RESEND_API, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info("Email sent to %s — id: %s", recipients, result.get("id"))
        return result


# ── Email templates ──────────────────────────────────────


def render_notification_email(title: str, body: str, action_url: str | None = None) -> str:
    """Render a simple notification email."""
    action_html = ""
    if action_url:
        action_html = f"""
        <div style="text-align:center;margin:24px 0">
            <a href="{action_url}"
               style="background:#6d28d9;color:#fff;padding:12px 32px;
                      border-radius:8px;text-decoration:none;font-weight:600">
                Ver en VULKRAN OS
            </a>
        </div>"""

    return f"""
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;
                background:#0a0a0f;color:#e2e8f0;padding:32px;border-radius:12px;
                border:1px solid rgba(109,40,217,0.3)">
        <div style="text-align:center;margin-bottom:24px">
            <span style="font-size:20px;font-weight:700;color:#8b5cf6;letter-spacing:1px">
                VULKRAN OS
            </span>
        </div>
        <h2 style="color:#fff;font-size:18px;margin:0 0 12px">{title}</h2>
        <div style="color:#94a3b8;font-size:14px;line-height:1.6">{body}</div>
        {action_html}
        <hr style="border:none;border-top:1px solid rgba(109,40,217,0.2);margin:24px 0">
        <p style="color:#475569;font-size:12px;text-align:center">
            Enviado por VULKRAN OS — Tu asistente de negocio
        </p>
    </div>"""


def render_briefing_email(briefing_text: str, period: str) -> str:
    """Render the daily briefing email."""
    return render_notification_email(
        title=f"Briefing Diario — {period}",
        body=briefing_text.replace("\n", "<br>"),
        action_url=None,
    )


def render_invoice_email(
    client_name: str,
    invoice_number: str,
    total: str,
    due_date: str,
) -> str:
    """Render an invoice notification email."""
    return render_notification_email(
        title=f"Factura {invoice_number}",
        body=f"""
        Hola {client_name},<br><br>
        Te enviamos la factura <strong>{invoice_number}</strong> por un total de
        <strong>{total}€</strong>.<br>
        Fecha de vencimiento: <strong>{due_date}</strong>.<br><br>
        Si tienes alguna duda, no dudes en contactarnos.
        """,
    )


def render_lead_intro_email(lead_name: str, company: str | None, message: str) -> str:
    """Render an outreach email to a lead."""
    company_line = f" de {company}" if company else ""
    return render_notification_email(
        title=f"Hola {lead_name}{company_line}",
        body=message,
    )
