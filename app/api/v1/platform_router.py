"""Private company operations endpoints.

These endpoints are intentionally separate from school-admin operations.  Every
route requires an explicit active PlatformMembership and returns bounded,
aggregate data suitable for the internal console.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.permissions import (
    PLATFORM_ADMIN,
    PLATFORM_ANALYST,
    PLATFORM_CONTENT_OPERATOR,
    PLATFORM_OWNER,
    PLATFORM_SUPPORT,
    require_platform_roles,
)
from app.models.exam import Exam
from app.models.support import FeedbackMessage, FeedbackTicket
from app.schemas.support import FeedbackMessageCreate, FeedbackStatusUpdate
from app.services.notifications import create_notification
from app.models.job import GenerationJob
from app.models.platform import PlatformMembership
from app.models.school import School
from app.models.usage_log import UsageLog
from app.models.user import User

router = APIRouter()

READ_ROLES = (
    PLATFORM_OWNER,
    PLATFORM_ADMIN,
    PLATFORM_SUPPORT,
    PLATFORM_ANALYST,
    PLATFORM_CONTENT_OPERATOR,
)


async def _count(db: AsyncSession, model, *conditions) -> int:
    value = await db.scalar(select(func.count()).select_from(model).where(*conditions))
    return int(value or 0)


@router.get("/overview", response_model=dict, tags=["Platform Operations"])
async def platform_overview(
    membership: PlatformMembership = Depends(require_platform_roles(*READ_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return bounded cross-school health, usage, and queue summaries."""
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_30d = now - timedelta(days=30)
    active_schools = await _count(db, School, School.is_active.is_(True))
    total_schools = await _count(db, School)
    active_users = await _count(db, User, User.is_active.is_(True))
    verified_users = await _count(db, User, User.is_verified.is_(True))
    exams_24h = await _count(db, Exam, Exam.created_at >= since_24h)
    exams_30d = await _count(db, Exam, Exam.created_at >= since_30d)
    failed_exams_24h = await _count(db, Exam, Exam.status == "failed", Exam.created_at >= since_24h)
    pending_jobs = await _count(db, GenerationJob, GenerationJob.status == "pending")
    running_jobs = await _count(db, GenerationJob, GenerationJob.status == "running")
    failed_jobs = await _count(db, GenerationJob, GenerationJob.status == "failed")

    usage = await db.execute(
        select(
            func.coalesce(func.sum(UsageLog.tokens_used), 0),
            func.coalesce(func.sum(UsageLog.cost), 0.0),
            func.count(UsageLog.id),
        ).where(UsageLog.created_at >= since_30d)
    )
    tokens_30d, estimated_cost_30d, usage_events_30d = usage.one()

    trend_result = await db.execute(
        select(func.date(Exam.created_at), func.count())
        .where(Exam.created_at >= now - timedelta(days=7))
        .group_by(func.date(Exam.created_at))
        .order_by(func.date(Exam.created_at))
    )
    trend = [{"date": str(day), "count": int(count)} for day, count in trend_result.all()]

    return {
        "timestamp": now.isoformat(),
        "viewer_role": membership.role,
        "schools": {"total": total_schools, "active": active_schools},
        "users": {"active": active_users, "verified": verified_users},
        "exams": {
            "created_24h": exams_24h,
            "created_30d": exams_30d,
            "failed_24h": failed_exams_24h,
        },
        "jobs": {"pending": pending_jobs, "running": running_jobs, "failed": failed_jobs},
        "usage_30d": {
            "tokens": int(tokens_30d or 0),
            "estimated_cost": float(estimated_cost_30d or 0),
            "events": int(usage_events_30d or 0),
        },
        "exam_volume_7d": trend,
    }


