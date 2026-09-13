"""Exam generation and management schemas."""

from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PassageSpec(BaseModel):
    """A reading/comprehension passage accompanying a section's questions.

    The teacher supplies the passage text; the LLM writes only the questions,
    grounded against it. Using the authoritative requested passage (not an LLM
    copy) keeps comprehension sections hallucination-resistant.
    """

    title: str = Field(default="", max_length=200, description="Passage title/heading")
    body: str = Field(..., min_length=40, max_length=4000, description="Passage text")


class SectionConfig(BaseModel):
    """Configuration for a single exam section."""
    
    section_number: int = Field(..., ge=1, description="Section number (1, 2, 3...)")
    section_title: str = Field(..., description="Section title (e.g., 'SECTION A: OBJECTIVES')")
    question_type: str = Field(..., description="Question type: multiple_choice, short_answer, essay, true_false")
    num_questions: int = Field(..., ge=1, le=100, description="Number of questions in this section")
    marks_per_question: Optional[int] = Field(None, ge=1, description="Marks per question (if uniform)")
    
    instruction_type: str = Field(
        "answer_all",
        description="Instruction type: answer_all, answer_any_n, compulsory_plus_optional"
    )
    answer_count: Optional[int] = Field(None, description="Number of questions to answer (for answer_any_n)")
    compulsory_questions: Optional[List[int]] = Field(None, description="Compulsory question numbers")
    
    sub_part_style: str = Field(
        "none",
        description="Sub-part numbering: none, roman (i,ii,iii), letter (a,b,c), number (1,2,3)"
    )
    sub_parts_per_question: Optional[int] = Field(None, ge=1, le=10, description="Sub-parts per question")
    allow_sub_parts: bool = Field(
        False,
        description="Spread theory/short-answer questions into (a)/(b) sub-parts with summing marks",
    )
    passage: Optional[PassageSpec] = Field(
        None,
        description="Reading passage all questions in this section must be answered from",
    )

    @field_validator("instruction_type")
    @classmethod
    def validate_instruction_type(cls, v):
        allowed = ["answer_all", "answer_any_n", "compulsory_plus_optional"]
        if v not in allowed:
            raise ValueError(f"instruction_type must be one of {allowed}")
        return v
    
    @field_validator("sub_part_style")
    @classmethod
    def validate_sub_part_style(cls, v):
        allowed = ["none", "roman", "letter", "number"]
        if v not in allowed:
            raise ValueError(f"sub_part_style must be one of {allowed}")
        return v
    
    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v):
        allowed = ["multiple_choice", "short_answer", "essay", "true_false"]
        if v not in allowed:
            raise ValueError(f"question_type must be one of {allowed}")
        return v
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "section_number": 1,
                "section_title": "SECTION A: OBJECTIVES",
                "question_type": "multiple_choice",
                "num_questions": 20,
                "marks_per_question": 2,
                "instruction_type": "answer_all",
                "sub_part_style": "none"
            }
        })


