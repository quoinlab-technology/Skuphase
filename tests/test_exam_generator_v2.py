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



def test_repair_restores_latex_commands_eaten_by_valid_json_escapes():
    """Single-backslash LaTeX whose first letter is a valid JSON escape
    (e.g. \\frac -> form feed, \\times -> tab) must be restored, not lost.

    This is the silent-corruption variant of the production failure: JSON
    parses fine but formulas render garbled.
    """
    from app.services.exam_generator import _repair_json_text

    import json as _json

    broken = '{"q": "Solve $\\\\frac{1}{2}x + $\\\\times$ $\\\\theta$, $\\\\beta = \\\\rho \\\\rightarrow \\\\neq x"}'
    repaired = _repair_json_text(broken)
    data = _json.loads(repaired)
    assert "\\frac{1}{2}" in data["q"]
    assert "\\times" in data["q"]
    assert "\\theta" in data["q"]
    assert "\\beta" in data["q"]
    assert "\\rho" in data["q"]
    assert "\\rightarrow" in data["q"]
    assert "\\neq" in data["q"]


def test_repair_leaves_real_json_escapes_in_prose_untouched():
    """Genuine \\n / \\t escapes not part of LaTeX commands must survive."""
    from app.services.exam_generator import _repair_json_text

    import json as _json

    valid = '{"a": "line one\\nline two", "b": "col\\there"}'
    repaired = _repair_json_text(valid)
    data = _json.loads(repaired)
    assert data["a"] == "line one\nline two"
    assert data["b"] == "col\there"


def test_repair_does_not_double_escape_correct_latex():
    from app.services.exam_generator import _repair_json_text

    import json as _json

    correct = '{"explanation": "$x = \\\\frac{-b}{2a}$ and $\\\\ce{H2SO4}$"}'
    assert _repair_json_text(correct) == correct
    data = _json.loads(correct)
    assert data["explanation"] == "$x = \\frac{-b}{2a}$ and $\\ce{H2SO4}$"


def test_build_prompt_contains_rendering_contract_for_maths():
    """STEM exams must instruct KaTeX figures and structured blocks."""
    from unittest.mock import patch

    from app.schemas.exam import ExamGenerationRequest, SectionConfig
    from app.services.exam_generator import ExamGenerator

    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    request = ExamGenerationRequest(
        subject="Mathematics",
        grade_level="SSS 2",
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A",
                question_type="multiple_choice",
                num_questions=2,
            )
        ],
    )
    prompt = generator.build_prompt(request, {"combined_context": "ctx"})
    assert "RENDERING CONTRACT" in prompt
    assert "content_blocks" in prompt
    assert "diagram_svg" in prompt
    assert "mermaid" not in prompt.lower()


def test_build_prompt_includes_mermaid_when_diagrams_enabled():
    from unittest.mock import patch

    from app.schemas.exam import ExamGenerationRequest, SectionConfig
    from app.services.exam_generator import ExamGenerator

    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    def _request(include_diagrams: bool):
        return ExamGenerationRequest(
            subject="Biology",
            grade_level="SSS 1",
            include_diagrams=include_diagrams,
            sections=[
                SectionConfig(
                    section_number=1,
                    section_title="SECTION A",
                    question_type="multiple_choice",
                    num_questions=1,
                )
            ],
        )

    on_prompt = generator.build_prompt(_request(True), {"combined_context": "ctx"})
    off_prompt = generator.build_prompt(_request(False), {"combined_context": "ctx"})
    assert "mermaid" in on_prompt.lower()
    assert "mermaid" not in off_prompt.lower()


def test_sanitize_content_blocks_keeps_safe_drops_unsafe():
    from app.services.svg_safety import sanitize_content_blocks

    blocks = [
        {"type": "text", "text": "Step 1: factorise $x^2 - 9$:"},
        {"type": "math", "latex": "x = \\frac{27}{3}"},
        {"type": "table", "rows": [["x", "y"], ["1", "3"]]},
        {"type": "svg", "svg": "<svg xmlns='http://www.w3.org/2000/svg'><circle cx='1' cy='1' r='1'/></svg>"},
        {"type": "mermaid", "diagram": "graph TD\n A-->B"},
        {"type": "video", "src": "x.mp4"},
        {"type": "svg", "svg": "<svg><script>alert(1)</script></svg>"},
        {"type": "mermaid", "diagram": "just some prose"},
        {"type": "mermaid", "diagram": "graph TD\n A[\"<script>alert(1)</script>\"]-->B"},
        "not-a-dict",
    ]
    cleaned = sanitize_content_blocks(blocks)
    kinds = [b["type"] for b in cleaned]
    assert kinds == ["text", "math", "table", "svg", "mermaid"]
    assert cleaned[3]["svg"].startswith("<svg")
    assert "<script" not in cleaned[3]["svg"].lower()
    assert cleaned[4]["diagram"].startswith("graph")


