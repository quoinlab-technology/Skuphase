"""Operational observability endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.exam import Exam
from app.models.user import User

router = APIRouter()


@router.get(
    "/health",
    response_model=dict,
    summary="Operational health check",
    description="Health endpoint for internal monitoring.",
    tags=["Operations"],
)
async def ops_health(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return service and database health."""
    try:
        await db.execute(select(1))
    except Exception:
        raise HTTPException(status_code=503, detail="database_unhealthy")

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "database": "healthy",
        },
    }


@router.get(
    "/stats",
    response_model=dict,
    summary="Generation stats",
    description="School-scoped exam status counters for ops visibility.",
    tags=["Operations"],
)
async def ops_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return school-scoped operational counters."""
    if current_user.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only school administrators can view ops stats")

    school_id = current_user.school_id
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    status_counts_result = await db.execute(
        select(Exam.status, func.count())
        .where(Exam.school_id == school_id)
        .group_by(Exam.status)
    )
    status_counts = {row[0]: row[1] for row in status_counts_result.all()}

    failed_24h_result = await db.execute(
        select(func.count())
        .select_from(Exam)
        .where(
            and_(
                Exam.school_id == school_id,
                Exam.status == "failed",
                Exam.created_at >= since_24h,
            )
        )
    )

    return {
        "school_id": str(school_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exams": {
            "generating_draft": status_counts.get("draft", 0),
            "under_review": status_counts.get("under_review", 0),
            "approved": status_counts.get("approved", 0),
            "failed_last_24h": failed_24h_result.scalar_one(),
        },
    }