class ExamGenerationRequest(BaseModel):
    """Request schema for generating an exam."""

    subject: str = Field(..., min_length=1, max_length=100, description="Subject name")
    grade_level: str = Field(..., description="Grade level (e.g., Primary 4)")
    term: Optional[str] = Field(None, description="Term (First Term, Second Term, Third Term)")
    selected_weeks: Optional[List[int]] = Field(None, description="Selected Scheme of Work weeks (e.g. [1, 2, 3, 4])")

    sections: List[SectionConfig] = Field(..., min_length=1, max_length=5, description="Exam sections")

    duration_minutes: Optional[int] = Field(120, ge=30, le=300, description="Exam duration in minutes")
    custom_instructions: Optional[str] = Field(None, max_length=1000, description="Teacher's custom instructions")
    include_diagrams: bool = Field(False, description="Allow compact markdown/mermaid visual blocks in questions")
    language: str = Field(
        "English",
        max_length=30,
        description="Language of instruction for questions/answers (English, Igbo, Yoruba, Hausa...)",
    )

    difficulty_distribution: Optional[Dict[str, float]] = Field(
        None,
        description='Requested difficulty mix, e.g. {"easy": 0.4, "medium": 0.4, "hard": 0.2}',
    )
    
    @field_validator("sections")
    @classmethod
    def validate_sections(cls, sections):
        """Validate section configuration."""
        # Check section numbers are sequential
        section_numbers = [s.section_number for s in sections]
        if section_numbers != list(range(1, len(sections) + 1)):
            raise ValueError("Section numbers must be sequential starting from 1")
        
        # Validate total questions
        total_questions = sum(s.num_questions for s in sections)
        if total_questions > 100:
            raise ValueError(f"Total questions ({total_questions}) cannot exceed 100")
        
        return sections
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "subject": "Basic Science",
                "grade_level": "JSS 2",
                "document_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "sections": [
                    {
                        "section_number": 1,
                        "section_title": "SECTION A: OBJECTIVES",
                        "question_type": "multiple_choice",
                        "num_questions": 20,
                        "marks_per_question": 2,
                        "instruction_type": "answer_all",
                        "sub_part_style": "none"
                    },
                    {
                        "section_number": 2,
                        "section_title": "SECTION B: THEORY",
                        "question_type": "essay",
                        "num_questions": 5,
                        "instruction_type": "answer_any_n",
                        "answer_count": 3,
                        "sub_part_style": "letter",
                        "sub_parts_per_question": 3
                    }
                ],
                "duration_minutes": 90,
                "custom_instructions": "Focus on practical applications"
            }
        })


class ExamUpdateRequest(BaseModel):
    """Request schema for updating an exam."""

    status: Optional[str] = Field(None, description="Exam status: draft, under_review")
    instructions: Optional[str] = Field(None, max_length=2000, description="Exam instructions")
    duration_minutes: Optional[int] = Field(None, ge=30, le=300, description="Exam duration")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            # "approved" is intentionally unreachable here: approval must go
            # through the governed approve endpoint (preflight + workflow).
            allowed = ["draft", "under_review"]
            if v not in allowed:
                raise ValueError(f"status must be one of {allowed}")
        return v


class SubPartResponse(BaseModel):
    """Response schema for question sub-parts."""
    
    part: str = Field(..., description="Sub-part identifier (a, b, c or i, ii, iii)")
    question: str = Field(..., description="Sub-part question text")
    marks: int = Field(..., description="Marks for this sub-part")
    marking_scheme: Optional[List[str]] = Field(None, description="Marking scheme points")


class QuestionResponse(BaseModel):
    """Response schema for a single question."""
    
    id: UUID
    question_number: int
    type: str
    question_text: str
    marks: int
    
    # Optional fields
    difficulty: Optional[str] = None
    bloom_level: Optional[str] = None
    topic: Optional[str] = None
    
    # MCQ fields
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    
    # Short answer/Essay fields
    marking_scheme: Optional[List[str]] = None
    sub_parts: Optional[List[dict]] = None

    # Diagram
    diagram_svg: Optional[str] = None

    # Comprehension passage link
    passage_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class QuestionEditRequest(BaseModel):
    """Request schema for manually editing an exam question."""

    question_text: Optional[str] = Field(None, min_length=3, max_length=5000, description="Updated question text")
    options: Optional[List[str]] = Field(None, description="Updated options list (for MCQ)")
    correct_answer: Optional[str] = Field(None, description="Updated correct answer")
    marks: Optional[int] = Field(None, ge=1, le=100, description="Updated marks")
    explanation: Optional[str] = Field(None, max_length=2000, description="Updated explanation")
    marking_scheme: Optional[List[str]] = Field(None, description="Updated marking scheme points")


class SectionResponse(BaseModel):
    """Response schema for an exam section."""
    
    section_number: int
    section_title: str
    instruction: str
    questions: List[QuestionResponse]
    total_marks: int