def test_sanitize_mermaid_rejects_unknown_keyword_and_none_input():
    from app.services.svg_safety import sanitize_mermaid

    assert sanitize_mermaid(None) is None
    assert sanitize_mermaid("") is None
    assert sanitize_mermaid("flowchart LR\n A-->B") is not None
    assert sanitize_mermaid("sequenceDiagram\n A->>B: hi") is not None
    assert sanitize_mermaid("Hello world") is None


def test_render_structured_blocks_renders_mermaid():
    from app.frontend.components.exam import render_structured_blocks

    rendered = render_structured_blocks([{"type": "mermaid", "diagram": "graph TD\n A-->B"}])
    html = str(rendered)
    assert "data-fs-mermaid" in html
    assert "graph TD" in html


def test_render_structured_blocks_skips_malicious_mermaid():
    from app.frontend.components.exam import render_structured_blocks

    assert render_structured_blocks([{"type": "mermaid", "diagram": "graph TD\n <script>x</script>"}]) is None


@pytest.mark.asyncio
async def test_normalize_choice_answers_maps_shapes_to_letters():
    """Cosmetic correct_answer shapes must normalize before validation."""
    from app.services.exam_generator import _normalize_choice_answers

    parsed = {
        "sections": [
            {
                "questions": [
                    {"type": "multiple_choice", "correct_answer": "b", "options": ["A. 1", "B. 2"]},
                    {"type": "multiple_choice", "correct_answer": "C. Three", "options": ["A. 1", "B. 2", "C. Three", "D. 4"]},
                    {"type": "multiple_choice", "correct_answer": "$46,000", "options": ["A. $42,000", "B. $46,000", "C. $40,000", "D. $44,000"]},
                    {"type": "true_false", "correct_answer": "True", "options": ["A. True", "B. False"]},
                    {"type": "multiple_choice", "correct_answer": "Z", "options": ["A. 1", "B. 2", "C. 3", "D. 4"]},
                    {"type": "essay", "correct_answer": "free text stays"},
                ]
            }
        ]
    }
    _normalize_choice_answers(parsed, [])
    got = [q["correct_answer"] for q in parsed["sections"][0]["questions"]]
    assert got == ["B", "C", "B", "A", "Z", "free text stays"]


def test_prompt_declares_answer_key_discipline():
    from unittest.mock import patch

    from app.schemas.exam import ExamGenerationRequest, SectionConfig
    from app.services.exam_generator import ExamGenerator

    with patch("app.services.exam_generator.get_llm_service"):
        generator = ExamGenerator()

    request = ExamGenerationRequest(
        subject="Mathematics",
        grade_level="JSS 3",
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A",
                question_type="multiple_choice",
                num_questions=1,
            )
        ],
    )
    prompt = generator.build_prompt(request, {"combined_context": "ctx"})
    assert "ANSWER-KEY DISCIPLINE" in prompt
    assert "bare letter" in prompt


@pytest.mark.asyncio
async def test_store_exam_persists_sanitized_content_blocks():
    """AI-generated content_blocks must survive store_exam (cleaned)."""
    import uuid
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.services.exam_generator import ExamGenerator

    def _generator():
        with patch("app.services.exam_generator.get_llm_service"):
            return ExamGenerator()

    generator = _generator()

    from app.schemas.exam import ExamGenerationRequest, SectionConfig

    request = ExamGenerationRequest(
        subject="Mathematics",
        grade_level="JSS 2",
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A",
                question_type="multiple_choice",
                num_questions=1,
            )
        ],
    )
    parsed = {
        "sections": [
            {
                "section_number": 1,
                "section_title": "SECTION A",
                "questions": [
                    {
                        "type": "multiple_choice",
                        "question": "Solve $2x = 6$.",
                        "marks": 2,
                        "options": ["A. 2", "B. 3", "C. 4", "D. 5"],
                        "correct_answer": "B",
                        "diagram_svg": None,
                        "content_blocks": [
                            {"type": "math", "latex": "x = \\frac{6}{2}"},
                            {"type": "video", "src": "drop-me.mp4"},
                        ],
                    }
                ],
            }
        ]
    }
    db = AsyncMock()
    added = []
    db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    existing = SimpleNamespace(
        id=uuid.uuid4(), total_marks=0, status="draft", workflow_state="draft", updated_at=None,
        language=None,
    )
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: existing))

    result = await generator.store_exam(
        parsed_exam=parsed,
        request=request,
        school_id=uuid.uuid4(),
        created_by_user_id=uuid.uuid4(),
        llm_response={"provider": "test"},
        db=db,
        exam_id=existing.id,
    )
    assert result is not None
    questions = [o for o in added if type(o).__name__ == "Question"]
    assert len(questions) == 1
    stored = questions[0].content_blocks
    assert stored is not None
    assert [b["type"] for b in stored] == ["math"]
    assert "frac" in stored[0]["latex"]


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
