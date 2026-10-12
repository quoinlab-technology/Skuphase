"""School-user feedback submission and personal ticket history."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.support import FeedbackMessage, FeedbackTicket
from app.schemas.auth import CurrentUser
from app.schemas.support import FeedbackCreate
from app.services.notifications import create_notification
from app.services.audit import record_audit_event

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
    await record_audit_event(
        db,
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
        school_id=current_user.school_id,
        action="feedback.ticket_created",
        target_type="feedback_ticket",
        target_id=ticket.id,
        summary="Submitted a support ticket.",
        metadata={"category": request.category, "severity": request.severity},
    )
    # Notify the submitter so the event is visible in the durable inbox even
    # before the platform support queue is implemented in the UI.
    await create_notification(
        db,
        recipient_user_id=current_user.user_id,
        school_id=current_user.school_id,
        kind="feedback_received",
        title="Feedback received",
        body="Your feedback has been recorded. The SkuPhase team will review it.",
        target_url=f"/app/feedback/{ticket.id}",
        payload={"ticket_id": str(ticket.id)},
        email_requested=True,
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


@router.get("/{ticket_id}", response_model=dict, tags=["Feedback"])
async def get_my_feedback(
    ticket_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return one caller-owned ticket and its public support conversation."""
    ticket = await db.scalar(
        select(FeedbackTicket).where(
            FeedbackTicket.id == ticket_id,
            FeedbackTicket.requester_user_id == current_user.user_id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Feedback ticket not found")
    messages = await db.execute(
        select(FeedbackMessage)
        .where(FeedbackMessage.ticket_id == ticket.id, FeedbackMessage.is_internal.is_(False))
        .order_by(FeedbackMessage.created_at.asc())
    )
    return {
        "ticket": {
            "ticket_id": str(ticket.id),
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category,
            "severity": ticket.severity,
            "status": ticket.status,
            "page_url": ticket.page_url,
            "created_at": ticket.created_at.isoformat(),
            "resolution_note": ticket.resolution_note,
        },
        "messages": [
            {"message_id": str(item.id), "body": item.body, "created_at": item.created_at.isoformat()}
            for item in messages.scalars().all()
        ],
    }