class ExamResponse(BaseModel):
    """Response schema for a complete exam."""

    id: UUID
    school_id: UUID
    created_by_user_id: Optional[UUID] = None
    
    subject: str
    grade_level: str
    status: str
    workflow_state: str = "teacher_review"  # FRONTEND_SPEC §3.1 badge/action mapping
    total_marks: int
    
    duration_minutes: Optional[int] = None
    instructions: Optional[str] = None
    language: str = "English"
    
    sections: Optional[List[SectionResponse]] = None
    questions: Optional[List[QuestionResponse]] = None  # Flat list for backward compatibility
    passages: Optional[List["ExamPassageResponse"]] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ExamPassageResponse(BaseModel):
    """Response schema for a reading passage attached to an exam section."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exam_id: UUID
    title: Optional[str] = None
    body: str
    section_number: int


class ExamListItem(BaseModel):
    """Response schema for exam list item (summary)."""
    
    id: UUID
    subject: str
    grade_level: str
    status: str
    total_marks: int
    question_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ExamListResponse(BaseModel):
    """Response schema for exam list."""
    
    total: int
    exams: List[ExamListItem]


class ExamGenerationResponse(BaseModel):
    """Response schema for exam generation request (background task)."""

    message: str
    exam_id: UUID
    status: str
    poll_endpoint: str
    estimated_time_seconds: int
    warnings: Optional[List[str]] = Field(
        default=None,
        description="Curriculum coverage notices (e.g. missing scheme-of-work data)",
    )


class ExamRegenerationRequest(BaseModel):
    """Request to regenerate or correct an exam."""
    
    feedback: str = Field(..., description="Instructions for what to change/correct")
    question_ids: Optional[List[UUID]] = Field(None, description="Specific questions to regenerate (if empty, applies to whole exam logic)")


class ExamExportRequest(BaseModel):
    """Request options for exporting an exam."""

    format: str = Field(default="pdf", description="Export format (pdf only for MVP)")
    include_answers: bool = Field(default=False, description="Include answers/marking hints")


class ExamExportResponse(BaseModel):
    """Response schema for exam export."""

    message: str
    file_name: str
    download_url: str


class ExamAuditCommentCreateRequest(BaseModel):
    """Request for teacher/auditor exam comment submission."""

    question_id: Optional[UUID] = Field(
        default=None,
        description="Optional specific question ID for targeted feedback",
    )
    comment_text: str = Field(..., min_length=5, max_length=2000)
    suggested_question_text: Optional[str] = Field(default=None, max_length=5000)
    suggested_marking_scheme: Optional[List[str]] = Field(default=None)


class ExamAuditCommentResponse(BaseModel):
    """Response schema for exam audit comments."""

    id: UUID
    exam_id: UUID
    question_id: Optional[UUID] = None
    author_user_id: Optional[UUID] = None
    comment_text: str
    suggested_question_text: Optional[str] = None
    suggested_marking_scheme: Optional[str] = None
    status: str
    resolved_by_user_id: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamRefineFromCommentsRequest(BaseModel):
    """Admin request to batch refine using submitted audit comments."""

    comment_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional subset of comment IDs; defaults to all open comments",
    )
    additional_feedback: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional admin instruction appended to teacher feedback",
    )


class ExamGenerationProposalCreateRequest(BaseModel):
    """Teacher/auditor proposal for admin-driven generation."""

    subject: str = Field(..., min_length=1, max_length=100)
    grade_level: str = Field(..., min_length=1, max_length=50)
    term: Optional[str] = Field(
        default=None,
        description="Term (First Term, Second Term, Third Term)",
    )
    selected_weeks: Optional[List[int]] = Field(
        default=None,
        description="Selected Scheme of Work weeks (e.g. [1, 2, 3])",
    )
    desired_outcomes: str = Field(..., min_length=10, max_length=3000)
    custom_instructions: Optional[str] = Field(default=None, max_length=3000)
    draft_questions: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Optional teacher-proposed draft questions text",
    )


class ExamGenerationProposalResponse(BaseModel):
    """Proposal response payload."""

    id: UUID
    school_id: UUID
    requested_by_user_id: Optional[UUID] = None
    used_by_user_id: Optional[UUID] = None
    used_at: Optional[datetime] = None
    subject: str
    grade_level: str
    term: Optional[str] = None
    selected_weeks: Optional[List[int]] = None
    desired_outcomes: str
    custom_instructions: Optional[str] = None
    draft_questions: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateFromProposalRequest(BaseModel):
    """Admin request to generate exam from a proposal."""

    sections: List[SectionConfig] = Field(..., min_length=1, max_length=5)
    duration_minutes: Optional[int] = Field(120, ge=30, le=300)
    include_diagrams: bool = Field(False)
    additional_admin_instructions: Optional[str] = Field(default=None, max_length=2000)
    term: Optional[str] = Field(
        default=None,
        description="Overrides proposal term for scheme-of-work alignment",
    )
    selected_weeks: Optional[List[int]] = Field(
        default=None,
        description="Overrides proposal weeks for scheme-of-work alignment",
    )


class ManualQuestionInput(BaseModel):
    """Teacher-provided question payload for manual submission."""

    question_number: int = Field(..., ge=1)
    type: str = Field(..., description="multiple_choice, short_answer, essay, true_false")
    question_text: str = Field(..., min_length=3)
    marks: int = Field(..., ge=1, le=100)
    difficulty: Optional[str] = None
    bloom_level: Optional[str] = None
    topic: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    marking_scheme: Optional[List[str]] = None
    sub_parts: Optional[List[SubPartResponse]] = None
    diagram_svg: Optional[str] = None


class ManualExamSubmissionRequest(BaseModel):
    """Manual exam submission where teacher writes full questions without AI."""

    subject: str = Field(..., min_length=1, max_length=100)
    grade_level: str = Field(..., min_length=1, max_length=50)
    duration_minutes: Optional[int] = Field(120, ge=30, le=300)
    instructions: Optional[str] = Field(default=None, max_length=2000)
    language: str = Field(
        "English",
        max_length=30,
        description="Language of instruction (English, Igbo, Yoruba, Hausa...)",
    )
    questions: List[ManualQuestionInput] = Field(..., min_length=1, max_length=200)


class QuestionBankSaveRequest(BaseModel):
    """Save questions from an exam into the question bank."""

    question_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional subset of question IDs; if omitted, saves all exam questions",
    )


class QuestionBankItemResponse(BaseModel):
    """Question bank item response."""

    id: UUID
    school_id: Optional[UUID] = None
    source_exam_id: Optional[UUID] = None
    source_question_id: Optional[UUID] = None
    created_by_user_id: Optional[UUID] = None
    owner_type: str = "school"
    curriculum_id: Optional[UUID] = None
    week_index: Optional[int] = None
    exam_type: Optional[str] = None
    source_year: Optional[int] = None
    subject: str
    grade_level: str
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: str
    question_text: str
    marks: int
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    marking_scheme: Optional[List[str]] = None
    sub_parts: Optional[List[dict]] = None
    diagram_svg: Optional[str] = None
    is_active: bool
    usage_count: int = 0
    review_status: str = "approved"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionBankItemUpdateRequest(BaseModel):
    """Manual edit request for a question bank item."""

    topic: Optional[str] = Field(default=None, max_length=255)
    difficulty: Optional[str] = Field(default=None, max_length=20)
    question_text: Optional[str] = Field(default=None, min_length=3, max_length=5000)
    marks: Optional[int] = Field(default=None, ge=1, le=100)
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = Field(default=None, max_length=20000)
    explanation: Optional[str] = Field(default=None, max_length=5000)
    marking_scheme: Optional[List[str]] = None
    sub_parts: Optional[List[dict]] = None
    diagram_svg: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionBankItemCreateRequest(BaseModel):
    """Manual addition of a reusable question to the school question bank."""

    subject: str = Field(..., min_length=2, max_length=100)
    grade_level: str = Field(..., min_length=2, max_length=50)
    topic: Optional[str] = Field(default=None, max_length=255)
    difficulty: Optional[str] = Field(default="medium", max_length=20)
    question_type: str = Field(default="multiple_choice", max_length=30)
    question_text: str = Field(..., min_length=3, max_length=5000)
    marks: int = Field(default=1, ge=1, le=100)
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = Field(default=None, max_length=20000)
    explanation: Optional[str] = Field(default=None, max_length=5000)
    marking_scheme: Optional[List[str]] = None


class QuestionBankImportRequest(BaseModel):
    """Request to import questions from Question Bank into an Exam section."""

    bank_item_ids: List[UUID] = Field(..., min_length=1, description="List of bank question IDs to import")
    section_number: int = Field(default=1, ge=1, description="Target section number")
    section_name: Optional[str] = Field(default=None, max_length=100, description="Target section name")

