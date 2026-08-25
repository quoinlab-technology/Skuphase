"""Exam generation and management API endpoints."""

import asyncio
import uuid
import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update

from app.core.dependencies import get_current_user
from app.core.permissions import require_llm_permission, is_workspace_admin
from app.core.workflow import MUTABLE_STATUSES
from app.core.database import get_db_session, async_session_maker
from app.config.settings import get_settings
from app.models.user import User
from app.models.exam import Exam, Question
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
    QuestionBankItemUpdateRequest,
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
            issues.extend(
                _formula_issues_from_text(
                    text=field_value,
                    question_id=question.id,
                    question_number=question.question_number,
                    field_name=field_name,
                )
            )

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
        await db.commit()

        # Enqueue a durable, restart-safe job (survives deploys/restarts).
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
        total_marks=exam.total_marks,
        duration_minutes=exam.duration_minutes,
        instructions=exam.instructions,
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
    query_text: Optional[str] = Query(None, description="Free-text search on question text"),
    include_inactive: bool = Query(False, description="Include inactive items"),
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
    if query_text:
        query = query.where(QuestionBankItem.question_text.ilike(f"%{query_text}%"))

    query = query.order_by(QuestionBankItem.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


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

    await db.commit()

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


# ============================================================================
# LIST EXAMS ENDPOINT
# ============================================================================

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
            total_marks=exam.total_marks,
            duration_minutes=exam.duration_minutes,
            instructions=exam.instructions,
            questions=question_responses,
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
            questions=question_responses,
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
        if exam.workflow_state != "final_submitted_by_teacher":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Exam must be submitted by teacher as final before approval "
                    "(workflow_state=final_submitted_by_teacher)."
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

        file_name = await asyncio.to_thread(
            ExportService.export_exam_pdf,
            exam=exam,
            questions=list(questions),
            include_answers=request.include_answers,
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

