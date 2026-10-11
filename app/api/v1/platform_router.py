"""Private company operations endpoints.

These endpoints are intentionally separate from school-admin operations.  Every
route requires an explicit active PlatformMembership and returns bounded,
aggregate data suitable for the internal console.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
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
