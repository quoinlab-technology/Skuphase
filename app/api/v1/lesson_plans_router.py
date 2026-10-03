"""Scheme-grounded lesson planning API."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.curriculum import SchemeOfWork
from app.models.lesson_plan import LessonPlan
from app.schemas.lesson_plan import LessonPlanCreate, LessonPlanUpdate, LessonPlanResponse

router = APIRouter()


def _can_plan(user: User) -> bool:
    return user.role in {"teacher", "school_admin"} or user.account_type == "individual_teacher"


@router.post("", response_model=LessonPlanResponse, status_code=201)
async def create_lesson_plan(
    request: LessonPlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    if not _can_plan(current_user):
        raise HTTPException(status_code=403, detail="Only teachers and school administrators can create lesson plans")
    scheme = await db.scalar(
        select(SchemeOfWork).where(
            SchemeOfWork.id == request.scheme_id,
            SchemeOfWork.curriculum_id == request.curriculum_id,
        )
    )
    if scheme is None:
        raise HTTPException(status_code=422, detail="The selected scheme week does not belong to the curriculum")
    plan = LessonPlan(
        school_id=current_user.school_id,
        created_by_user_id=current_user.user_id,
        curriculum_id=request.curriculum_id,
        scheme_id=request.scheme_id,
        term=scheme.term,
        week_number=scheme.week_number,
        title=request.title,
        learning_objectives=request.learning_objectives or list(scheme.subtopics or []),
        activities=request.activities,
        resources=request.resources,
        assessment_notes=request.assessment_notes,
        status="draft",
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("", response_model=list[LessonPlanResponse])
async def list_lesson_plans(
    status: str | None = Query(None, pattern="^(draft|submitted|approved|returned)$"),
    week_number: int | None = Query(None, ge=1, le=52),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    if not _can_plan(current_user):
        raise HTTPException(status_code=403, detail="You do not have access to lesson plans")
    query = select(LessonPlan).where(LessonPlan.school_id == current_user.school_id)
    if status:
        query = query.where(LessonPlan.status == status)
    if week_number:
        query = query.where(LessonPlan.week_number == week_number)
    result = await db.execute(query.order_by(LessonPlan.week_number, LessonPlan.created_at.desc()))
    return list(result.scalars().all())


@router.patch("/{lesson_plan_id}", response_model=LessonPlanResponse)
async def update_lesson_plan(
    lesson_plan_id: UUID,
    request: LessonPlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    if not _can_plan(current_user):
        raise HTTPException(status_code=403, detail="You do not have access to lesson plans")
    plan = await db.scalar(select(LessonPlan).where(LessonPlan.id == lesson_plan_id, LessonPlan.school_id == current_user.school_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    data = request.model_dump(exclude_unset=True)
    if "status" in data and data["status"] == "approved" and current_user.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only a school administrator can approve lesson plans")
    for key, value in data.items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{lesson_plan_id}", status_code=204)
async def delete_lesson_plan(
    lesson_plan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    if not _can_plan(current_user):
        raise HTTPException(status_code=403, detail="You do not have access to lesson plans")
    plan = await db.scalar(select(LessonPlan).where(LessonPlan.id == lesson_plan_id, LessonPlan.school_id == current_user.school_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    await db.delete(plan)
    await db.commit()
