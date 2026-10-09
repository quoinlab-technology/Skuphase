"""Generator v2 flow tests — curriculum-first, no RAG."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.exam_generator import ExamGenerator
from app.schemas.exam import ExamGenerationRequest, SectionConfig

MOCK_SCHOOL_ID = uuid4()
MOCK_USER_ID = uuid4()

MOCK_SECTION_CONFIG = [
    SectionConfig(
        section_number=1,
        section_title="SECTION A",
        question_type="multiple_choice",
        num_questions=2,
        marks_per_question=2,
        instruction_type="answer_all",
        sub_part_style="none"
    ),
    SectionConfig(
        section_number=2,
        section_title="SECTION B",
        question_type="essay",
        num_questions=1,
        instruction_type="answer_all",
        sub_part_style="letter",
        sub_parts_per_question=2
    )
]

MOCK_LLM_RESPONSE_JSON = {
    "sections": [
        {
            "section_number": 1,
            "section_title": "SECTION A",
            "instruction": "Answer ALL questions",
            "questions": [
                {
                    "id": 1,
                    "type": "multiple_choice",
                    "question": "Q1 Text",
                    "options": ["A. one", "B. two", "C. three", "D. four"],
                    "correct_answer": "A",
                    "marks": 2
                },
                {
                    "id": 2,
                    "type": "multiple_choice",
                    "question": "Q2 Text",
                    "options": ["A. red", "B. green", "C. blue", "D. yellow"],
                    "correct_answer": "B",
                    "marks": 2
                }
            ]
        },
        {
            "section_number": 2,
            "section_title": "SECTION B",
            "instruction": "Answer ALL questions",
            "questions": [
                {
                    "id": 1,
                    "type": "essay",
                    "question": "Essay Q1",
                    "marks": 10,
                    "sub_parts": [
                        {"part": "a", "question": "Part a", "marks": 5},
                        {"part": "b", "question": "Part b", "marks": 5}
                    ]
                }
            ]
        }
    ]
}


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_llm_service():
    service = AsyncMock()
    service.generate = AsyncMock(return_value={
        "content": json.dumps(MOCK_LLM_RESPONSE_JSON),
        "tokens_used": 1000,
        "cost": 0.0
    })
    return service


def _make_generator(mock_llm_service):
    with patch("app.services.exam_generator.get_llm_service", return_value=mock_llm_service):
        generator = ExamGenerator()
    # Few-shot selection returns nothing (empty platform bank).
    generator.few_shot_selector.select = AsyncMock(return_value=[])
    return generator


@pytest.mark.asyncio
async def test_generate_exam_success_without_documents(mock_db_session, mock_llm_service):
    """Generation works from curriculum context alone — no documents needed."""
    generator = _make_generator(mock_llm_service)

    request = ExamGenerationRequest(
        subject="Basic Science",
        grade_level="Primary 4",
        sections=MOCK_SECTION_CONFIG,
        duration_minutes=60
    )

    exam = await generator.generate_exam(
        request=request,
        school_id=MOCK_SCHOOL_ID,
        created_by_user_id=MOCK_USER_ID,
        db=mock_db_session
    )

    mock_llm_service.generate.assert_called_once()
    prompt = mock_llm_service.generate.call_args[1]["prompt"]
    assert "<internal_planning>" in prompt
    assert "SECTION A" in prompt
    assert "SECTION B" in prompt

    assert exam.subject == "Basic Science"
    assert exam.total_marks == 14  # 2*2 + 10
    assert exam.status == "under_review"
    assert exam.workflow_state == "teacher_review"

    questions_added = [
        call[0][0] for call in mock_db_session.add.call_args_list
        if isinstance(call[0][0], __import__("app.models.exam", fromlist=["Question"]).Question)
    ]
    assert len(questions_added) == 3
    assert questions_added[0].type == "multiple_choice"
    assert questions_added[2].type == "essay"
    assert questions_added[2].sub_parts is not None


@pytest.mark.asyncio
async def test_generate_exam_empty_curriculum_context_is_non_fatal(mock_db_session, mock_llm_service):
    """Empty scheme/few-shot context falls back gracefully (by design)."""
    generator = _make_generator(mock_llm_service)
    generator.retrieve_context = AsyncMock(
        return_value={
            "combined_context": (
                "Standard National Curriculum for Nigerian Schools: "
                "Physics (Primary 6)."
            ),
            "has_scheme_data": False,
            "few_shot_count": 0,
        }
    )

    request = ExamGenerationRequest(
        subject="Physics",
        grade_level="Primary 6",
        sections=MOCK_SECTION_CONFIG
    )

    exam = await generator.generate_exam(
        request=request,
        school_id=MOCK_SCHOOL_ID,
        created_by_user_id=MOCK_USER_ID,
        db=mock_db_session
    )
    assert exam.status == "under_review"
    prompt = mock_llm_service.generate.call_args[1]["prompt"]
    assert "Standard National Curriculum" in prompt


@pytest.mark.asyncio
async def test_generate_exam_retries_once_after_malformed_json(mock_db_session, mock_llm_service):
    """A successful provider response with broken JSON gets one bounded retry."""
    mock_llm_service.generate = AsyncMock(side_effect=[
        {"content": '{"sections":[{"section_number":1,"questions":[', "tokens_used": 10, "cost": 0.0},
        {"content": json.dumps(MOCK_LLM_RESPONSE_JSON), "tokens_used": 1000, "cost": 0.0},
    ])
    generator = _make_generator(mock_llm_service)
    request = ExamGenerationRequest(
        subject="Basic Science",
        grade_level="Primary 4",
        sections=MOCK_SECTION_CONFIG,
        duration_minutes=60,
    )

    exam = await generator.generate_exam(
        request=request,
        school_id=MOCK_SCHOOL_ID,
        created_by_user_id=MOCK_USER_ID,
        db=mock_db_session,
    )

    assert exam.status == "under_review"
    assert mock_llm_service.generate.await_count == 2
    assert mock_llm_service.generate.await_args_list[1].kwargs["temperature"] == 0.2


@pytest.mark.asyncio
async def test_parse_response_validation():
    """Test response parsing validation logic."""
    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    bad_json = "{invalid_json}"
    with pytest.raises(ValueError, match="Invalid JSON response"):
        generator.parse_response(bad_json, MOCK_SECTION_CONFIG)

    missing_sections = json.dumps({"foo": "bar"})
    with pytest.raises(ValueError, match="Response missing 'sections' key"):
        generator.parse_response(missing_sections, MOCK_SECTION_CONFIG)

    mismatch_response = json.dumps({"sections": []})
    parsed = generator.parse_response(mismatch_response, MOCK_SECTION_CONFIG)
    assert len(parsed["sections"]) == 0

    parsed = generator.parse_response(json.dumps(MOCK_LLM_RESPONSE_JSON), MOCK_SECTION_CONFIG)
    assert len(parsed["sections"]) == 2


def test_repair_json_text_fixes_invalid_backslash_escape():
    """LaTeX like \\ce{H2SO4} inside a JSON string must not kill parsing.

    Regression for a real production failure: the Chemistry prompt tells the
    model to emit mhchem notation, the model wrote a single backslash, and
    json.loads rejected it with \"Invalid \\escape\".
    """
    from app.services.exam_generator import _repair_json_text

    # Simulate the model emitting ONE backslash (invalid JSON escape):
    broken = '{"explanation": "Sulphuric acid is \\ce{H2SO4} diluted in water."}'
    repaired = _repair_json_text(broken)
    import json as _json

    data = _json.loads(repaired)
    assert "\\ce{H2SO4}" in data["explanation"]


def test_repair_json_text_fixes_embedded_unescaped_quotes():
    """An unescaped quote inside a value must be escaped, not end the string."""
    from app.services.exam_generator import _repair_json_text

    broken = '{"question": "The teacher said "begin now" to the class.", "marks": 2}'
    repaired = _repair_json_text(broken)
    import json as _json

    data = _json.loads(repaired)
    assert data["marks"] == 2
    assert "begin now" in data["question"]


def test_repair_json_text_strips_trailing_commas():
    from app.services.exam_generator import _repair_json_text

    broken = '{"options": ["A. 1", "B. 2",], "marks": 1,}'
    repaired = _repair_json_text(broken)
    import json as _json

    assert _json.loads(repaired) == {"options": ["A. 1", "B. 2"], "marks": 1}


def test_repair_json_text_returns_valid_json_unchanged():
    from app.services.exam_generator import _repair_json_text

    valid = '{"a": "line\\nbreak \\t tab \\" quote", "b": [1, 2]}'
    assert _repair_json_text(valid) == valid


def test_parse_response_repairs_invalid_escape_before_failing():
    """parse_response must recover a complete JSON with bad escapes."""
    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    # Model output with a single-backslash LaTeX escape inside a string.
    response = '{"sections": [{"section_number": 1, "section_title": "SECTION A", "instruction": "Answer ALL", "questions": [{"id": 1, "type": "multiple_choice", "question": "Which compound is \\ce{NaCl}?", "options": ["A. Salt", "B. Sand", "C. Sugar", "D. Stone"], "correct_answer": "A", "marks": 2}]}]}'
    parsed = generator.parse_response(response, MOCK_SECTION_CONFIG[:1])
    assert parsed["sections"][0]["questions"][0]["marks"] == 2


@pytest.mark.asyncio
async def test_groq_reasoning_effort_low_for_gpt_oss(monkeypatch):
    """gpt-oss reasoning tokens must not eat the JSON output budget.

    Regression: production runs returned empty or truncated content because
    chain-of-thought consumed max_tokens. The Groq call must request
    reasoning_effort=low for gpt-oss models.
    """
    from app.core.llm import LLMService

    captured = {}

    class _FakeMessage:
        content = '{"ok": true}'

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeUsage:
        total_tokens = 10

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = _FakeUsage()

    class _FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return _FakeResponse()

    class _FakeChat:
        completions = _FakeCompletions()

    service = LLMService(groq_api_key="test-key")
    service.groq_client = type("C", (), {"chat": _FakeChat()})()

    await service.generate(prompt="p", max_tokens=1000, preferred_provider="groq")
    assert captured.get("reasoning_effort") == "low"
    assert captured.get("response_format") == {"type": "json_object"}


def test_difficulty_distribution_wired_into_prompt():
    """CP5: difficulty mix must reach the LLM prompt."""
    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    request = ExamGenerationRequest(
        subject="Mathematics",
        grade_level="Primary 5",
        difficulty_distribution={"easy": 0.5, "medium": 0.3, "hard": 0.2},
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A",
                question_type="multiple_choice",
                num_questions=10,
                marks_per_question=2,
                instruction_type="answer_all",
                sub_part_style="none",
            )
        ],
    )
    prompt = generator.build_prompt(request, {"combined_context": "ctx"})
    assert "DIFFICULTY DISTRIBUTION" in prompt
    assert "50% easy" in prompt
    assert "30% medium" in prompt
    assert "20% hard" in prompt
def test_parse_response_normalizes_british_bloom_spelling():
    """British/mixed-case Bloom levels are canonicalized at parse time.

    Regression for a real failure: the LLM returned "analyse" and validation
    then failed on "invalid Bloom level 'analyse'". Normalizing during
    parse_response means the persisted value and validation both see the
    canonical "analyze".
    """
    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    data = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A",
                "questions": [
                    {
                        "id": 1,
                        "type": "multiple_choice",
                        "question": "Q?",
                        "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
                        "correct_answer": "A",
                        "marks": 2,
                        "difficulty": "easy",
                        "bloom_level": "analyse",
                    },
                    {
                        "id": 2,
                        "type": "multiple_choice",
                        "question": "Q2?",
                        "options": ["A. 5", "B. 6", "C. 7", "D. 8"],
                        "correct_answer": "B",
                        "marks": 2,
                        "difficulty": "medium",
                        "bloom_level": "Analyse",
                    },
                ],
            }
        ]
    }

    parsed = generator.parse_response(json.dumps(data), MOCK_SECTION_CONFIG)
    questions = parsed["sections"][0]["questions"]
    assert questions[0]["bloom_level"] == "analyze"
    assert questions[1]["bloom_level"] == "analyze"
def test_parse_response_preserves_long_essay_correct_answer():
    """Essay/short-answer model answers are NOT truncated to a single char.

    Regression for a real failure: essay questions store their full model
    answer in ``correct_answer`` (e.g. "a) 5 × 1000 = ... e) Yes, because..."),
    but the DB column was VARCHAR(1) and Pydantic capped max_length=1, so
    generation failed at store time after a successful LLM call.
    """
    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    long_answer = (
        "a) 5 × 1000 = ₦5,000. "
        "b) 2 × 500 = ₦1,000. "
        "c) 5000 + 1000 = ₦6,000. "
        "d) 10000 - 6000 = ₦4,000. "
        "e) Yes, because ₦4,000 is greater than ₦800."
    )
    assert len(long_answer) > 1

    data = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION B",
                "questions": [
                    {
                        "id": 1,
                        "type": "essay",
                        "question": "Fatima went to the market...",
                        "marks": 20,
                        "difficulty": "hard",
                        "bloom_level": "analyze",
                        "correct_answer": long_answer,
                    }
                ],
            }
        ]
    }
    parsed = generator.parse_response(json.dumps(data), MOCK_SECTION_CONFIG)
    stored = parsed["sections"][0]["questions"][0]["correct_answer"]
    assert stored == long_answer


def test_question_bank_schema_accepts_long_essay_answer():
    """QuestionBankItemCreateRequest allows a multi-char correct_answer."""
    from app.schemas.exam import QuestionBankItemCreateRequest

    item = QuestionBankItemCreateRequest(
        subject="Mathematics",
        grade_level="Primary 4",
        question_type="essay",
        question_text="Explain how you would budget ₦10,000 for a week.",
        marks=5,
        correct_answer="= 5 × 1000 = ₦5,000 ... " * 5,  # far longer than 1 char
    )
    assert len(item.correct_answer) > 1


def test_resolve_optimal_provider():
    """Verify intelligent class & subject aware LLM routing."""
    # Senior Secondary STEM -> Gemini
    assert ExamGenerator._resolve_optimal_provider("Physics", "SSS 1", 20) == "gemini"
    assert ExamGenerator._resolve_optimal_provider("Chemistry", "SS 2", 25) == "gemini"
    assert ExamGenerator._resolve_optimal_provider("Further Mathematics", "SSS 3", 15) == "gemini"
    assert ExamGenerator._resolve_optimal_provider("Biology", "Senior Secondary 2", 20) == "gemini"

    # Primary and Junior Secondary -> Groq (for speed)
    assert ExamGenerator._resolve_optimal_provider("Mathematics", "Primary 4", 25) == "groq"
    assert ExamGenerator._resolve_optimal_provider("Basic Science", "JSS 2", 20) == "groq"
    assert ExamGenerator._resolve_optimal_provider("English Language", "Primary 6", 30) == "groq"
    assert ExamGenerator._resolve_optimal_provider("Social Studies", "JSS 1", 25) == "groq"

    # High question volume (> 30 questions) -> Gemini
    assert ExamGenerator._resolve_optimal_provider("English Language", "Primary 5", 35) == "gemini"
    assert ExamGenerator._resolve_optimal_provider("Civic Education", "JSS 3", 40) == "gemini"
