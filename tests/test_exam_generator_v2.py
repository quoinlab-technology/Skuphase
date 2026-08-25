import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.exam_generator import ExamGenerator
from app.schemas.exam import ExamGenerationRequest, SectionConfig
from app.models.exam import Exam, Question

# Mock data
MOCK_SCHOOL_ID = uuid4()
MOCK_USER_ID = uuid4()
MOCK_DOC_ID = uuid4()

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
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "marks": 2
                },
                {
                    "id": 2,
                    "type": "multiple_choice",
                    "question": "Q2 Text",
                    "options": ["A", "B", "C", "D"],
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
def mock_rag_service():
    service = AsyncMock()
    service.search = AsyncMock(return_value=[
        {"content": "Chunk 1 content", "metadata": {}},
        {"content": "Chunk 2 content", "metadata": {}}
    ])
    return service

@pytest.fixture
def mock_llm_service():
    service = AsyncMock()
    service.generate = AsyncMock(return_value={
        "content": json.dumps(MOCK_LLM_RESPONSE_JSON),
        "tokens_used": 1000,
        "cost": 0.0
    })
    return service

@pytest.mark.asyncio
async def test_generate_exam_success(mock_db_session, mock_rag_service, mock_llm_service):
    """Test successful exam generation flow."""
    with patch("app.services.exam_generator.RAGService", return_value=mock_rag_service), \
         patch("app.services.exam_generator.get_llm_service", return_value=mock_llm_service), \
         patch("app.services.exam_generator.EmbeddingService"):
        
        generator = ExamGenerator()
        
        request = ExamGenerationRequest(
            subject="Physics",
            grade_level="SSS 1",
            document_ids=[MOCK_DOC_ID],
            sections=MOCK_SECTION_CONFIG,
            duration_minutes=60
        )
        
        exam = await generator.generate_exam(
            request=request,
            school_id=MOCK_SCHOOL_ID,
            created_by_user_id=MOCK_USER_ID,
            db=mock_db_session
        )
        
        # Verify RAG call
        mock_rag_service.search.assert_called_once()
        
        # Verify LLM call
        mock_llm_service.generate.assert_called_once()
        prompt = mock_llm_service.generate.call_args[1]["prompt"]
        assert "<internal_planning>" in prompt
        assert "SECTION A" in prompt
        assert "SECTION B" in prompt
        
        # Verify DB interactions
        assert mock_db_session.add.call_count >= 1  # Exam + Questions + Context
        mock_db_session.commit.assert_called_once()
        
        # Verify Exam object
        # Note: Since mock_db_session.add doesn't actually set IDs etc (it's a mock),
        # we check the arguments passed to it.
        
        # Check Exam creation
        exam_arg = mock_db_session.add.call_args_list[0][0][0]
        assert isinstance(exam_arg, Exam)
        assert exam_arg.subject == "Physics"
        assert exam_arg.total_marks == 14  # 2*2 + 10
        
        # Check Question creation (we have 3 questions total in the mocks? No, 2 MCQs + 1 Essay = 3 items in response JSON)
        # We need to filter the `add` calls to find Questions
        questions_added = [
            call[0][0] for call in mock_db_session.add.call_args_list 
            if isinstance(call[0][0], Question)
        ]
        assert len(questions_added) == 3
        
        # Verify question details
        assert questions_added[0].type == "multiple_choice"
        assert questions_added[2].type == "essay"
        assert questions_added[2].sub_parts is not None

@pytest.mark.asyncio
async def test_generate_exam_rag_failure(mock_db_session, mock_rag_service, mock_llm_service):
    """Test failure when RAG finds no content."""
    mock_rag_service.search.return_value = []  # No chunks
    
    with patch("app.services.exam_generator.RAGService", return_value=mock_rag_service), \
         patch("app.services.exam_generator.get_llm_service", return_value=mock_llm_service), \
         patch("app.services.exam_generator.EmbeddingService"):
        
        generator = ExamGenerator()
        request = ExamGenerationRequest(
            subject="Physics",
            grade_level="SSS 1",
            document_ids=[MOCK_DOC_ID],
            sections=MOCK_SECTION_CONFIG
        )
        
        with pytest.raises(ValueError, match="Exam generation failed"):
            await generator.generate_exam(
                request=request,
                school_id=MOCK_SCHOOL_ID,
                created_by_user_id=MOCK_USER_ID,
                db=mock_db_session
            )

@pytest.mark.asyncio
async def test_parse_response_validation():
    """Test response parsing validation logic."""
    generator = ExamGenerator()
    
    # Invalid JSON should raise ValueError
    bad_json = "{invalid_json}"
    with pytest.raises(ValueError, match="Invalid JSON response"):
        generator.parse_response(bad_json, MOCK_SECTION_CONFIG)
        
    # Missing 'sections' key should raise ValueError
    missing_sections = json.dumps({"foo": "bar"})
    with pytest.raises(ValueError, match="Response missing 'sections' key"):
        generator.parse_response(missing_sections, MOCK_SECTION_CONFIG)

    # Mismatch section count - logs warning but returns data (doesn't raise)
    # We just verify it parses what is there
    mismatch_response = json.dumps({"sections": []})
    parsed = generator.parse_response(mismatch_response, MOCK_SECTION_CONFIG)
    assert len(parsed["sections"]) == 0
        
    # Test valid parsing
    parsed = generator.parse_response(json.dumps(MOCK_LLM_RESPONSE_JSON), MOCK_SECTION_CONFIG)
    assert len(parsed["sections"]) == 2
