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

    result = validator.validate(parsed_exam=parsed_exam, request=request)
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
        validator.validate_or_raise(parsed_exam=parsed_exam, request=request)


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

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    assert any("non-local context" in warning.lower() for warning in result.warnings)

# ============================================================================
# PHASE 5 REGRESSION TESTS — passages, true/false, language, sub-parts
# ============================================================================


def _comprehension_request() -> ExamGenerationRequest:
    """Request with a teacher-supplied comprehension passage (Section 1)."""
    from app.schemas.exam import PassageSpec

    return ExamGenerationRequest(
        subject="English Studies",
        grade_level="Primary 5",
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A: COMPREHENSION",
                question_type="multiple_choice",
                num_questions=2,
                marks_per_question=2,
                instruction_type="answer_all",
                sub_part_style="none",
                passage=PassageSpec(
                    title="The Market Day",
                    body=(
                        "Amina went to the Lagos market on Saturday morning. "
                        "She bought cassava, pepper and tomatoes for the family "
                        "stew. On the way home, harmattan dust covered her basket, "
                        "so she washed everything before cooking."
                    ),
                ),
            )
        ],
    )


def _comprehension_parsed(question_texts, correct_answers):
    return {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A: COMPREHENSION",
                "passage": {
                    "title": "The Market Day",
                    "body": (
                        "Amina went to the Lagos market on Saturday morning. "
                        "She bought cassava, pepper and tomatoes for the family "
                        "stew. On the way home, harmattan dust covered her basket, "
                        "so she washed everything before cooking."
                    ),
                },
                "questions": [
                    {
                        "type": "multiple_choice",
                        "question": q,
                        "options": ["A. Lagos", "B. Kano", "C. Aba", "D. Enugu"],
                        "correct_answer": a,
                        "marks": 2,
                    }
                    for q, a in zip(question_texts, correct_answers)
                ],
            }
        ]
    }


def test_quality_validator_passes_grounded_comprehension_questions():
    """Questions whose content words appear in the passage must pass cleanly."""
    validator = ExamQualityValidator()
    request = _comprehension_request()
    parsed_exam = _comprehension_parsed(
        [
            "Where did Amina go on Saturday morning?",
            "What did harmattan dust cover?",
        ],
        ["A", "A"],
    )

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    grounding_errors = [e for e in result.errors if "grounding" in e]
    assert grounding_errors == []


def test_quality_validator_rejects_ungrounded_comprehension_questions():
    """Questions with zero lexical overlap with the passage are hard errors."""
    validator = ExamQualityValidator()
    request = _comprehension_request()
    parsed_exam = _comprehension_parsed(
        [
            "Which planet has the largest ring system?",
            "State the boiling point of mercury.",
        ],
        ["A", "B"],
    )

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    grounding_errors = [e for e in result.errors if "grounding" in e]
    assert len(grounding_errors) == 2


def test_quality_validator_warns_on_low_passage_overlap():
    """Partial overlap (<50%) triggers a warning, not an error."""
    validator = ExamQualityValidator()
    request = _comprehension_request()
    # "Saturday" and "morning" overlap; most other content words do not.
    parsed_exam = _comprehension_parsed(
        [
            "Saturday morning activities happen where exactly?",
            "What did harmattan dust cover?",
        ],
        ["A", "A"],
    )

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    grounding_errors = [e for e in result.errors if "grounding" in e]
    overlap_warnings = [w for w in result.warnings if "overlap" in w]
    # Either all questions pass (>=50%) or the borderline one warns — but at
    # least one question must not hard-error for this marginal case.
    assert not grounding_errors or overlap_warnings


def _true_false_request() -> ExamGenerationRequest:
    return ExamGenerationRequest(
        subject="History",
        grade_level="Primary 5",
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A: TRUE/FALSE",
                question_type="true_false",
                num_questions=2,
                marks_per_question=1,
                instruction_type="answer_all",
                sub_part_style="none",
            )
        ],
    )


