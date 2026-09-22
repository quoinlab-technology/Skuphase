"""Exam generation and management API endpoints."""

import asyncio
import uuid
import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update

from app.core.dependencies import get_current_user
from app.core.permissions import require_llm_permission, is_workspace_admin
from app.core.workflow import (
    MUTABLE_STATUSES,
    REFINABLE_STATES,
    SUBMITTABLE_STATES,
    can_transition,
)
from app.core.database import get_db_session
from app.config.settings import get_settings
from app.models.user import User
from app.models.school import School, SchoolSettings
from app.models.exam import Exam, Question, ExamPassage
from app.models.question import ExamAuditComment
from app.models.proposal import ExamGenerationProposal
from app.models.quality import ExamQualitySnapshot
from app.models.question_bank import QuestionBankItem
from app.models.usage_log import UsageLog
from app.schemas.exam import (
    GenerateFromProposalRequest,
    ExamGenerationProposalCreateRequest,
    ExamGenerationProposalResponse,
    ManualExamSubmissionRequest,
    QuestionBankSaveRequest,
    QuestionBankItemResponse,
    QuestionBankItemCreateRequest,
    QuestionBankItemUpdateRequest,
    QuestionBankImportRequest,
    ExamGenerationRequest,
    ExamGenerationResponse,
    ExamResponse,
    ExamListResponse,
    ExamListItem,
    ExamUpdateRequest,
    QuestionResponse,
    ExamRegenerationRequest,
    ExamExportRequest,
    ExamExportResponse,
    ExamAuditCommentCreateRequest,
    ExamAuditCommentResponse,
    ExamRefineFromCommentsRequest,
    ExamPassageResponse,
    QuestionEditRequest,
)

from app.services.curriculum_service import CurriculumService
from app.services.exam_generator import ExamGenerator
from app.services.exam_quality_report import ExamQualityReportService
from app.services.export_service import ExportService
from app.services.job_queue import enqueue_generation_job

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Regex-validated export filename component.
_EXPORT_FILE_PATTERN = re.compile(r"^[0-9a-f]{32}\.pdf$")


def _can_submit_audit_comment(role: str) -> bool:
    """Teachers/auditors/admin can leave review comments."""
    return role in {"teacher", "auditor", "school_admin"}


def _can_submit_proposal(role: str) -> bool:
    """Teacher/auditor/admin can submit generation proposals."""
    return role in {"teacher", "auditor", "school_admin"}


async def _run_exam_preflight(
    db: AsyncSession,
    exam: Exam,
) -> dict:
    """Run preflight checks before final submission/approval."""
    issues: List[dict] = []
    warnings: List[dict] = []

    questions_result = await db.execute(
        select(Question)
        .where(Question.exam_id == exam.id)
        .order_by(Question.question_number)
    )
    questions = list(questions_result.scalars().all())
    if not questions:
        issues.append(
            {
                "code": "no_questions",
                "message": "Exam has no questions.",
            }
        )
        return {
            "passed": False,
            "issue_count": len(issues),
            "warning_count": len(warnings),
            "issues": issues,
            "warnings": warnings,
        }

    def _formula_issues_from_text(
        text: str,
        question_id: uuid.UUID,
        question_number: int,
        field_name: str,
    ) -> List[dict]:
        local_issues: List[dict] = []
        if not text or not isinstance(text, str):
            return local_issues

        block_dollar_count = len(re.findall(r"(?<!\\)\$\$", text))
        if block_dollar_count % 2 != 0:
            local_issues.append(
                {
                    "code": "formula_unbalanced_block_dollar",
                    "question_id": str(question_id),
                    "question_number": question_number,
                    "field": field_name,
                    "message": "Unbalanced $$...$$ delimiter in formula markup.",
                }
            )

        text_without_block = re.sub(r"(?<!\\)\$\$", "", text)
        inline_dollar_count = len(re.findall(r"(?<!\\)\$", text_without_block))
        if inline_dollar_count % 2 != 0:
            local_issues.append(
                {
                    "code": "formula_unbalanced_inline_dollar",
                    "question_id": str(question_id),
                    "question_number": question_number,
                    "field": field_name,
                    "message": "Unbalanced $...$ delimiter in formula markup.",
                }
            )

        open_round = len(re.findall(r"\\\(", text))
        close_round = len(re.findall(r"\\\)", text))
        if open_round != close_round:
            local_issues.append(
                {
                    "code": "formula_unbalanced_round_delimiter",
                    "question_id": str(question_id),
                    "question_number": question_number,
                    "field": field_name,
                    "message": "Mismatched \\( and \\) formula delimiters.",
                }
            )

        open_square = len(re.findall(r"\\\[", text))
        close_square = len(re.findall(r"\\\]", text))
        if open_square != close_square:
            local_issues.append(
                {
                    "code": "formula_unbalanced_square_delimiter",
                    "question_id": str(question_id),
                    "question_number": question_number,
                    "field": field_name,
                    "message": "Mismatched \\[ and \\] formula delimiters.",
                }
            )

        begin_envs = re.findall(r"\\begin\{([A-Za-z*]+)\}", text)
        end_envs = re.findall(r"\\end\{([A-Za-z*]+)\}", text)
        if len(begin_envs) != len(end_envs):
            local_issues.append(
                {
                    "code": "formula_unbalanced_environment",
                    "question_id": str(question_id),
                    "question_number": question_number,
                    "field": field_name,
                    "message": "Mismatched LaTeX \\begin{...}/\\end{...} environments.",
                }
            )

        return local_issues

    for question in questions:
        formula_fields: List[tuple[str, str]] = [("question_text", question.question_text or "")]
        if question.explanation:
            formula_fields.append(("explanation", question.explanation))
        if question.options:
            for idx, option in enumerate(question.options, start=1):
                formula_fields.append((f"options[{idx}]", str(option)))
        if question.marking_scheme:
            for idx, mark_item in enumerate(question.marking_scheme, start=1):
                formula_fields.append((f"marking_scheme[{idx}]", str(mark_item)))
        if question.sub_parts:
            for idx, sub_part in enumerate(question.sub_parts, start=1):
                if isinstance(sub_part, dict):
                    formula_fields.append(
                        (
                            f"sub_parts[{idx}]",
                            str(sub_part.get("question") or ""),
                        )
                    )
                else:
                    formula_fields.append((f"sub_parts[{idx}]", str(sub_part)))

        for field_name, field_value in formula_fields:
            warnings.extend(
                _formula_issues_from_text(
                    text=field_value,
                    question_id=question.id,
                    question_number=question.question_number,
                    field_name=field_name,
                )
            )

        # Question structure integrity checks
        if not question.question_text or not question.question_text.strip():
            issues.append({
                "code": "empty_question_text",
                "question_id": str(question.id),
                "question_number": question.question_number,
                "field": "question_text",
                "message": f"Question {question.question_number} has empty question text.",
            })
        if question.marks is None or question.marks <= 0:
            issues.append({
                "code": "invalid_marks",
                "question_id": str(question.id),
                "question_number": question.question_number,
                "field": "marks",
                "message": f"Question {question.question_number} must have positive marks.",
            })
        if question.type == "multiple_choice":
            if not question.options or len(question.options) < 2:
                warnings.append({
                    "code": "mcq_few_options",
                    "question_id": str(question.id),
                    "question_number": question.question_number,
                    "field": "options",
                    "message": f"Question {question.question_number} has fewer than 2 options.",
                })
            if not question.correct_answer:
                warnings.append({
                    "code": "mcq_no_answer",
                    "question_id": str(question.id),
                    "question_number": question.question_number,
                    "field": "correct_answer",
                    "message": f"Question {question.question_number} has no correct answer selected.",
                })

    # Total marks sanity check
    actual_marks_sum = sum((q.marks or 0) for q in questions)
    if exam.total_marks and actual_marks_sum != exam.total_marks:
        warnings.append({
            "code": "total_marks_mismatch",
            "message": f"Sum of question marks ({actual_marks_sum}) does not match exam total ({exam.total_marks}).",
        })

    return {
        "passed": len(issues) == 0,
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
    }


