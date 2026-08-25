"""Tests for the curriculum-first exam generator (post-RAG removal)."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql.dml import Delete

from app.schemas.exam import ExamGenerationRequest, SectionConfig
from app.services.exam_generator import ExamGenerator


def _request(subject: str = "Basic Science", grade: str = "Primary 4") -> ExamGenerationRequest:
    return ExamGenerationRequest(
        subject=subject,
        grade_level=grade,
        term="First Term",
        selected_weeks=[1],
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A",
                question_type="multiple_choice",
                num_questions=2,
                marks_per_question=2,
                instruction_type="answer_all",
                sub_part_style="none",
            )
        ],
    )


def _make_generator() -> ExamGenerator:
    with patch("app.services.exam_generator.get_llm_service"):
        return ExamGenerator()


@pytest.mark.asyncio
async def test_retrieve_context_is_sql_only_and_tenant_free():
    """retrieve_context must not accept or use document/RAG context anymore."""
    import inspect

    signature = inspect.signature(ExamGenerator.retrieve_context)
    assert "document_ids" not in signature.parameters
    assert "school_id" not in signature.parameters

    generator = _make_generator()
    db = AsyncMock()
    db.commit = AsyncMock()
    # CurriculumService + few-shot both hit the DB; empty results are fine.
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])))

    context = await generator.retrieve_context(
        subject="Basic Science",
        grade_level="Primary 4",
        term="First Term",
        selected_weeks=[1],
        db=db,
    )

    assert "combined_context" in context
    assert context["has_scheme_data"] is False


@pytest.mark.asyncio
async def test_store_exam_regeneration_issues_delete_for_old_questions():
    exam_id = uuid.uuid4()
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()

    request = _request(subject="Physics", grade="Primary 5")

    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A",
                "questions": [
                    {
                        "type": "multiple_choice",
                        "question": "What is force?",
                        "marks": 2,
                        "options": ["A. push", "B. pull", "C. lift", "D. drop"],
                        "correct_answer": "A",
                    },
                    {
                        "type": "multiple_choice",
                        "question": "Which is a unit of force?",
                        "marks": 2,
                        "options": ["A. newton", "B. metre", "C. litre", "D. gram"],
                        "correct_answer": "A",
                    },
                ],
            }
        ]
    }

    db = AsyncMock()
    db.add = MagicMock()
    existing_exam = SimpleNamespace(
        id=exam_id,
        total_marks=0,
        status="draft",
        updated_at=None,
    )
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: existing_exam))

    generator = _make_generator()
    await generator.store_exam(
        parsed_exam=parsed_exam,
        request=request,
        school_id=school_id,
        created_by_user_id=user_id,
        llm_response={"tokens_used": 10, "cost": 0.0, "provider": "groq", "content": "{}"},
        db=db,
        exam_id=exam_id,
    )

    assert any(
        isinstance(call.args[0], Delete)
        for call in db.execute.call_args_list
        if call.args
    )