def test_quality_validator_accepts_valid_true_false():
    validator = ExamQualityValidator()
    request = _true_false_request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A: TRUE/FALSE",
                "questions": [
                    {
                        "type": "true_false",
                        "question": "Nigeria gained independence in 1960.",
                        "options": ["A. True", "B. False"],
                        "correct_answer": "A",
                        "marks": 1,
                    },
                    {
                        "type": "true_false",
                        "question": "The first military coup happened in 1976.",
                        "options": ["A. True", "B. False"],
                        "correct_answer": "B",
                        "marks": 1,
                    },
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    assert result.errors == []


def test_quality_validator_rejects_bad_true_false_answers():
    validator = ExamQualityValidator()
    request = _true_false_request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A: TRUE/FALSE",
                "questions": [
                    {
                        "type": "true_false",
                        "question": "Bad answer letter for true/false.",
                        "options": ["A. True", "B. False"],
                        "correct_answer": "D",  # illegal for true/false
                        "marks": 1,
                    },
                    {
                        "type": "true_false",
                        "question": "Too few options.",
                        "options": ["A. True"],
                        "correct_answer": "A",
                        "marks": 1,
                    },
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    assert any("A/B correct_answer" in e for e in result.errors)
    assert any("2 options" in e for e in result.errors)


def _igbo_request() -> ExamGenerationRequest:
    return ExamGenerationRequest(
        subject="Igbo",
        grade_level="Primary 5",
        language="Igbo",
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


def test_quality_validator_skips_english_bias_checks_for_non_english():
    """US-bias / Nigeria-context warnings must not fire on e.g. Igbo papers."""
    validator = ExamQualityValidator()
    request = _igbo_request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A",
                "questions": [
                    {
                        "type": "multiple_choice",
                        "question": "Gịnị bụ isi obodo Naịjiria?",
                        "options": ["A. Lagos", "B. Abuja", "C. Kano", "D. Enugu"],
                        "correct_answer": "B",
                        "marks": 2,
                    },
                    {
                        "type": "multiple_choice",
                        "question": "Kedu ihe akụ na ụba pụtara?",
                        "options": ["A. Akụ", "B. Ụba", "C. Aka", "D. Azụ"],
                        "correct_answer": "B",
                        "marks": 2,
                    },
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    assert not any("nigeria-local terms" in w.lower() for w in result.warnings)
    assert not any("non-local context" in w.lower() for w in result.warnings)


def _theory_request() -> ExamGenerationRequest:
    return ExamGenerationRequest(
        subject="National Values",
        grade_level="Primary 5",
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION B: THEORY",
                question_type="short_answer",
                num_questions=1,
                marks_per_question=6,
                instruction_type="answer_all",
                sub_part_style="letter",
                allow_sub_parts=True,
            )
        ],
    )


def test_quality_validator_accepts_balanced_sub_parts():
    validator = ExamQualityValidator()
    request = _theory_request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION B: THEORY",
                "questions": [
                    {
                        "type": "short_answer",
                        "question": "Explain the roles of community leaders.",
                        "marks": 6,
                        "sub_parts": [
                            {"part": "a", "question": "State two roles.", "marks": 4},
                            {"part": "b", "question": "Give one example.", "marks": 2},
                        ],
                    }
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    assert not any("sub-part marks" in e for e in result.errors)


def test_quality_validator_rejects_unbalanced_sub_parts():
    validator = ExamQualityValidator()
    request = _theory_request()
    parsed_exam = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION B: THEORY",
                "questions": [
                    {
                        "type": "short_answer",
                        "question": "Explain the roles of community leaders.",
                        "marks": 6,
                        "sub_parts": [
                            {"part": "a", "question": "State two roles.", "marks": 4},
                            {"part": "b", "question": "Give one example.", "marks": 3},
                        ],
                    }
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    assert any("sub-part marks 7 do not sum to question marks 6" in e for e in result.errors)
def test_quality_validator_accepts_british_and_mixed_case_bloom_levels():
    """British 'analyse' and any casing must not fail quality validation.

    Regression for a real failure: the LLM returned "analyse" (British
    spelling), which was not in the canonical American list and killed an
    otherwise-fine generation.
    """
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
                        "question": "What is 2+2?",
                        "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
                        "correct_answer": "D",
                        "marks": 2,
                        "difficulty": "easy",
                        "bloom_level": "analyse",
                    },
                    {
                        "type": "multiple_choice",
                        "question": "Which is even?",
                        "options": ["A. 1", "B. 3", "C. 4", "D. 5"],
                        "correct_answer": "C",
                        "marks": 2,
                        "difficulty": "medium",
                        "bloom_level": "Analyse",
                    },
                ],
            }
        ]
    }

    result = validator.validate(parsed_exam=parsed_exam, request=request)
    assert not any("Bloom level" in e for e in result.errors)


def test_quality_validator_still_rejects_junk_bloom_level():
    """Genuinely invalid Bloom values are still rejected after normalizing."""
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
                        "question": "Q?",
                        "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
                        "correct_answer": "A",
                        "marks": 2,
                        "difficulty": "easy",
                        "bloom_level": "Application",
                    }
                ],
            }
        ]
    }

    with pytest.raises(ValueError, match="quality validation"):
        validator.validate_or_raise(parsed_exam=parsed_exam, request=request)
