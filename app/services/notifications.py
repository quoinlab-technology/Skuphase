"""Durable in-app notifications and optional email delivery queue."""

import html
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.support import Notification
from app.models.user import User
from app.services.mailer import send_email


async def create_notification(
    db: AsyncSession,
    *,
    recipient_user_id,
    kind: str,
    title: str,
    body: str,
    severity: str = "info",
    target_url: str | None = None,
    school_id=None,
    payload: dict | None = None,
    email_requested: bool = False,
) -> Notification:
    """Persist an in-app notification and optionally queue an email copy."""
    item = Notification(
        recipient_user_id=recipient_user_id,
        school_id=school_id,
        kind=kind,
        title=title,
        body=body,
        severity=severity,
        target_url=target_url,
        payload=payload or {},
        email_status="pending" if email_requested else "not_requested",
        email_run_at=datetime.now(timezone.utc) if email_requested else None,
    )
    db.add(item)
    await db.flush()
    return item


async def process_pending_notification_emails(session_maker, limit: int = 10) -> int:
    """Claim and deliver a bounded batch of notification email copies.

    In-app notifications are committed independently and are never removed if
    SMTP/Resend is unavailable. Failed deliveries are retried with the same
    bounded backoff policy as generation jobs, then remain visibly failed for
    platform operators to investigate.
    """
    now = datetime.now(timezone.utc)
    max_attempts = max(1, int(get_settings().background_retry_attempts))
    async with session_maker() as db:
        result = await db.execute(
            select(Notification, User.email)
            .join(User, User.id == Notification.recipient_user_id)
            .where(
                Notification.email_status == "pending",
                (Notification.email_run_at.is_(None) | (Notification.email_run_at <= now)),
            )
            .order_by(Notification.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        claimed = list(result.all())
        for item, _email in claimed:
            item.email_status = "sending"
            item.email_attempts = (item.email_attempts or 0) + 1
            item.updated_at = now
        await db.commit()

    delivered = 0
    for item, email in claimed:
        try:
            sent = await send_email(
                to=email,
                subject=item.title,
                html=f"<h2>{html.escape(item.title)}</h2><p>{html.escape(item.body).replace(chr(10), '<br>')}</p>",
            )
            error = None if sent else "Email provider unavailable or not configured."
        except Exception as exc:  # defensive: mailer itself normally returns False
            sent = False
            error = str(exc)[:2000]
        async with session_maker() as db:
            current = await db.scalar(select(Notification).where(Notification.id == item.id))
            if current is None:
                continue
            if sent:
                current.email_status = "sent"
                current.email_sent_at = datetime.now(timezone.utc)
                current.email_last_error = None
                delivered += 1
            elif current.email_attempts < max_attempts:
                delay = max(2.0, float(get_settings().background_retry_base_delay_seconds)) * (2 ** (current.email_attempts - 1))
                current.email_status = "pending"
                current.email_run_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                current.email_last_error = error
            else:
                current.email_status = "failed"
                current.email_last_error = error
            current.updated_at = datetime.now(timezone.utc)
            await db.commit()
    return delivered
