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
from app.models.support import FeedbackMessage, FeedbackTicket, Notification
from app.schemas.support import FeedbackMessageCreate, FeedbackStatusUpdate
from app.services.notifications import create_notification
from app.models.job import GenerationJob
from app.models.platform import PlatformMembership
from app.models.school import School
from app.models.usage_log import UsageLog
from app.models.user import User
from app.models.audit import AuditEvent
from app.services.audit import record_audit_event
from app.config.settings import get_settings

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
    pending_email = await _count(db, Notification, Notification.email_status.in_({"pending", "sending"}))
    failed_email = await _count(db, Notification, Notification.email_status == "failed")

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
        "notifications": {"email_pending": pending_email, "email_failed": failed_email},
        "usage_30d": {
            "tokens": int(tokens_30d or 0),
            "estimated_cost": float(estimated_cost_30d or 0),
            "events": int(usage_events_30d or 0),
        },
        "exam_volume_7d": trend,
    }


@router.get("/jobs", response_model=dict, tags=["Platform Operations"])
async def platform_jobs(
    status: str | None = Query(None, max_length=20),
    limit: int = Query(50, ge=1, le=100),
    membership: PlatformMembership = Depends(require_platform_roles(*READ_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return bounded generation queue state and sanitized errors."""
    conditions = [GenerationJob.status == status] if status else []
    counts_result = await db.execute(select(GenerationJob.status, func.count()).group_by(GenerationJob.status))
    rows = await db.execute(select(GenerationJob).where(*conditions).order_by(GenerationJob.created_at.desc()).limit(limit))
    return {
        "counts": {str(state): int(count) for state, count in counts_result.all()},
        "jobs": [{"job_id": str(job.id), "exam_id": str(job.exam_id), "school_id": str(job.school_id), "status": job.status, "attempts": job.attempts, "max_attempts": job.max_attempts, "last_error": (job.last_error or "")[:500] or None, "created_at": job.created_at.isoformat(), "run_at": job.run_at.isoformat() if job.run_at else None} for job in rows.scalars().all()],
    }


@router.post("/jobs/{job_id}/retry", response_model=dict, tags=["Platform Operations"])
async def retry_platform_job(
    job_id: str,
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Requeue a failed generation job after operator review."""
    job = await db.scalar(select(GenerationJob).where(GenerationJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status not in {"failed", "pending"}:
        raise HTTPException(status_code=409, detail="Only failed or pending jobs can be retried")
    job.status = "pending"
    job.run_at = datetime.now(timezone.utc)
    job.last_error = None
    await record_audit_event(db, actor_user_id=membership.user_id, actor_role=membership.role, school_id=job.school_id, action="platform.job_retried", target_type="generation_job", target_id=job.id, summary="Requeued a generation job for retry.")
    await db.commit()
    return {"message": "Generation job requeued.", "job_id": str(job.id), "status": job.status}


@router.get("/health", response_model=dict, tags=["Platform Operations"])
async def platform_health(
    membership: PlatformMembership = Depends(require_platform_roles(*READ_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return platform-scoped dependency and worker health."""
    checks = {"database": "healthy"}
    status = "healthy"
    try:
        await db.execute(select(1))
    except Exception:
        checks["database"] = "unhealthy"
        status = "degraded"
    pending = await _count(db, GenerationJob, GenerationJob.status == "pending")
    running = await _count(db, GenerationJob, GenerationJob.status == "running")
    failed = await _count(db, GenerationJob, GenerationJob.status == "failed")
    pending_email = await _count(db, Notification, Notification.email_status.in_({"pending", "sending"}))
    failed_email = await _count(db, Notification, Notification.email_status == "failed")
    return {"status": status, "timestamp": datetime.now(timezone.utc).isoformat(), "checks": checks, "queue": {"pending": pending, "running": running, "failed": failed}, "email_delivery": {"pending": pending_email, "failed": failed_email}, "provider_configuration": {"primary": get_settings().primary_llm_provider, "fallback": get_settings().fallback_llm_provider}}


@router.get("/usage", response_model=dict, tags=["Platform Operations"])
async def platform_usage(
    days: int = Query(30, ge=1, le=90),
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_ANALYST)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return bounded daily usage totals for company reporting."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(select(func.date(UsageLog.created_at), func.sum(UsageLog.tokens_used), func.sum(UsageLog.cost), func.count(UsageLog.id)).where(UsageLog.created_at >= since).group_by(func.date(UsageLog.created_at)).order_by(func.date(UsageLog.created_at)))
    daily = [{"date": str(day), "tokens": int(tokens or 0), "estimated_cost": float(cost or 0), "events": int(events)} for day, tokens, cost, events in result.all()]
    return {"days": days, "daily": daily, "totals": {"tokens": sum(item["tokens"] for item in daily), "estimated_cost": sum(item["estimated_cost"] for item in daily), "events": sum(item["events"] for item in daily)}}


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


@router.get("/schools/{school_id}", response_model=dict, tags=["Platform Operations"])
async def platform_school_detail(
    school_id: str,
    membership: PlatformMembership = Depends(require_platform_roles(*READ_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return a bounded operational profile for one school."""
    school = await db.scalar(select(School).where(School.id == school_id))
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    since_30d = datetime.now(timezone.utc) - timedelta(days=30)
    staff_total = await _count(db, User, User.school_id == school.id)
    active_staff = await _count(db, User, User.school_id == school.id, User.is_active.is_(True))
    verified_staff = await _count(db, User, User.school_id == school.id, User.is_verified.is_(True))
    exams_30d = await _count(db, Exam, Exam.school_id == school.id, Exam.created_at >= since_30d)
    failed_jobs = await _count(db, GenerationJob, GenerationJob.school_id == school.id, GenerationJob.status == "failed")
    open_tickets = await _count(db, FeedbackTicket, FeedbackTicket.school_id == school.id, FeedbackTicket.status.not_in({"resolved", "closed"}))
    usage = await db.execute(
        select(func.coalesce(func.sum(UsageLog.tokens_used), 0), func.coalesce(func.sum(UsageLog.cost), 0.0), func.count(UsageLog.id))
        .where(UsageLog.school_id == school.id, UsageLog.created_at >= since_30d)
    )
    tokens, cost, usage_events = usage.one()
    return {
        "school": {"school_id": str(school.id), "name": school.name, "contact_email": school.contact_email, "contact_phone": school.contact_phone, "is_active": school.is_active, "created_at": school.created_at.isoformat()},
        "users": {"total": staff_total, "active": active_staff, "verified": verified_staff},
        "exams_30d": exams_30d,
        "failed_jobs": failed_jobs,
        "open_support_cases": open_tickets,
        "usage_30d": {"tokens": int(tokens or 0), "estimated_cost": float(cost or 0), "events": int(usage_events or 0)},
    }


@router.get("/users", response_model=dict, tags=["Platform Operations"])
async def platform_users(
    q: str | None = Query(None, max_length=100),
    school_id: str | None = Query(None, max_length=80),
    active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT, PLATFORM_ANALYST)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return a bounded cross-school user directory without credentials."""
    conditions = []
    if q:
        needle = f"%{q.strip()}%"
        conditions.append((User.full_name.ilike(needle)) | (User.email.ilike(needle)))
    if school_id:
        conditions.append(User.school_id == school_id)
    if active is not None:
        conditions.append(User.is_active.is_(active))
    total = await db.scalar(select(func.count()).select_from(User).where(*conditions))
    rows = await db.execute(
        select(User, School.name).join(School, School.id == User.school_id).where(*conditions)
        .order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    return {"total": int(total or 0), "offset": offset, "limit": limit, "users": [
        {"user_id": str(user.id), "full_name": user.full_name, "email": user.email, "school_id": str(user.school_id), "school_name": school_name, "role": user.role, "is_active": user.is_active, "is_verified": user.is_verified, "last_login": user.last_login.isoformat() if user.last_login else None}
        for user, school_name in rows.all()
    ]}


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


@router.get("/notifications/delivery", response_model=dict, tags=["Platform Operations"])
async def platform_notification_delivery(
    status: str | None = Query(None, max_length=20),
    limit: int = Query(50, ge=1, le=100),
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return bounded notification-email delivery state for operator recovery."""
    conditions = [Notification.email_status != "not_requested"]
    if status:
        conditions.append(Notification.email_status == status)
    counts_result = await db.execute(
        select(Notification.email_status, func.count())
        .where(Notification.email_status != "not_requested")
        .group_by(Notification.email_status)
    )
    rows = await db.execute(
        select(Notification, User.email)
        .join(User, User.id == Notification.recipient_user_id)
        .where(*conditions)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return {
        "counts": {str(state): int(count) for state, count in counts_result.all()},
        "deliveries": [
            {
                "notification_id": str(item.id),
                "recipient_email": email,
                "title": item.title,
                "status": item.email_status,
                "attempts": item.email_attempts,
                "last_error": (item.email_last_error or "")[:500] or None,
                "run_at": item.email_run_at.isoformat() if item.email_run_at else None,
                "sent_at": item.email_sent_at.isoformat() if item.email_sent_at else None,
                "created_at": item.created_at.isoformat(),
            }
            for item, email in rows.all()
        ],
    }


@router.post("/notifications/delivery/{notification_id}/retry", response_model=dict, tags=["Platform Operations"])
async def retry_notification_delivery(
    notification_id: str,
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_SUPPORT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Requeue a terminal notification email failure for immediate delivery."""
    item = await db.scalar(select(Notification).where(Notification.id == notification_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Notification delivery not found")
    if item.email_status != "failed":
        raise HTTPException(status_code=409, detail="Only failed notification emails can be retried")
    item.email_status = "pending"
    item.email_run_at = datetime.now(timezone.utc)
    item.email_last_error = None
    await record_audit_event(
        db,
        actor_user_id=membership.user_id,
        actor_role=membership.role,
        school_id=item.school_id,
        action="platform.notification_email_retried",
        target_type="notification",
        target_id=item.id,
        summary="Requeued a failed notification email.",
    )
    await db.commit()
    return {"message": "Notification email requeued.", "notification_id": str(item.id), "status": item.email_status}


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


@router.get("/audit-events", response_model=dict, tags=["Platform Operations"])
async def platform_audit_events(
    action: str | None = Query(None, max_length=100),
    actor_user_id: str | None = Query(None, max_length=80),
    success: bool | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    membership: PlatformMembership = Depends(require_platform_roles(PLATFORM_OWNER, PLATFORM_ADMIN, PLATFORM_ANALYST)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return bounded, sanitized audit events for internal investigation."""
    conditions = [AuditEvent.action == action] if action else []
    if actor_user_id:
        conditions.append(AuditEvent.actor_user_id == actor_user_id)
    if success is not None:
        conditions.append(AuditEvent.success.is_(success))
    if date_from:
        conditions.append(AuditEvent.created_at >= date_from)
    if date_to:
        conditions.append(AuditEvent.created_at <= date_to)
    rows = await db.execute(select(AuditEvent).where(*conditions).order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit))
    return {
        "offset": offset, "limit": limit,
        "events": [{
            "event_id": str(item.id), "action": item.action, "target_type": item.target_type,
            "target_id": item.target_id, "success": item.success, "actor_role": item.actor_role,
            "request_id": item.request_id, "summary": item.summary, "created_at": item.created_at.isoformat(),
        } for item in rows.scalars().all()],
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
                email_requested=True,
            )
    if request.status in {"resolved", "closed"}:
        from datetime import datetime, timezone
        ticket.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    await record_audit_event(
        db, actor_user_id=membership.user_id, actor_role=membership.role,
        school_id=ticket.school_id, action="platform.support_status_updated",
        target_type="feedback_ticket", target_id=ticket.id,
        summary=f"Updated support case status to {request.status}.",
        metadata={"status": request.status},
    )
    if ticket.requester_user_id:
        await create_notification(
            db,
            recipient_user_id=ticket.requester_user_id,
            school_id=ticket.school_id,
            kind="support_ticket_updated",
            title="Feedback update",
            body=f"Your report '{ticket.subject}' is now {request.status.replace('_', ' ')}.",
            target_url=f"/app/feedback/{ticket.id}",
            payload={"ticket_id": str(ticket.id), "status": request.status},
            email_requested=True,
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
    await record_audit_event(
        db, actor_user_id=membership.user_id, actor_role=membership.role,
        school_id=ticket.school_id, action="platform.support_message_added",
        target_type="feedback_ticket", target_id=ticket.id,
        summary="Added an internal support note." if request.is_internal else "Sent a support reply.",
        metadata={"is_internal": request.is_internal},
    )
    if not request.is_internal and ticket.requester_user_id:
        await create_notification(
            db,
            recipient_user_id=ticket.requester_user_id,
            school_id=ticket.school_id,
            kind="support_ticket_reply",
            title="Support replied to your feedback",
            body=request.body[:240],
            target_url=f"/app/feedback/{ticket.id}",
            payload={"ticket_id": str(ticket.id)},
            email_requested=True,
        )
    await db.commit()
    return {"message": "Support message added."}
