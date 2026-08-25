import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql.dml import Delete

from app.schemas.exam import ExamGenerationRequest, SectionConfig
from app.services.exam_generator import ExamGenerator


@pytest.mark.asyncio
async def test_retrieve_context_passes_selected_document_ids_to_rag():
    doc_id = uuid.uuid4()
    request = ExamGenerationRequest(
        subject="Biology",
        grade_level="SSS 1",
        document_ids=[doc_id],
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

    with patch("app.services.exam_generator.EmbeddingService"), patch(
        "app.services.exam_generator.get_llm_service"
    ):
        generator = ExamGenerator()
        generator.rag_service.search = AsyncMock(
            return_value=[
                {
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": str(doc_id),
                    "chunk_index": 0,
                    "content": "Photosynthesis is the process...",
                    "similarity_score": 0.91,
                    "chunk_metadata": {},
                }
            ]
        )

        db = AsyncMock()
        await generator.retrieve_context(
            school_id=uuid.uuid4(),
            document_ids=request.document_ids,
            subject=request.subject,
            db=db,
        )

        call_kwargs = generator.rag_service.search.call_args.kwargs
        assert call_kwargs["document_ids"] == [doc_id]


@pytest.mark.asyncio
async def test_store_exam_regeneration_issues_delete_for_old_questions():
    exam_id = uuid.uuid4()
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    request = ExamGenerationRequest(
        subject="Physics",
        grade_level="SSS 2",
        document_ids=[doc_id],
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A",
                question_type="multiple_choice",
                num_questions=1,
                marks_per_question=2,
                instruction_type="answer_all",
                sub_part_style="none",
            )
        ],
    )

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
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                    }
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

    with patch("app.services.exam_generator.EmbeddingService"), patch(
        "app.services.exam_generator.get_llm_service"
    ):
        generator = ExamGenerator()
        await generator.store_exam(
            parsed_exam=parsed_exam,
            request=request,
            school_id=school_id,
            created_by_user_id=user_id,
            rag_context={"document_ids": [doc_id], "combined_context": "ctx", "chunks": []},
            llm_response={"tokens_used": 10, "cost": 0.0, "provider": "grok", "content": "{}"},
            db=db,
            exam_id=exam_id,
        )

    assert any(
        isinstance(call.args[0], Delete)
        for call in db.execute.call_args_list
        if call.args
    )
