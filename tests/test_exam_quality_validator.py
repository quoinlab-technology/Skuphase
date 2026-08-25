import uuid

import pytest

from app.schemas.exam import ExamGenerationRequest, SectionConfig
from app.services.exam_quality_validator import ExamQualityValidator


def _request() -> ExamGenerationRequest:
    return ExamGenerationRequest(
        subject="Basic Science",
        grade_level="JSS 2",
        document_ids=[uuid.uuid4()],
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


def test_quality_validator_accepts_valid_exam_shape():
    validator = ExamQualityValidator()
    request = _request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A",
                "questions": [
                    {
                        "type": "multiple_choice",
                        "question": "Which city is the capital of Nigeria?",
                        "options": ["A. Lagos", "B. Abuja", "C. Kano", "D. Ibadan"],
                        "correct_answer": "B",
                        "marks": 2,
                        "difficulty": "easy",
                        "bloom_level": "remember",
                    },
                    {
                        "type": "multiple_choice",
                        "question": "NEPA relates to which utility service?",
                        "options": ["A. Water", "B. Electricity", "C. Roads", "D. Health"],
                        "correct_answer": "B",
                        "marks": 2,
                        "difficulty": "medium",
                        "bloom_level": "understand",
                    },
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request, rag_context={"chunks": []})
    assert result.errors == []
    assert result.metrics["generated_question_total"] == 2
    assert result.metrics["generated_marks_total"] == 4


def test_quality_validator_rejects_mcq_without_options():
    validator = ExamQualityValidator()
    request = _request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A",
                "questions": [
                    {
                        "type": "multiple_choice",
                        "question": "Bad MCQ",
                        "options": ["A", "B"],
                        "correct_answer": "E",
                        "marks": 2,
                    },
                    {
                        "type": "multiple_choice",
                        "question": "Another bad MCQ",
                        "marks": 2,
                    },
                ],
            }
        ]
    }

    with pytest.raises(ValueError, match="quality validation"):
        validator.validate_or_raise(parsed_exam=parsed_exam, request=request, rag_context={"chunks": []})


def test_quality_validator_flags_non_local_context_warning():
    validator = ExamQualityValidator()
    request = _request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A",
                "questions": [
                    {
                        "type": "multiple_choice",
                        "question": "A student paid in dollars and drove for miles.",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "marks": 2,
                    },
                    {
                        "type": "multiple_choice",
                        "question": "Another context question.",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "B",
                        "marks": 2,
                    },
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request, rag_context={"chunks": []})
    assert any("non-local context" in warning.lower() for warning in result.warnings)
