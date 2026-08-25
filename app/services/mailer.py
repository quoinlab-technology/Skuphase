"""Email delivery with pluggable providers.

Providers:
- "smtp"    : Gmail SMTP via App Password (MVP default).
- "resend"  : Resend HTTP API (implemented now; activate by setting
              MAIL_PROVIDER=resend and RESEND_API_KEY once the sending
              domain is verified).

If a provider is unconfigured, send_email returns False and logs the
skipped delivery — auth flows must never fail because mail is down.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage

import httpx

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def _send_smtp(to: str, subject: str, html: str) -> bool:
    """Deliver via SMTP (Gmail App Password)."""
    import aiosmtplib

    settings = get_settings()
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "SMTP mail not configured (SMTP_USER/SMTP_PASSWORD missing); "
            "skipped email to=%s subject=%r",
            to,
            subject,
        )
        return False

    from_addr = settings.mail_from or settings.smtp_user
    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to
    message["Subject"] = subject
    message.set_content("Please view this email in an HTML-capable client.")
    message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
    return True


async def _send_resend(to: str, subject: str, html: str) -> bool:
    """Deliver via Resend HTTP API."""
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning(
            "Resend mail not configured (RESEND_API_KEY missing); "
            "skipped email to=%s subject=%r",
            to,
            subject,
        )
        return False

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.mail_from or "SkuPhase <onboarding@resend.dev>",
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        response.raise_for_status()
    return True


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email using the configured provider.

    Returns True when delivered; False when skipped/unavailable.
    Raises nothing — callers decide whether failures are fatal (they usually
    are not: tokens are already persisted before mailing).
    """
    settings = get_settings()
    try:
        if settings.mail_provider == "resend":
            return await _send_resend(to, subject, html)
        return await _send_smtp(to, subject, html)
    except Exception:
        logger.exception("Email delivery failed to=%s subject=%r", to, subject)
        return False