async def _consume_llm_call_budget(exam: Exam, db: AsyncSession) -> None:
    """Consume one LLM call budget unit for an exam and enforce max usage."""
    if (exam.llm_call_count or 0) >= (exam.llm_call_limit or 3):
        raise HTTPException(
            status_code=400,
            detail=(
                "This exam has reached its LLM call limit "
                f"({exam.llm_call_limit})."
            ),
        )
    exam.llm_call_count = (exam.llm_call_count or 0) + 1
    await db.commit()


async def _log_usage(
    db: AsyncSession,
    school_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str,
    metadata: dict,
    tokens_used: int = 0,
    cost: float = 0.0,
    provider: Optional[str] = None,
) -> None:
    usage = UsageLog(
        school_id=school_id,
        user_id=user_id,
        action=action,
        tokens_used=tokens_used,
        cost=cost,
        provider=provider,
        log_metadata=json.dumps(metadata),
    )
    db.add(usage)


# ============================================================================
# EXAM GENERATION ENDPOINT
# ============================================================================

@router.post(
    "/generate",
    response_model=ExamGenerationResponse,
    status_code=202,
    summary="Generate an exam (async)",
    description="Start generating an exam in the background. Returns immediately with exam ID.",
    tags=["Exams"],
)
async def generate_exam(
    request: ExamGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamGenerationResponse:
    """
    Generate an exam from official scheme-of-work objectives.

    This endpoint:
    1. Validates the request
    2. Creates a draft exam record
    3. Enqueues a durable background generation job (LLM)
    4. Returns immediately with exam ID
    5. Client can poll GET /exams/{id} to check status

    Returns:
        202 Accepted with exam ID and polling endpoint
    """
    try:
        # Only workspace admins trigger LLM generation calls (cost control).
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only school administrators or individual teachers can generate exams",
            )

        warnings: List[str] = []
        if request.term and request.selected_weeks:
            scheme_data = await CurriculumService.get_objectives_for_weeks(
                class_level=request.grade_level,
                subject_name=request.subject,
                term=request.term,
                selected_weeks=request.selected_weeks,
                db=db,
            )
            if not scheme_data:
                class_list = await CurriculumService.get_all_classes(db)
                available = ", ".join(class_list)
                warnings.append(
                    f"No official NERDC scheme data found for {request.grade_level} "
                    f"{request.subject} {request.term}. Generating from general "
                    f"curriculum knowledge instead. Available classes: {available}"
                )

        # Check rate limit (10 exams per day per school)
        from datetime import datetime, timedelta

        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        rate_limit_query = select(func.count()).where(
            and_(
                Exam.school_id == current_user.school_id,
                Exam.created_at >= one_day_ago
            )
        )
        rate_limit_result = await db.execute(rate_limit_query)
        daily_count = rate_limit_result.scalar()

        if daily_count >= 10:
            raise HTTPException(
                status_code=429,
                detail="Daily exam generation limit reached (10 exams/day). Please try again tomorrow.",
            )

        # Create draft exam record
        exam_id = uuid.uuid4()
        exam = Exam(
            id=exam_id,
            school_id=current_user.school_id,
            created_by_user_id=current_user.user_id,
            subject=request.subject,
            grade_level=request.grade_level,
            status="draft",  # Will be updated by the job worker
            workflow_state="generation_requested",
            llm_call_count=1,
            llm_call_limit=3,
            total_marks=0,  # Will be updated by the job worker
            duration_minutes=request.duration_minutes,
        )

        db.add(exam)
        await db.flush()

        # Enqueue the durable, restart-safe job in the SAME transaction so a
        # crash between the two writes can never leave an orphaned draft.
        # The request-scoped db dependency commits exam + job atomically.
        await enqueue_generation_job(
            session=db,
            exam_id=exam_id,
            request_data=request.model_dump(mode="json"),
            school_id=current_user.school_id,
            created_by_user_id=current_user.user_id,
        )

        return ExamGenerationResponse(
            message="Exam generation queued",
            exam_id=exam_id,
            status="generating",
            poll_endpoint=f"/api/v1/exams/{exam_id}",
            estimated_time_seconds=30,
            warnings=warnings or None,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to start exam generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start exam generation: {str(e)}",
        )


# ============================================================================
# MANUAL EXAM SUBMISSION ENDPOINT
# ============================================================================

