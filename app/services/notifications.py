"""Durable notification creation helpers."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import Notification


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
) -> Notification:
    """Persist an in-app notification; email delivery is a later worker concern."""
    item = Notification(
        recipient_user_id=recipient_user_id,
        school_id=school_id,
        kind=kind,
        title=title,
        body=body,
        severity=severity,
        target_url=target_url,
        payload=payload or {},
    )
    db.add(item)
    await db.flush()
    return item
