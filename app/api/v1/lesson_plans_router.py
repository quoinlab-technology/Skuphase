"""Scheme-grounded lesson planning API."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.school import SchoolSettings
from app.models.curriculum import SchemeOfWork, Curriculum
from app.models.lesson_plan import LessonPlan, WeeklyExercise, SyllabusCoverage
from app.schemas.lesson_plan import (LessonPlanCreate, LessonPlanUpdate, LessonPlanResponse,
    WeeklyExerciseCreate, WeeklyExerciseResponse, CoverageUpdate, CoverageResponse, LessonNoteRequest)
from app.services.lesson_delivery_service import generate_lesson_note, coverage_summary
from app.services.worksheet_export_service import export_worksheet_pdf
from app.services.curriculum_service import CurriculumService
from app.services.export_service import ExportService

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


@router.post("/exercises", response_model=WeeklyExerciseResponse, status_code=201)
async def create_weekly_exercise(request: WeeklyExerciseCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    if not _can_plan(current_user):
        raise HTTPException(status_code=403, detail="Only teachers and school administrators can create exercises")
    plan = await db.scalar(select(LessonPlan).where(LessonPlan.id == request.lesson_plan_id, LessonPlan.school_id == current_user.school_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    exercise = WeeklyExercise(school_id=current_user.school_id, lesson_plan_id=plan.id, created_by_user_id=current_user.user_id, title=request.title, instructions=request.instructions, questions=request.questions)
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    return exercise


@router.get("/exercises", response_model=list[WeeklyExerciseResponse])
async def list_weekly_exercises(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(WeeklyExercise).where(WeeklyExercise.school_id == current_user.school_id).order_by(WeeklyExercise.created_at.desc()))
    return list(result.scalars().all())


@router.post("/exercises/{exercise_id}/export", response_model=dict)
async def export_weekly_exercise(exercise_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    exercise = await db.scalar(select(WeeklyExercise).where(WeeklyExercise.id == exercise_id, WeeklyExercise.school_id == current_user.school_id))
    if exercise is None:
        raise HTTPException(status_code=404, detail="Weekly exercise not found")
    plan = await db.scalar(select(LessonPlan).where(LessonPlan.id == exercise.lesson_plan_id))
    school_settings = await db.scalar(select(SchoolSettings).where(SchoolSettings.school_id == current_user.school_id))
    filename = export_worksheet_pdf(
        export_dir=ExportService.EXPORT_DIR,
        title=exercise.title,
        subject="Curriculum Exercise",
        grade_level=plan.term if plan else "",
        instructions=exercise.instructions,
        questions=exercise.questions or [],
        school_logo_path=school_settings.logo_url if school_settings else None,
    )
    return {"filename": filename, "download_path": f"/api/v1/lesson-plans/exercises/{exercise_id}/download/{filename}"}


@router.get("/exercises/{exercise_id}/download/{filename}")
async def download_weekly_exercise(exercise_id: UUID, filename: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    exercise = await db.scalar(select(WeeklyExercise).where(WeeklyExercise.id == exercise_id, WeeklyExercise.school_id == current_user.school_id))
    if exercise is None or Path(filename).name != filename or not filename.endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Worksheet not found")
    path = ExportService.EXPORT_DIR / "worksheets" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Worksheet not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("/{lesson_plan_id}/lesson-note", response_model=LessonPlanResponse)
async def create_lesson_note(lesson_plan_id: UUID, request: LessonNoteRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    if request.lesson_plan_id != lesson_plan_id:
        raise HTTPException(status_code=422, detail="Lesson plan id mismatch")
    plan = await db.scalar(select(LessonPlan).where(LessonPlan.id == lesson_plan_id, LessonPlan.school_id == current_user.school_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    scheme = await db.scalar(select(SchemeOfWork).where(SchemeOfWork.id == plan.scheme_id))
    curriculum = await db.scalar(select(Curriculum).where(Curriculum.id == plan.curriculum_id))
    subject = getattr(curriculum, "subject_name", "the selected subject")
    class_level = getattr(curriculum, "class_level", "the selected class")
    plan.ai_lesson_note = await generate_lesson_note(topic=scheme.topic, subtopics=list(scheme.subtopics or []), class_level=class_level, subject=subject, guidance=request.additional_guidance)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/{lesson_plan_id}/coverage", response_model=CoverageResponse, status_code=201)
async def start_coverage(lesson_plan_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    plan = await db.scalar(select(LessonPlan).where(LessonPlan.id == lesson_plan_id, LessonPlan.school_id == current_user.school_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    existing = await db.scalar(select(SyllabusCoverage).where(SyllabusCoverage.school_id == current_user.school_id, SyllabusCoverage.scheme_id == plan.scheme_id, SyllabusCoverage.teacher_id == current_user.user_id))
    if existing:
        return existing
    row = SyllabusCoverage(school_id=current_user.school_id, curriculum_id=plan.curriculum_id, scheme_id=plan.scheme_id, teacher_id=current_user.user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/coverage/{coverage_id}", response_model=CoverageResponse)
async def update_coverage(coverage_id: UUID, request: CoverageUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    row = await db.scalar(select(SyllabusCoverage).where(SyllabusCoverage.id == coverage_id, SyllabusCoverage.school_id == current_user.school_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Coverage record not found")
    if request.status == "verified" and current_user.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only a school administrator can verify coverage")
    row.status, row.teacher_notes = request.status, request.teacher_notes
    if request.status == "completed":
        row.completed_at = datetime.now(timezone.utc)
    if request.status == "verified":
        row.verified_by_user_id, row.verified_at = current_user.user_id, datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/coverage", response_model=list[CoverageResponse])
async def list_coverage(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    """Return the school's coverage rows for the teaching workspace."""
    result = await db.execute(
        select(SyllabusCoverage)
        .where(SyllabusCoverage.school_id == current_user.school_id)
        .order_by(SyllabusCoverage.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/coverage/summary", response_model=dict)
async def coverage_dashboard(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(SyllabusCoverage).where(SyllabusCoverage.school_id == current_user.school_id))
    return coverage_summary([{"status": row.status} for row in result.scalars().all()])


@router.patch("/{lesson_plan_id}", response_model=LessonPlanResponse)
async def update_lesson_plan(lesson_plan_id: UUID, request: LessonPlanUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    if not _can_plan(current_user):
        raise HTTPException(status_code=403, detail="You do not have access to lesson plans")
    plan = await db.scalar(select(LessonPlan).where(LessonPlan.id == lesson_plan_id, LessonPlan.school_id == current_user.school_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    data = request.model_dump(exclude_unset=True)
    if data.get("status") == "approved" and current_user.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only a school administrator can approve lesson plans")
    for key, value in data.items():
        setattr(plan, key, value)
    if data.get("status") == "approved":
        plan.approved_by_user_id = current_user.user_id
        plan.approved_at = datetime.now(timezone.utc)
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