@router.get("/schools", response_model=dict, tags=["Platform Operations"])
async def platform_schools(
    q: str | None = Query(None, max_length=100),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    membership: PlatformMembership = Depends(require_platform_roles(*READ_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return a bounded school directory for internal support and monitoring."""
    filters = []
    if q:
        filters.append(School.name.ilike(f"%{q.strip()}%"))
    total = await db.scalar(select(func.count()).select_from(School).where(*filters))
    rows = await db.execute(
        select(School)
        .where(*filters)
        .order_by(School.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    schools = []
    for school in rows.scalars().all():
        staff_count = await _count(db, User, User.school_id == school.id)
        exam_count = await _count(db, Exam, Exam.school_id == school.id, Exam.created_at >= datetime.now(timezone.utc) - timedelta(days=30))
        schools.append({
            "school_id": str(school.id),
            "name": school.name,
            "contact_email": school.contact_email,
            "is_active": school.is_active,
            "created_at": school.created_at.isoformat(),
            "staff_count": staff_count,
            "exams_30d": exam_count,
        })
    return {"total": int(total or 0), "offset": offset, "limit": limit, "schools": schools}


@router.get("/feedback", response_model=dict, tags=["Platform Operations"])
async def platform_feedback(
    status: str | None = Query(None, max_length=30),
    limit: int = Query(50, ge=1, le=100),
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return the bounded support queue for platform operators."""
    conditions = [FeedbackTicket.status == status] if status else []
    rows = await db.execute(
        select(FeedbackTicket).where(*conditions).order_by(FeedbackTicket.created_at.desc()).limit(limit)
    )
    return {
        "tickets": [
            {
                "ticket_id": str(item.id),
                "school_id": str(item.school_id) if item.school_id else None,
                "subject": item.subject,
                "category": item.category,
                "severity": item.severity,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows.scalars().all()
        ]
    }


@router.get("/members", response_model=dict, tags=["Platform Operations"])
async def platform_members(
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return active platform staff who can own support cases."""
    rows = await db.execute(
        select(User, PlatformMembership.role)
        .join(PlatformMembership, PlatformMembership.user_id == User.id)
        .where(PlatformMembership.is_active.is_(True))
        .order_by(User.full_name.asc(), User.email.asc())
    )
    return {
        "members": [
            {"user_id": str(user.id), "full_name": user.full_name, "email": user.email, "role": role}
            for user, role in rows.all()
        ]
    }


@router.get("/feedback/{ticket_id}", response_model=dict, tags=["Platform Operations"])
async def platform_feedback_detail(
    ticket_id: str,
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    ticket = await db.scalar(select(FeedbackTicket).where(FeedbackTicket.id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Feedback ticket not found")
    messages = await db.execute(
        select(FeedbackMessage).where(FeedbackMessage.ticket_id == ticket.id).order_by(FeedbackMessage.created_at.asc())
    )
    assigned_user = await db.scalar(select(User).where(User.id == ticket.assigned_to_user_id)) if ticket.assigned_to_user_id else None
    return {
        "ticket": {
            "ticket_id": str(ticket.id),
            "school_id": str(ticket.school_id) if ticket.school_id else None,
            "requester_user_id": str(ticket.requester_user_id) if ticket.requester_user_id else None,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category,
            "severity": ticket.severity,
            "status": ticket.status,
            "page_url": ticket.page_url,
            "created_at": ticket.created_at.isoformat(),
            "resolution_note": ticket.resolution_note,
            "assigned_to_user_id": str(ticket.assigned_to_user_id) if ticket.assigned_to_user_id else None,
            "assigned_to_name": assigned_user.full_name if assigned_user else None,
        },
        "messages": [
            {"message_id": str(item.id), "body": item.body, "is_internal": item.is_internal, "created_at": item.created_at.isoformat()}
            for item in messages.scalars().all()
        ],
    }


@router.patch("/feedback/{ticket_id}", response_model=dict, tags=["Platform Operations"])
async def update_platform_feedback(
    ticket_id: str,
    request: FeedbackStatusUpdate,
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    ticket = await db.scalar(select(FeedbackTicket).where(FeedbackTicket.id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Feedback ticket not found")
    ticket.status = request.status
    ticket.resolution_note = request.resolution_note
    if "assigned_to_user_id" in request.model_fields_set:
        assignee = None
        if request.assigned_to_user_id is not None:
            assignee = await db.scalar(
                select(User).join(PlatformMembership, PlatformMembership.user_id == User.id).where(
                    User.id == request.assigned_to_user_id,
                    PlatformMembership.is_active.is_(True),
                )
            )
            if assignee is None:
                raise HTTPException(status_code=400, detail="Assignee is not an active platform member")
        previous_assignee = ticket.assigned_to_user_id
        ticket.assigned_to_user_id = assignee.id if assignee else None
        if assignee and previous_assignee != assignee.id:
            await create_notification(
                db,
                recipient_user_id=assignee.id,
                kind="support_ticket_assigned",
                title="Support case assigned",
                body=f"'{ticket.subject}' has been assigned to you.",
                target_url=f"/internal/platform/support/{ticket.id}",
                payload={"ticket_id": str(ticket.id)},
            )
    if request.status in {"resolved", "closed"}:
        from datetime import datetime, timezone
        ticket.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    if ticket.requester_user_id:
        await create_notification(
            db,
            recipient_user_id=ticket.requester_user_id,
            school_id=ticket.school_id,
            kind="support_ticket_updated",
            title="Feedback update",
            body=f"Your report '{ticket.subject}' is now {request.status.replace('_', ' ')}.",
            target_url="/app/feedback",
            payload={"ticket_id": str(ticket.id), "status": request.status},
        )
    await db.commit()
    return {"message": "Support ticket updated.", "status": ticket.status}


@router.post("/feedback/{ticket_id}/messages", response_model=dict, tags=["Platform Operations"])
async def add_platform_feedback_message(
    ticket_id: str,
    request: FeedbackMessageCreate,
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    ticket = await db.scalar(select(FeedbackTicket).where(FeedbackTicket.id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Feedback ticket not found")
    message = FeedbackMessage(ticket_id=ticket.id, author_user_id=membership.user_id, body=request.body, is_internal=request.is_internal)
    db.add(message)
    if not request.is_internal and ticket.requester_user_id:
        await create_notification(
            db,
            recipient_user_id=ticket.requester_user_id,
            school_id=ticket.school_id,
            kind="support_ticket_reply",
            title="Support replied to your feedback",
            body=request.body[:240],
            target_url="/app/feedback",
            payload={"ticket_id": str(ticket.id)},
        )
    await db.commit()
    return {"message": "Support message added."}