@router.post(
    "/manual-submit",
    response_model=ExamResponse,
    summary="Submit manual exam draft",
    description="Teacher/admin submits full exam questions directly without AI generation.",
    tags=["Exams"],
)
async def submit_manual_exam(
    request: ManualExamSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamResponse:
    """Create an under-review exam from manually authored questions."""
    if current_user.role not in {"school_admin", "teacher"}:
        raise HTTPException(
            status_code=403,
            detail="Only school administrators and teachers can submit manual exams",
        )

    exam = Exam(
        id=uuid.uuid4(),
        school_id=current_user.school_id,
        created_by_user_id=current_user.user_id,
        subject=request.subject,
        grade_level=request.grade_level,
        status="under_review",
        workflow_state="final_submitted_by_teacher",
        llm_call_count=0,
        llm_call_limit=3,
        total_marks=sum(q.marks for q in request.questions),
        duration_minutes=request.duration_minutes,
        instructions=request.instructions,
        language=(request.language or "English"),
    )
    db.add(exam)
    await db.flush()

    for question_data in request.questions:
        question = Question(
            id=uuid.uuid4(),
            exam_id=exam.id,
            question_number=question_data.question_number,
            type=question_data.type,
            question_text=question_data.question_text,
            marks=question_data.marks,
            difficulty=question_data.difficulty,
            bloom_level=question_data.bloom_level,
            topic=question_data.topic,
            options=question_data.options,
            correct_answer=question_data.correct_answer,
            explanation=question_data.explanation,
            marking_scheme=question_data.marking_scheme,
            sub_parts=(
                [part.model_dump() for part in question_data.sub_parts]
                if question_data.sub_parts
                else None
            ),
            diagram_svg=question_data.diagram_svg,
        )
        db.add(question)

    await _log_usage(
        db=db,
        school_id=current_user.school_id,
        user_id=current_user.user_id,
        action="manual_exam_submission",
        metadata={
            "exam_id": str(exam.id),
            "question_count": len(request.questions),
        },
    )
    await db.commit()
    await db.refresh(exam)

    question_result = await db.execute(
        select(Question)
        .where(Question.exam_id == exam.id)
        .order_by(Question.question_number)
    )
    questions = question_result.scalars().all()

    return ExamResponse(
        id=exam.id,
        school_id=exam.school_id,
        created_by_user_id=exam.created_by_user_id,
        subject=exam.subject,
        grade_level=exam.grade_level,
        status=exam.status,
        workflow_state=(getattr(exam, "workflow_state", None) or "final_submitted_by_teacher"),
        total_marks=exam.total_marks,
        duration_minutes=exam.duration_minutes,
        instructions=exam.instructions,
        language=(getattr(exam, "language", None) or "English"),
        questions=[
            QuestionResponse(
                id=q.id,
                question_number=q.question_number,
                type=q.type,
                question_text=q.question_text,
                marks=q.marks,
                difficulty=q.difficulty,
                bloom_level=q.bloom_level,
                topic=q.topic,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                marking_scheme=q.marking_scheme,
                sub_parts=q.sub_parts,
                diagram_svg=q.diagram_svg,
            )
            for q in questions
        ],
        created_at=exam.created_at,
        updated_at=exam.updated_at,
    )


# ============================================================================
# QUESTION BANK ENDPOINTS
# ============================================================================

@router.post(
    "/{exam_id}/question-bank/save",
    response_model=dict,
    summary="Save exam questions to question bank",
    description="Copy selected (or all) questions from an exam into school question bank.",
    tags=["Exams"],
)
async def save_exam_questions_to_bank(
    exam_id: uuid.UUID,
    request: QuestionBankSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Store reusable question variants without any AI call."""
    if current_user.role not in {"teacher", "school_admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only teachers or school administrators can save bank items",
        )

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    question_query = select(Question).where(Question.exam_id == exam_id)
    if request.question_ids:
        question_query = question_query.where(Question.id.in_(request.question_ids))
    questions_result = await db.execute(question_query.order_by(Question.question_number))
    questions = questions_result.scalars().all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found to save")

    for question in questions:
        item = QuestionBankItem(
            school_id=current_user.school_id,
            # SECURITY: school-contributed rows must NEVER be marked platform;
            # platform rows are injected into every school's prompts.
            owner_type="school",
            source_exam_id=exam.id,
            source_question_id=question.id,
            created_by_user_id=current_user.user_id,
            subject=exam.subject,
            grade_level=exam.grade_level,
            topic=question.topic,
            difficulty=question.difficulty,
            question_type=question.type,
            question_text=question.question_text,
            marks=question.marks,
            options=question.options,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            marking_scheme=question.marking_scheme,
            sub_parts=question.sub_parts,
            diagram_svg=question.diagram_svg,
            is_active=True,
            # Owner curation queue (D-NEW-1): school rows start pending and
            # only app/scripts/promote_bank_items.py (owner-run) can promote
            # them into the shared platform corpus.
            review_status="pending",
        )
        db.add(item)

    await db.commit()
    return {
        "message": "Questions saved to bank successfully",
        "exam_id": str(exam_id),
        "saved_count": len(questions),
    }


@router.get(
    "/question-bank/items",
    response_model=list[QuestionBankItemResponse],
    summary="Browse question bank",
    description="List school question bank items with optional filtering.",
    tags=["Exams"],
)
async def list_question_bank_items(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    grade_level: Optional[str] = Query(None, description="Filter by grade level"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    query_text: Optional[str] = Query(None, description="Free-text search on question text"),
    include_inactive: bool = Query(False, description="Include inactive items"),
    review_status: Optional[str] = Query(None, description="Filter by review status (pending/approved/rejected)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[QuestionBankItemResponse]:
    """Browse reusable questions for manual exam composition."""
    if current_user.role not in {"teacher", "auditor", "school_admin"}:
        raise HTTPException(status_code=403, detail="You are not allowed to browse question bank")

    query = select(QuestionBankItem).where(QuestionBankItem.school_id == current_user.school_id)
    if not include_inactive:
        query = query.where(QuestionBankItem.is_active.is_(True))
    if subject:
        query = query.where(QuestionBankItem.subject == subject)
    if grade_level:
        query = query.where(QuestionBankItem.grade_level == grade_level)
    if topic:
        query = query.where(QuestionBankItem.topic == topic)
    if difficulty:
        query = query.where(func.lower(QuestionBankItem.difficulty) == difficulty.lower())
    if review_status:
        query = query.where(QuestionBankItem.review_status == review_status)
    if query_text:
        query = query.where(QuestionBankItem.question_text.ilike(f"%{query_text}%"))

    query = query.order_by(QuestionBankItem.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(
    "/question-bank/items",
    response_model=QuestionBankItemResponse,
    status_code=201,
    summary="Add question to bank",
    description="Manually create a reusable bank question.",
    tags=["Exams"],
)
async def create_question_bank_item(
    request: QuestionBankItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuestionBankItemResponse:
    """Manually add question to bank (matching Question-Bank3.png)."""
    if current_user.role not in {"teacher", "school_admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only teachers or school administrators can add questions to the bank",
        )

    item = QuestionBankItem(
        school_id=current_user.school_id,
        owner_type="school",
        created_by_user_id=current_user.id,
        subject=request.subject,
        grade_level=request.grade_level,
        topic=request.topic,
        difficulty=request.difficulty or "medium",
        question_type=request.question_type or "multiple_choice",
        question_text=request.question_text,
        marks=request.marks,
        options=request.options,
        correct_answer=request.correct_answer,
        explanation=request.explanation,
        marking_scheme=request.marking_scheme,
        is_active=True,
        review_status="approved",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch(
    "/question-bank/items/{item_id}",
    response_model=QuestionBankItemResponse,
    summary="Edit question bank item",
    description="Manual edit of a reusable bank item (no AI call).",
    tags=["Exams"],
)
async def update_question_bank_item(
    item_id: uuid.UUID,
    request: QuestionBankItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuestionBankItemResponse:
    """Update bank item content so teachers can reuse and adjust quickly."""
    if current_user.role not in {"teacher", "school_admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only teachers or school administrators can edit bank items",
        )

    item_result = await db.execute(
        select(QuestionBankItem).where(
            and_(
                QuestionBankItem.id == item_id,
                QuestionBankItem.school_id == current_user.school_id,
            )
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Question bank item not found")

    payload = request.model_dump(exclude_unset=True)
    for field_name, value in payload.items():
        setattr(item, field_name, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete(
    "/question-bank/items/{item_id}",
    summary="Delete question bank item",
    description="Deactivate/remove an item from the school question bank.",
    tags=["Exams"],
)
async def delete_question_bank_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Soft delete a question bank item from the school repository."""
    if current_user.role not in {"teacher", "school_admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only teachers or school administrators can delete bank items",
        )

    item_result = await db.execute(
        select(QuestionBankItem).where(
            and_(
                QuestionBankItem.id == item_id,
                QuestionBankItem.school_id == current_user.school_id,
            )
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Question bank item not found")

    item.is_active = False
    await db.commit()
    return {"message": "Question bank item deleted successfully", "id": str(item_id)}


@router.post(
    "/{exam_id}/questions/import-from-bank",
    summary="Import questions from Question Bank into exam section",
    description="Import selected bank questions into a target section of an exam.",
    tags=["Exams"],
)
async def import_questions_from_bank(
    exam_id: uuid.UUID,
    request: QuestionBankImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Import selected bank questions directly into a specific section of an exam."""
    if not is_workspace_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only workspace administrators can import questions into exams",
        )

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    editable_states = {"draft", "teacher_review", "final_submitted_by_teacher"}
    current_state = getattr(exam, "workflow_state", None) or exam.status
    if current_state not in editable_states:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot add questions to an exam in state '{current_state}'",
        )

    bank_result = await db.execute(
        select(QuestionBankItem).where(
            and_(
                QuestionBankItem.id.in_(request.bank_item_ids),
                QuestionBankItem.school_id == current_user.school_id,
                QuestionBankItem.is_active.is_(True),
            )
        )
    )
    bank_items = bank_result.scalars().all()
    if not bank_items:
        raise HTTPException(status_code=404, detail="No valid question bank items found to import")

    q_max_res = await db.execute(
        select(func.max(Question.question_number)).where(Question.exam_id == exam_id)
    )
    max_q_num = q_max_res.scalar() or 0

    imported_count = 0
    sec_num = request.section_number or 1
    sec_name = request.section_name or f"Section {chr(64 + sec_num)}"

    for idx, item in enumerate(bank_items, start=1):
        q = Question(
            exam_id=exam_id,
            question_number=max_q_num + idx,
            section_number=sec_num,
            section_name=sec_name,
            type=item.question_type,
            difficulty=item.difficulty or "medium",
            question_text=item.question_text,
            marks=item.marks or 1,
            options=item.options,
            correct_answer=item.correct_answer,
            explanation=item.explanation,
            marking_scheme=item.marking_scheme,
            topic=item.topic,
        )
        db.add(q)
        await db.execute(
            update(QuestionBankItem)
            .where(QuestionBankItem.id == item.id)
            .values(usage_count=QuestionBankItem.usage_count + 1)
        )
        imported_count += 1

    # Recalculate total marks
    all_q = await db.execute(
        select(Question.marks).where(Question.exam_id == exam_id)
    )
    existing_marks = sum(m or 0 for m in all_q.scalars().all())
    new_marks = sum(item.marks or 1 for item in bank_items)
    exam.total_marks = existing_marks + new_marks

    # Add audit comment
    audit_comment = ExamAuditComment(
        exam_id=exam_id,
        author_user_id=current_user.user_id,
        comment_text=f"Imported {imported_count} question(s) from Question Bank into {sec_name}.",
        status="resolved",
    )
    db.add(audit_comment)

    await db.commit()
    return {
        "message": f"Successfully imported {imported_count} question(s) into {sec_name}.",
        "imported_count": imported_count,
        "exam_id": str(exam_id),
    }


# ============================================================================
# GENERATION PROPOSAL ENDPOINTS
# ============================================================================

@router.post(
    "/generation-proposals",
    response_model=ExamGenerationProposalResponse,
    summary="Submit exam generation proposal",
    description="Teacher/auditor submits exam intent and resources for admin approval.",
    tags=["Exams"],
)
async def create_generation_proposal(
    request: ExamGenerationProposalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamGenerationProposalResponse:
    """Create teacher/auditor proposal without triggering LLM call."""
    if not _can_submit_proposal(current_user.role):
        raise HTTPException(status_code=403, detail="You are not allowed to submit proposals")

    proposal = ExamGenerationProposal(
        school_id=current_user.school_id,
        requested_by_user_id=current_user.user_id,
        subject=request.subject,
        grade_level=request.grade_level,
        term=request.term,
        selected_weeks=request.selected_weeks or [],
        desired_outcomes=request.desired_outcomes,
        custom_instructions=request.custom_instructions,
        draft_questions=request.draft_questions,
        status="open",
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)
    return proposal


@router.get(
    "/generation-proposals",
    response_model=list[ExamGenerationProposalResponse],
    summary="List generation proposals",
    description="List school proposals; optionally include used/rejected items.",
    tags=["Exams"],
)
async def list_generation_proposals(
    include_closed: bool = Query(False, description="Include used/rejected proposals"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[ExamGenerationProposalResponse]:
    """List proposals in current school scope."""
    if not _can_submit_proposal(current_user.role):
        raise HTTPException(status_code=403, detail="You are not allowed to view proposals")

    query = select(ExamGenerationProposal).where(
        ExamGenerationProposal.school_id == current_user.school_id
    )
    if not include_closed:
        query = query.where(ExamGenerationProposal.status == "open")
    query = query.order_by(ExamGenerationProposal.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(
    "/generation-proposals/{proposal_id}/generate",
    response_model=ExamGenerationResponse,
    status_code=202,
    summary="Generate exam from proposal (admin)",
    description="Admin converts a teacher/auditor proposal into a standardized exam generation job.",
    tags=["Exams"],
)
async def generate_exam_from_proposal(
    proposal_id: uuid.UUID,
    request: GenerateFromProposalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamGenerationResponse:
    """Create draft exam and durable generation job from queued proposal."""
    if not is_workspace_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only school administrators or individual teachers can generate exams from proposals",
        )

    proposal_result = await db.execute(
        select(ExamGenerationProposal).where(
            and_(
                ExamGenerationProposal.id == proposal_id,
                ExamGenerationProposal.school_id == current_user.school_id,
            )
        )
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "open":
        raise HTTPException(status_code=400, detail="Proposal is not open")

    # Curriculum-first alignment: admin override wins, else fall back to the
    # teacher's proposal values. getattr() keeps older callers/tests that build
    # requests without these fields working.
    effective_term = getattr(request, "term", None) or getattr(proposal, "term", None)
    raw_weeks = getattr(request, "selected_weeks", None) or getattr(
        proposal, "selected_weeks", None
    )
    effective_weeks = [int(w) for w in raw_weeks] if raw_weeks else None

    from datetime import timedelta

    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    rate_limit_query = select(func.count()).where(
        and_(
            Exam.school_id == current_user.school_id,
            Exam.created_at >= one_day_ago,
        )
    )
    rate_limit_result = await db.execute(rate_limit_query)
    daily_count = rate_limit_result.scalar()
    if daily_count >= 10:
        raise HTTPException(
            status_code=429,
            detail="Daily exam generation limit reached (10 exams/day). Please try again tomorrow.",
        )

    teacher_feedback = [f"Teacher desired outcomes:\n{proposal.desired_outcomes}"]
    if proposal.custom_instructions:
        teacher_feedback.append(f"Teacher custom instructions:\n{proposal.custom_instructions}")
    if proposal.draft_questions:
        teacher_feedback.append(f"Teacher draft question ideas:\n{proposal.draft_questions}")
    if request.additional_admin_instructions:
        teacher_feedback.append(
            f"Admin standardization instructions:\n{request.additional_admin_instructions}"
        )

    generation_request = ExamGenerationRequest(
        subject=proposal.subject,
        grade_level=proposal.grade_level,
        term=effective_term,
        selected_weeks=effective_weeks,
        sections=request.sections,
        duration_minutes=request.duration_minutes,
        custom_instructions="\n\n".join(teacher_feedback),
        include_diagrams=request.include_diagrams,
    )

    exam_id = uuid.uuid4()
    exam = Exam(
        id=exam_id,
        school_id=current_user.school_id,
        created_by_user_id=current_user.user_id,
        subject=generation_request.subject,
        grade_level=generation_request.grade_level,
        status="draft",
        workflow_state="generation_requested",
        llm_call_count=1,
        llm_call_limit=3,
        total_marks=0,
        duration_minutes=generation_request.duration_minutes,
    )
    db.add(exam)

    proposal.status = "used"
    proposal.used_by_user_id = current_user.user_id
    proposal.used_at = datetime.now(timezone.utc)

    # Exam + proposal flip + job enqueue commit atomically via the
    # request-scoped db dependency (no orphaned drafts on crash).
    await enqueue_generation_job(
        session=db,
        exam_id=exam_id,
        request_data=generation_request.model_dump(mode="json"),
        school_id=current_user.school_id,
        created_by_user_id=current_user.user_id,
    )

    return ExamGenerationResponse(
        message="Exam generation from proposal queued",
        exam_id=exam_id,
        status="generating",
        poll_endpoint=f"/api/v1/exams/{exam_id}",
        estimated_time_seconds=30,
    )


@router.post(
    "/generation-proposals/{proposal_id}/reject",
    response_model=ExamGenerationProposalResponse,
    summary="Reject generation proposal (admin)",
    description=(
        "Admin declines a teacher/auditor proposal without generating an exam. "
        "The proposal status becomes 'rejected' and can no longer be generated."
    ),
    tags=["Exams"],
)
async def reject_generation_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamGenerationProposal:
    """Mark an open proposal as rejected (audit #5: this endpoint did not
    exist, so the modal's Reject button posted to the generate route and
    silently generated an exam instead)."""
    if not is_workspace_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only school administrators or individual teachers can reject proposals",
        )

    proposal_result = await db.execute(
        select(ExamGenerationProposal).where(
            and_(
                ExamGenerationProposal.id == proposal_id,
                ExamGenerationProposal.school_id == current_user.school_id,
            )
        )
    )
    proposal = proposal_result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status not in {"open", "accepted"}:
        raise HTTPException(status_code=400, detail="Proposal is not open for rejection")

    proposal.status = "rejected"
    await db.commit()
    await db.refresh(proposal)
    return proposal


# ============================================================================
# LIST EXAMS ENDPOINT
# ============================================================================

@router.get(
    "",
    response_model=ExamListResponse,
    include_in_schema=False,
)
@router.get(
    "/",
    response_model=ExamListResponse,
    summary="List exams",
    description="Get a list of exams for the school with optional filters.",
    tags=["Exams"],
)
async def list_exams(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    grade_level: Optional[str] = Query(None, description="Filter by grade level"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamListResponse:
    """
    List exams for the school.
    
    Supports filtering by subject, grade level, and status.
    Results are paginated.
    
    School data isolation: Only returns exams for the user's school.
    """
    try:
        # Build query with school isolation
        query = select(Exam).where(Exam.school_id == current_user.school_id)
        
        # Apply filters
        if subject:
            query = query.where(Exam.subject == subject)
        if grade_level:
            query = query.where(Exam.grade_level == grade_level)
        if status:
            query = query.where(Exam.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(Exam.created_at.desc()).offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        exams = result.scalars().all()

        # Single grouped query for question counts (avoids N+1)
        exam_ids = [exam.id for exam in exams]
        counts_by_exam: Dict[uuid.UUID, int] = {}
        if exam_ids:
            counts_result = await db.execute(
                select(Question.exam_id, func.count())
                .where(Question.exam_id.in_(exam_ids))
                .group_by(Question.exam_id)
            )
            counts_by_exam = {
                row[0]: row[1] for row in counts_result.all()
            }

        exam_list = [
            ExamListItem(
                id=exam.id,
                subject=exam.subject,
                grade_level=exam.grade_level,
                status=exam.status,
                total_marks=exam.total_marks,
                question_count=counts_by_exam.get(exam.id, 0),
                created_at=exam.created_at,
            )
            for exam in exams
        ]

        return ExamListResponse(total=total, exams=exam_list)
        
    except Exception as e:
        logger.error(f"Failed to list exams: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list exams: {str(e)}",
        )


@router.get(
    "/{exam_id}/quality-report",
    response_model=dict,
    summary="Get exam quality report",
    description="Return question quality and curriculum coverage analysis for an exam.",
    tags=["Exams"],
)
async def get_exam_quality_report(
    exam_id: uuid.UUID,
    save_snapshot: bool = Query(False, description="Persist this report as a historical snapshot"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Generate quality and coverage analytics for the exam."""
    if current_user.role not in {"teacher", "auditor", "school_admin"}:
        raise HTTPException(status_code=403, detail="You are not allowed to view quality reports")

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    questions_result = await db.execute(
        select(Question).where(Question.exam_id == exam_id).order_by(Question.question_number)
    )
    questions = questions_result.scalars().all()
    if not questions:
        raise HTTPException(status_code=400, detail="Exam has no questions for analysis")

    # Coverage signal: overlap between question keywords and the exam's own
    # curriculum metadata (subject/topic vocabulary).
    context_text = " ".join(
        filter(None, [exam.subject, *(getattr(q, "topic", None) for q in questions)])
    )

    report = ExamQualityReportService.build_report(
        subject=exam.subject,
        grade_level=exam.grade_level,
        questions=questions,
        context_text=context_text,
    )

    if save_snapshot:
        snapshot = ExamQualitySnapshot(
            exam_id=exam.id,
            school_id=exam.school_id,
            created_by_user_id=current_user.user_id,
            quality_status=report["quality_status"],
            overall_score=str(report["overall_score"]),
            report_data=report,
        )
        db.add(snapshot)
        await db.commit()

    return {
        "exam_id": str(exam_id),
        **report,
    }


@router.get(
    "/{exam_id}/quality-reports",
    response_model=dict,
    summary="List exam quality snapshots",
    description="List stored quality/coverage snapshots for an exam.",
    tags=["Exams"],
)
async def list_exam_quality_snapshots(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return all saved quality snapshots for an exam."""
    if current_user.role not in {"teacher", "auditor", "school_admin"}:
        raise HTTPException(status_code=403, detail="You are not allowed to view quality reports")

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    snapshots_result = await db.execute(
        select(ExamQualitySnapshot)
        .where(ExamQualitySnapshot.exam_id == exam_id)
        .order_by(ExamQualitySnapshot.created_at.desc())
    )
    snapshots = snapshots_result.scalars().all()

    return {
        "exam_id": str(exam_id),
        "total": len(snapshots),
        "snapshots": [
            {
                "snapshot_id": str(item.id),
                "created_at": item.created_at,
                "quality_status": item.quality_status,
                "overall_score": item.overall_score,
                "report": item.report_data,
            }
            for item in snapshots
        ],
    }


# ============================================================================
# GET EXAM DETAILS ENDPOINT
# ============================================================================

@router.get(
    "/{exam_id}",
    response_model=ExamResponse,
    summary="Get exam details",
    description="Get detailed information about a specific exam including all questions.",
    tags=["Exams"],
)
async def get_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamResponse:
    """
    Get exam details with all questions.
    
    School data isolation: Only returns exam if it belongs to the user's school.
    """
    try:
        # Get exam with school isolation
        result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id
                )
            )
        )
        exam = result.scalar_one_or_none()
        
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Get questions
        questions_result = await db.execute(
            select(Question)
            .where(Question.exam_id == exam_id)
            .order_by(Question.question_number)
        )
        questions = questions_result.scalars().all()

        passages_result = await db.execute(
            select(ExamPassage)
            .where(ExamPassage.exam_id == exam_id)
            .order_by(ExamPassage.section_number)
        )
        passages = list(passages_result.scalars().all())

        # Convert to response schema
        question_responses = [
            QuestionResponse(
                id=q.id,
                question_number=q.question_number,
                type=q.type,
                question_text=q.question_text,
                marks=q.marks,
                difficulty=q.difficulty,
                bloom_level=q.bloom_level,
                topic=q.topic,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                marking_scheme=q.marking_scheme,
                sub_parts=q.sub_parts,
                diagram_svg=q.diagram_svg,
            )
            for q in questions
        ]
        
        return ExamResponse(
            id=exam.id,
            school_id=exam.school_id,
            created_by_user_id=exam.created_by_user_id,
            subject=exam.subject,
            grade_level=exam.grade_level,
            status=exam.status,
workflow_state=(getattr(exam, "workflow_state", None) or "teacher_review"),
            total_marks=exam.total_marks,
            duration_minutes=exam.duration_minutes,
            instructions=exam.instructions,
            language=(getattr(exam, "language", None) or "English"),
            questions=question_responses,
            passages=[ExamPassageResponse.model_validate(p) for p in passages] or None,
            created_at=exam.created_at,
            updated_at=exam.updated_at,
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get exam: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get exam: {str(e)}",
        )


# ============================================================================
# UPDATE EXAM ENDPOINT
# ============================================================================

@router.put(
    "/{exam_id}",
    response_model=ExamResponse,
    summary="Update exam",
    description="Update exam metadata (status, instructions, duration). Cannot update questions.",
    tags=["Exams"],
)
async def update_exam(
    exam_id: uuid.UUID,
    update_request: ExamUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamResponse:
    """
    Update exam metadata.
    
    Only allows updating:
    - status (draft, under_review, approved)
    - instructions
    - duration_minutes
    
    Cannot update questions (exams are immutable once generated).
    
    School data isolation: Only updates exam if it belongs to the user's school.
    """
    try:
        # Verify user is a workspace admin
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only school administrators or individual teachers can update exams",
            )

        # Get exam with school isolation
        result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id
                )
            )
        )
        exam = result.scalar_one_or_none()

        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        # Approved exams are immutable; approval only via the approve endpoint.
        if exam.workflow_state == "approved":
            raise HTTPException(
                status_code=409,
                detail="Approved exams cannot be modified",
            )

        # Update fields (status restricted to draft/under_review by schema)
        if update_request.status is not None:
            if update_request.status not in MUTABLE_STATUSES:
                raise HTTPException(
                    status_code=409,
                    detail="Illegal status change; use the governed approval endpoint",
                )
            exam.status = update_request.status
        if update_request.instructions is not None:
            exam.instructions = update_request.instructions
        if update_request.duration_minutes is not None:
            exam.duration_minutes = update_request.duration_minutes

        await db.commit()
        await db.refresh(exam)

        passages_result = await db.execute(
            select(ExamPassage)
            .where(ExamPassage.exam_id == exam_id)
            .order_by(ExamPassage.section_number)
        )
        passages = list(passages_result.scalars().all())

        # Get questions for response
        questions_result = await db.execute(
            select(Question)
            .where(Question.exam_id == exam_id)
            .order_by(Question.question_number)
        )
        questions = questions_result.scalars().all()

        question_responses = [
            QuestionResponse(
                id=q.id,
                question_number=q.question_number,
                type=q.type,
                question_text=q.question_text,
                marks=q.marks,
                difficulty=q.difficulty,
                bloom_level=q.bloom_level,
                topic=q.topic,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                marking_scheme=q.marking_scheme,
                sub_parts=q.sub_parts,
                diagram_svg=q.diagram_svg,
            )
            for q in questions
        ]
        
        return ExamResponse(
            id=exam.id,
            school_id=exam.school_id,
            created_by_user_id=exam.created_by_user_id,
            subject=exam.subject,
            grade_level=exam.grade_level,
            status=exam.status,
            total_marks=exam.total_marks,
            duration_minutes=exam.duration_minutes,
            instructions=exam.instructions,
            language=(getattr(exam, "language", None) or "English"),
            questions=question_responses,
            passages=[ExamPassageResponse.model_validate(p) for p in passages] or None,
            created_at=exam.created_at,
            updated_at=exam.updated_at,
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to update exam: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update exam: {str(e)}",
        )


# ============================================================================
# UPDATE EXAM QUESTION ENDPOINT (SURGICAL CORRECTION)
# ============================================================================

@router.patch(
    "/{exam_id}/questions/{question_id}",
    response_model=QuestionResponse,
    summary="Update individual exam question",
    description="Surgical manual correction of a single question (options, text, marks, answer).",
    tags=["Exams"],
)
async def update_exam_question(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    request: QuestionEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuestionResponse:
    """Manually update an individual exam question."""
    try:
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only workspace administrators can edit exam questions",
            )

        # Get exam with school data isolation
        exam_result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id,
                )
            )
        )
        exam = exam_result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        # Check editable workflow states
        editable_states = {"draft", "teacher_review", "final_submitted_by_teacher"}
        current_state = getattr(exam, "workflow_state", None) or exam.status
        if current_state not in editable_states:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot edit questions on an exam in state '{current_state}'",
            )

        # Find question
        q_result = await db.execute(
            select(Question).where(
                and_(
                    Question.id == question_id,
                    Question.exam_id == exam_id,
                )
            )
        )
        question = q_result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        payload = request.model_dump(exclude_unset=True)
        if not payload:
            return QuestionResponse.model_validate(question)

        for field_name, val in payload.items():
            setattr(question, field_name, val)

        # Recompute total marks if marks changed
        if "marks" in payload:
            all_q = await db.execute(
                select(Question.marks).where(Question.exam_id == exam_id)
            )
            exam.total_marks = sum(m or 0 for m in all_q.scalars().all())

        # Record audit comment for transparency
        audit_comment = ExamAuditComment(
            exam_id=exam_id,
            question_id=question_id,
            author_user_id=current_user.user_id,
            comment_text=f"Question Q{question.question_number} manually corrected ({', '.join(payload.keys())}).",
            status="resolved",
        )
        db.add(audit_comment)

        await _log_usage(
            db=db,
            school_id=current_user.school_id,
            user_id=current_user.user_id,
            action="question_manual_edit",
            metadata={
                "exam_id": str(exam_id),
                "question_id": str(question_id),
                "question_number": question.question_number,
                "fields": list(payload.keys()),
            },
        )

        await db.commit()
        await db.refresh(question)

        return QuestionResponse.model_validate(question)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update question: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update question: {str(e)}",
        )


# ============================================================================
# DELETE EXAM QUESTION ENDPOINT
# ============================================================================

@router.delete(
    "/{exam_id}/questions/{question_id}",
    summary="Delete individual exam question",
    description="Delete a question, renumber remaining questions, and update total marks.",
    tags=["Exams"],
)
async def delete_exam_question(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a single question from an unapproved exam, renumbering the rest."""
    try:
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only workspace administrators can delete exam questions",
            )

        exam_result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id,
                )
            )
        )
        exam = exam_result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        editable_states = {"draft", "teacher_review", "final_submitted_by_teacher"}
        current_state = getattr(exam, "workflow_state", None) or exam.status
        if current_state not in editable_states:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete questions on an exam in state '{current_state}'",
            )

        q_result = await db.execute(
            select(Question).where(
                and_(
                    Question.id == question_id,
                    Question.exam_id == exam_id,
                )
            )
        )
        question = q_result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        deleted_num = question.question_number
        await db.delete(question)
        await db.flush()

        # Fetch remaining questions in order
        remaining_res = await db.execute(
            select(Question)
            .where(Question.exam_id == exam_id)
            .order_by(Question.question_number)
        )
        remaining_questions = remaining_res.scalars().all()

        # Renumber remaining questions sequentially
        for idx, q in enumerate(remaining_questions, start=1):
            q.question_number = idx

        # Recalculate totals
        exam.total_questions = len(remaining_questions)
        exam.total_marks = sum(q.marks or 0 for q in remaining_questions)

        await _log_usage(
            db=db,
            school_id=current_user.school_id,
            user_id=current_user.user_id,
            action="question_deleted",
            metadata={
                "exam_id": str(exam_id),
                "deleted_question_id": str(question_id),
                "deleted_number": deleted_num,
                "remaining_questions": exam.total_questions,
                "total_marks": exam.total_marks,
            },
        )

        await db.commit()

        return {
            "message": f"Question {deleted_num} deleted successfully",
            "exam_id": str(exam_id),
            "total_questions": exam.total_questions,
            "total_marks": exam.total_marks,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete exam question: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete exam question: {str(e)}",
        )


# ============================================================================
# AUDIT COMMENT ENDPOINTS
# ============================================================================


@router.post(
    "/{exam_id}/audit-comments",
    response_model=ExamAuditCommentResponse,
    summary="Submit teacher audit comment",
    description="Teachers/auditors submit comments or corrections for exam review.",
    tags=["Exams"],
)
async def create_audit_comment(
    exam_id: uuid.UUID,
    request: ExamAuditCommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamAuditCommentResponse:
    """Create exam-level or question-level audit comment."""
    if not _can_submit_audit_comment(current_user.role):
        raise HTTPException(status_code=403, detail="You are not allowed to submit audit comments")

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if request.question_id:
        question_result = await db.execute(
            select(Question).where(
                and_(
                    Question.id == request.question_id,
                    Question.exam_id == exam_id,
                )
            )
        )
        if not question_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Question not found for this exam")

    comment = ExamAuditComment(
        exam_id=exam_id,
        question_id=request.question_id,
        author_user_id=current_user.user_id,
        comment_text=request.comment_text,
        suggested_question_text=request.suggested_question_text,
        suggested_marking_scheme=(
            json.dumps(request.suggested_marking_scheme)
            if request.suggested_marking_scheme
            else None
        ),
        status="open",
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return comment


@router.get(
    "/{exam_id}/audit-comments",
    response_model=list[ExamAuditCommentResponse],
    summary="List exam audit comments",
    description="List review comments submitted by teachers/auditors for an exam.",
    tags=["Exams"],
)
async def list_audit_comments(
    exam_id: uuid.UUID,
    include_resolved: bool = Query(False, description="Include resolved comments"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[ExamAuditCommentResponse]:
    """List exam comments within current school scope."""
    if not _can_submit_audit_comment(current_user.role):
        raise HTTPException(status_code=403, detail="You are not allowed to view audit comments")

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    if not exam_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Exam not found")

    query = select(ExamAuditComment).where(ExamAuditComment.exam_id == exam_id)
    if not include_resolved:
        query = query.where(ExamAuditComment.status == "open")
    query = query.order_by(ExamAuditComment.created_at.asc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(
    "/{exam_id}/audit-comments/{comment_id}/resolve",
    response_model=ExamAuditCommentResponse,
    summary="Resolve or reopen audit comment",
    description="Toggle or mark an audit comment as resolved.",
    tags=["Exams"],
)
async def resolve_audit_comment(
    exam_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamAuditCommentResponse:
    """Mark an audit comment as resolved (or reopen if already resolved)."""
    if not _can_submit_audit_comment(current_user.role):
        raise HTTPException(status_code=403, detail="You are not allowed to resolve audit comments")

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    if not exam_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Exam not found")

    c_result = await db.execute(
        select(ExamAuditComment).where(
            and_(
                ExamAuditComment.id == comment_id,
                ExamAuditComment.exam_id == exam_id,
            )
        )
    )
    comment = c_result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.status == "resolved":
        comment.status = "open"
        comment.resolved_by_user_id = None
        comment.resolved_at = None
    else:
        comment.status = "resolved"
        comment.resolved_by_user_id = current_user.user_id
        comment.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(comment)
    return comment


# ============================================================================
# EXAM PREFLIGHT ENDPOINT
# ============================================================================

@router.get(
    "/{exam_id}/preflight",
    response_model=dict,
    summary="Run exam preflight checks",
    description="Validate question/asset integrity before final submission or approval.",
    tags=["Exams"],
)
async def exam_preflight(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Run quality checks that gate final submit/approve."""
    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    result = await _run_exam_preflight(db=db, exam=exam)
    return {
        "exam_id": str(exam_id),
        **result,
    }


# ============================================================================
# TEACHER FINAL SUBMISSION ENDPOINT
# ============================================================================

@router.post(
    "/{exam_id}/submit-final",
    response_model=dict,
    summary="Submit exam final draft (teacher)",
    description="Teacher marks exam as final and ready for admin approval.",
    tags=["Exams"],
)
async def submit_exam_final(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Move exam into final teacher-submitted state before admin approval."""
    if current_user.role not in {"teacher", "school_admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only teachers or school administrators can submit final exams",
        )

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.workflow_state not in SUBMITTABLE_STATES:
        raise HTTPException(
            status_code=(409 if exam.workflow_state == "approved" else 400),
            detail=(
                "Exam cannot be submitted as final from its current state "
                f"(workflow_state={exam.workflow_state})."
            ),
        )

    if current_user.role == "teacher" and exam.created_by_user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Teachers can only submit exams they created",
        )

    preflight = await _run_exam_preflight(db=db, exam=exam)
    if not preflight["passed"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Exam failed preflight checks. Resolve issues before final submission.",
                **preflight,
            },
        )

    exam.workflow_state = "final_submitted_by_teacher"
    exam.status = "under_review"
    await db.commit()

    return {
        "message": "Exam submitted for admin approval",
        "exam_id": str(exam_id),
        "workflow_state": exam.workflow_state,
    }


# ============================================================================
# REFINE EXAM ENDPOINT
# ============================================================================

@router.post(
    "/{exam_id}/refine",
    response_model=dict,
    summary="Refine exam questions",
    description="Refine selected exam questions using teacher feedback.",
    tags=["Exams"],
)
async def refine_exam(
    exam_id: uuid.UUID,
    request: ExamRegenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Refine selected questions (or all exam questions) and persist history.
    """
    try:
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only school administrators or individual teachers can refine exams",
            )

        exam_result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id,
                )
            )
        )
        exam = exam_result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        if exam.workflow_state not in REFINABLE_STATES:
            raise HTTPException(
                status_code=(409 if exam.workflow_state == "approved" else 400),
                detail=(
                    "Exam cannot be refined from its current state "
                    f"(workflow_state={exam.workflow_state})."
                ),
            )

        await _consume_llm_call_budget(exam, db)
        exam.workflow_state = "refinement_requested"
        await db.commit()

        generator = ExamGenerator()
        result = await generator.refine_exam(
            exam_id=exam_id,
            school_id=current_user.school_id,
            feedback=request.feedback,
            refined_by_user_id=current_user.user_id,
            question_ids=request.question_ids,
            db=db,
        )
        await _log_usage(
            db=db,
            school_id=current_user.school_id,
            user_id=current_user.user_id,
            action="exam_refinement",
            metadata={
                "exam_id": str(exam_id),
                "updated_questions": result.get("updated_questions", 0),
            },
            tokens_used=result.get("tokens_used") or 0,
            provider=result.get("provider"),
        )
        exam.workflow_state = "teacher_review"
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refine exam: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refine exam: {str(e)}",
        )


# ============================================================================
# REFINE FROM AUDIT COMMENTS ENDPOINT
# ============================================================================

@router.post(
    "/{exam_id}/refine-from-comments",
    response_model=dict,
    summary="Refine exam using teacher/auditor comments",
    description="Admin-only endpoint to batch unresolved comments into one refinement call.",
    tags=["Exams"],
)
async def refine_exam_from_comments(
    exam_id: uuid.UUID,
    request: ExamRefineFromCommentsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Batch review comments and send one combined refinement prompt to LLM."""
    if not is_workspace_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only school administrators or individual teachers can refine exams from comments",
        )

    exam_result = await db.execute(
        select(Exam).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.workflow_state not in REFINABLE_STATES:
        raise HTTPException(
            status_code=(409 if exam.workflow_state == "approved" else 400),
            detail=(
                "Exam cannot be refined from its current state "
                f"(workflow_state={exam.workflow_state})."
            ),
        )

    # Gather + validate comments BEFORE consuming LLM budget so a guaranteed
    # 400 path can never burn a call.
    comments_query = select(ExamAuditComment).where(
        and_(
            ExamAuditComment.exam_id == exam_id,
            ExamAuditComment.status == "open",
        )
    )
    if request.comment_ids:
        comments_query = comments_query.where(ExamAuditComment.id.in_(request.comment_ids))

    comments_result = await db.execute(comments_query.order_by(ExamAuditComment.created_at.asc()))
    comments = list(comments_result.scalars().all())
    if not comments:
        raise HTTPException(status_code=400, detail="No open comments available for refinement")

    feedback_parts = ["Teacher/Auditor review feedback:"]
    targeted_question_ids = set()
    for index, comment in enumerate(comments, start=1):
        line = f"{index}. {comment.comment_text}"
        if comment.question_id:
            line += f" (question_id={comment.question_id})"
            targeted_question_ids.add(comment.question_id)
        if comment.suggested_question_text:
            line += f" | suggested_text={comment.suggested_question_text}"
        if comment.suggested_marking_scheme:
            line += f" | suggested_marking_scheme={comment.suggested_marking_scheme}"
        feedback_parts.append(line)

    if request.additional_feedback:
        feedback_parts.append(f"Admin guidance: {request.additional_feedback}")

    # Budget is consumed only now: comments exist and feedback was built.
    await _consume_llm_call_budget(exam, db)
    exam.workflow_state = "refinement_requested"
    await db.commit()

    generator = ExamGenerator()
    result = await generator.refine_exam(
        exam_id=exam_id,
        school_id=current_user.school_id,
        feedback="\n".join(feedback_parts),
        refined_by_user_id=current_user.user_id,
        question_ids=list(targeted_question_ids) if targeted_question_ids else None,
        db=db,
    )

    resolved_at = datetime.now(timezone.utc)
    for comment in comments:
        comment.status = "resolved"
        comment.resolved_by_user_id = current_user.user_id
        comment.resolved_at = resolved_at

    await _log_usage(
        db=db,
        school_id=current_user.school_id,
        user_id=current_user.user_id,
        action="exam_refinement_from_comments",
        metadata={
            "exam_id": str(exam_id),
            "comments_processed": len(comments),
            "updated_questions": result.get("updated_questions", 0),
        },
        tokens_used=result.get("tokens_used") or 0,
        provider=result.get("provider"),
    )
    exam.workflow_state = "teacher_review"
    await db.commit()

    return {
        **result,
        "comments_processed": len(comments),
    }


# ============================================================================
# APPROVE EXAM ENDPOINT
# ============================================================================

@router.post(
    "/{exam_id}/approve",
    response_model=dict,
    summary="Approve exam",
    description="Mark an exam as approved for publishing/export.",
    tags=["Exams"],
)
async def approve_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Approve an exam that belongs to the current school.
    """
    try:
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only school administrators or individual teachers can approve exams",
            )

        result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id,
                )
            )
        )
        exam = result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        if exam.status == "failed":
            raise HTTPException(status_code=400, detail="Cannot approve a failed exam")
        if exam.workflow_state not in ("final_submitted_by_teacher", "teacher_review", "draft"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot approve exam in workflow state '{exam.workflow_state}'."
                ),
            )

        preflight = await _run_exam_preflight(db=db, exam=exam)
        if not preflight["passed"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Exam failed preflight checks. Resolve issues before approval.",
                    **preflight,
                },
            )

        exam.status = "approved"
        exam.workflow_state = "approved"
        await _log_usage(
            db=db,
            school_id=current_user.school_id,
            user_id=current_user.user_id,
            action="exam_approval",
            metadata={"exam_id": str(exam_id)},
        )
        await db.commit()

        return {
            "message": "Exam approved successfully",
            "exam_id": str(exam_id),
            "status": "approved",
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to approve exam: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve exam: {str(e)}",
        )


@router.post(
    "/{exam_id}/reject",
    response_model=dict,
    summary="Reject exam (send back to teacher)",
    description=(
        "Admin declines the teacher's final submission. The exam transitions "
        "back to teacher_review so the teacher can refine and resubmit. "
        "Optionally pass ?feedback= to leave a comment explaining why."
    ),
    tags=["Exams"],
)
async def reject_exam(
    exam_id: uuid.UUID,
    feedback: Optional[str] = Query(None, max_length=2000, description="Optional rejection note for the teacher"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Send a submitted exam back to teacher_review (governed transition)."""
    try:
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only school administrators or individual teachers can reject exams",
            )

        result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id,
                )
            )
        )
        exam = result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        if not can_transition(exam.workflow_state, "teacher_review"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot reject an exam in workflow_state={exam.workflow_state}. "
                    "Only submitted exams can be sent back for review."
                ),
            )

        exam.workflow_state = "teacher_review"
        exam.status = "under_review"
        if feedback:
            await _log_usage(
                db=db,
                school_id=current_user.school_id,
                user_id=current_user.user_id,
                action="exam_rejection_feedback",
                metadata={"exam_id": str(exam_id), "feedback": feedback},
            )
        await _log_usage(
            db=db,
            school_id=current_user.school_id,
            user_id=current_user.user_id,
            action="exam_rejection",
            metadata={"exam_id": str(exam_id)},
        )
        await db.commit()

        return {
            "message": "Exam sent back to the teacher for review",
            "exam_id": str(exam_id),
            "workflow_state": "teacher_review",
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reject exam: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject exam: {str(e)}",
        )


# ============================================================================
# EXPORT EXAM ENDPOINT
# ============================================================================

@router.post(
    "/{exam_id}/export",
    response_model=ExamExportResponse,
    summary="Export exam",
    description="Export an exam to PDF (MVP) and return a download URL.",
    tags=["Exams"],
)
async def export_exam(
    exam_id: uuid.UUID,
    request: ExamExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExamExportResponse:
    """
    Export exam to PDF (MVP).
    """
    try:
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only school administrators or individual teachers can export exams",
            )

        if request.format.lower() != "pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF export is currently supported",
            )

        exam_result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id,
                )
            )
        )
        exam = exam_result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        preflight = await _run_exam_preflight(db=db, exam=exam)
        if not preflight["passed"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Exam failed preflight checks. Resolve issues before export.",
                    **preflight,
                },
            )

        questions_result = await db.execute(
            select(Question)
            .where(Question.exam_id == exam_id)
            .order_by(Question.question_number)
        )
        questions = questions_result.scalars().all()
        if not questions:
            raise HTTPException(status_code=400, detail="Exam has no questions to export")

        passages_result = await db.execute(
            select(ExamPassage)
            .where(ExamPassage.exam_id == exam_id)
            .order_by(ExamPassage.section_number)
        )
        passages = list(passages_result.scalars().all())

        # Retrieve school branding and profile for official school exam header
        school_name = None
        school_address = None
        school_logo_url = None
        if getattr(current_user, "school_id", None):
            school_res = await db.execute(select(School).where(School.id == current_user.school_id))
            school_obj = school_res.scalar_one_or_none()
            if school_obj and isinstance(school_obj, School):
                school_name = getattr(school_obj, "name", None)
                school_address = getattr(school_obj, "address", None)
            settings_res = await db.execute(select(SchoolSettings).where(SchoolSettings.school_id == current_user.school_id))
            settings_obj = settings_res.scalar_one_or_none()
            if settings_obj and isinstance(settings_obj, SchoolSettings) and getattr(settings_obj, "logo_url", None):
                school_logo_url = getattr(settings_obj, "logo_url", None)

        doc_type = (getattr(request, "doc_type", None) or "exam").lower()
        if doc_type == "marking_guide":
            file_name = await asyncio.to_thread(
                ExportService.export_marking_guide_pdf,
                exam=exam,
                questions=list(questions),
                school_name=school_name,
                school_address=school_address,
            )
        elif doc_type == "omr":
            file_name = await asyncio.to_thread(
                ExportService.export_omr_sheet_pdf,
                exam=exam,
                school_name=school_name,
            )
        else:
            file_name = await asyncio.to_thread(
                ExportService.export_exam_pdf,
                exam=exam,
                questions=list(questions),
                include_answers=request.include_answers,
                passages=passages,
                school_name=school_name,
                school_address=school_address,
                school_logo_path=school_logo_url,
            )
        download_url = (
            f"/api/v1/exams/{exam_id}/exports/{file_name}"
        )

        await _log_usage(
            db=db,
            school_id=current_user.school_id,
            user_id=current_user.user_id,
            action="exam_export",
            metadata={
                "exam_id": str(exam_id),
                "format": "pdf",
                "include_answers": request.include_answers,
                "question_count": len(questions),
            },
        )
        await db.commit()

        return ExamExportResponse(
            message="Exam exported successfully",
            file_name=file_name,
            download_url=download_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to export exam: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export exam: {str(e)}",
        )


