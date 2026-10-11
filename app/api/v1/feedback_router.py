"""School-user feedback submission and personal ticket history."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.support import FeedbackTicket
from app.schemas.auth import CurrentUser
from app.schemas.support import FeedbackCreate
from app.services.notifications import create_notification

router = APIRouter()


@router.post("", response_model=dict, tags=["Feedback"])
async def create_feedback(
    request: FeedbackCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    ticket = FeedbackTicket(
        requester_user_id=current_user.user_id,
        school_id=current_user.school_id,
        category=request.category,
        severity=request.severity,
        subject=request.subject,
        description=request.description,
        page_url=request.page_url,
        context=request.context,
    )
    db.add(ticket)
    await db.flush()
    # Notify the submitter so the event is visible in the durable inbox even
    # before the platform support queue is implemented in the UI.
    await create_notification(
        db,
        recipient_user_id=current_user.user_id,
        school_id=current_user.school_id,
        kind="feedback_received",
        title="Feedback received",
        body="Your feedback has been recorded. The SkuPhase team will review it.",
        target_url="/app/feedback",
        payload={"ticket_id": str(ticket.id)},
    )
    await db.commit()
    return {"message": "Feedback submitted successfully.", "ticket_id": str(ticket.id), "status": ticket.status}


@router.get("/mine", response_model=dict, tags=["Feedback"])
async def list_my_feedback(
    limit: int = Query(25, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    rows = await db.execute(
        select(FeedbackTicket)
        .where(FeedbackTicket.requester_user_id == current_user.user_id)
        .order_by(FeedbackTicket.created_at.desc())
        .limit(limit)
    )
    return {
        "tickets": [
            {"ticket_id": str(item.id), "subject": item.subject, "category": item.category, "severity": item.severity, "status": item.status, "created_at": item.created_at.isoformat()}
            for item in rows.scalars().all()
        ]
    }
