"""Authenticated durable notification inbox endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.support import Notification
from app.schemas.auth import CurrentUser

router = APIRouter()


@router.get("", response_model=dict, tags=["Notifications"])
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(25, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    conditions = [Notification.recipient_user_id == current_user.user_id, Notification.archived_at.is_(None)]
    if unread_only:
        conditions.append(Notification.read_at.is_(None))
    rows = await db.execute(
        select(Notification).where(*conditions).order_by(Notification.created_at.desc()).limit(limit)
    )
    unread = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.recipient_user_id == current_user.user_id,
            Notification.archived_at.is_(None),
            Notification.read_at.is_(None),
        )
    )
    return {
        "unread": int(unread or 0),
        "notifications": [
            {
                "notification_id": str(item.id),
                "kind": item.kind,
                "title": item.title,
                "body": item.body,
                "severity": item.severity,
                "target_url": item.target_url,
                "is_read": item.read_at is not None,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows.scalars().all()
        ],
    }


@router.post("/{notification_id}/read", response_model=dict, tags=["Notifications"])
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.recipient_user_id == current_user.user_id)
        .values(read_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"message": "Notification marked as read."}


@router.post("/read-all", response_model=dict, tags=["Notifications"])
async def mark_all_notifications_read(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(Notification.recipient_user_id == current_user.user_id, Notification.read_at.is_(None))
        .values(read_at=now, updated_at=now)
    )
    await db.commit()
    return {"message": "Notifications marked as read.", "updated": result.rowcount or 0}