@router.get(
    "/{exam_id}/exports/{file_name}",
    summary="Download an exported exam PDF",
    description="Stream a previously generated PDF export for this exam.",
    tags=["Exams"],
)
async def download_export(
    exam_id: uuid.UUID,
    file_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Serve an exported PDF with tenant + filename validation."""
    if not _EXPORT_FILE_PATTERN.match(file_name or ""):
        raise HTTPException(status_code=400, detail="Invalid export file name")

    result = await db.execute(
        select(Exam.id).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Exam not found")

    file_path = ExportService.export_path(exam_id, file_name)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Export not found — run export again")

    return FileResponse(path=str(file_path), media_type="application/pdf", filename=file_name)


@router.get(
    "/{exam_id}/exports",
    response_model=list[str],
    summary="List exported PDFs for an exam",
    tags=["Exams"],
)
async def list_exports(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[str]:
    """List generated export files for this exam (tenant-scoped)."""
    result = await db.execute(
        select(Exam.id).where(
            and_(
                Exam.id == exam_id,
                Exam.school_id == current_user.school_id,
            )
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Exam not found")

    return ExportService.list_exports(exam_id)


# ============================================================================
# DELETE EXAM ENDPOINT
# ============================================================================

@router.delete(
    "/{exam_id}",
    response_model=dict,
    summary="Delete exam",
    description="Delete an exam and all its questions.",
    tags=["Exams"],
)
async def delete_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Delete an exam.
    
    This will cascade delete:
    - All questions
    - All exam context records
    
    School data isolation: Only deletes exam if it belongs to the user's school.
    """
    try:
        # Verify user is a workspace admin
        if not is_workspace_admin(current_user):
            raise HTTPException(
                status_code=403,
                detail="Only school administrators or individual teachers can delete exams",
            )
        
        # Get exam with school isolation
        result = await db.execute(
            select(Exam).where(
                and_(
                    Exam.id == exam_id,
                    Exam.school_id == current_user.school_id
                )
            )
        )
        exam = result.scalar_one_or_none()
        
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Delete exam (cascade will delete questions and context)
        await db.delete(exam)
        await db.commit()
        
        return {
            "message": "Exam deleted successfully",
            "exam_id": str(exam_id),
            "deleted": True,
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete exam: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete exam: {str(e)}",
        )

