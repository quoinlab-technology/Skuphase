"""Operational observability endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.document import SchoolDocument
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
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database_unhealthy: {exc}") from exc

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
    summary="Queue and generation stats",
    description="School-scoped processing and exam status counters for ops visibility.",
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

    documents_pending_result = await db.execute(
        select(func.count())
        .select_from(SchoolDocument)
        .where(
            and_(
                SchoolDocument.school_id == school_id,
                SchoolDocument.processing_status.in_(["pending", "in_progress"]),
            )
        )
    )
    documents_failed_result = await db.execute(
        select(func.count())
        .select_from(SchoolDocument)
        .where(
            and_(
                SchoolDocument.school_id == school_id,
                SchoolDocument.processing_status == "failed",
            )
        )
    )
    exams_generating_result = await db.execute(
        select(func.count())
        .select_from(Exam)
        .where(
            and_(
                Exam.school_id == school_id,
                Exam.status == "draft",
            )
        )
    )
    exams_under_review_result = await db.execute(
        select(func.count())
        .select_from(Exam)
        .where(
            and_(
                Exam.school_id == school_id,
                Exam.status == "under_review",
            )
        )
    )
    exams_approved_result = await db.execute(
        select(func.count())
        .select_from(Exam)
        .where(
            and_(
                Exam.school_id == school_id,
                Exam.status == "approved",
            )
        )
    )
    exams_failed_24h_result = await db.execute(
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
        "documents": {
            "pending_or_in_progress": documents_pending_result.scalar_one(),
            "failed_total": documents_failed_result.scalar_one(),
        },
        "exams": {
            "generating_draft": exams_generating_result.scalar_one(),
            "under_review": exams_under_review_result.scalar_one(),
            "approved": exams_approved_result.scalar_one(),
            "failed_last_24h": exams_failed_24h_result.scalar_one(),
        },
    }
