"""Exam and question models."""

from uuid import uuid4

from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Exam(BaseModel):
    """Generated exam."""
    
    __tablename__ = "exams"
    
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    subject = Column(String(100), nullable=False)
    grade_level = Column(String(50), nullable=False)  # JSS1, JSS2, SSS1, etc
    language = Column(String(20), nullable=False, default="English")  # language of instruction
    
    status = Column(String(20), default="draft")  # draft, under_review, approved
    workflow_state = Column(
        String(40),
        default="generation_requested",
    )  # generation_requested, teacher_review, final_submitted_by_teacher, approved
    llm_call_count = Column(Integer, default=0, nullable=False)
    llm_call_limit = Column(Integer, default=3, nullable=False)

    total_marks = Column(Integer, default=100)
    
    # Metadata
    duration_minutes = Column(Integer)  # Time allowed for exam
    instructions = Column(Text)
    # Optional table-of-specification captured at generation time. Keeping the
    # source blueprint with the exam makes review and export auditable.
    blueprint = Column(JSON, nullable=True)
    
    # Relationships
    school = relationship("School", back_populates="exams")
    created_by = relationship("User", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    passages = relationship("ExamPassage", back_populates="exam", cascade="all, delete-orphan")
    audit_comments = relationship(
        "ExamAuditComment",
        back_populates="exam",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, subject={self.subject}, grade_level={self.grade_level})>"

class ExamPassage(BaseModel):
    """A reading/comprehension passage attached to an exam section.

    The passage text is authoritative (teacher-supplied); generated questions
    are validated for lexical grounding against it (anti-hallucination).
    """

    __tablename__ = "exam_passages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    exam_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    section_number = Column(Integer, nullable=False, default=1)

    exam = relationship("Exam", back_populates="passages")

    def __repr__(self) -> str:
        return f"<ExamPassage(id={self.id}, exam_id={self.exam_id}, section={self.section_number})>"

class Question(BaseModel):
    """Individual exam question."""
    
    __tablename__ = "questions"
    
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    passage_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_passages.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    question_number = Column(Integer, nullable=False)
    section_number = Column(Integer, nullable=False, default=1)
    section_name = Column(String(50), nullable=True)
    type = Column(String(30), nullable=False)  # multiple_choice, short_answer, essay
    
    question_text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)
    
    # Question attributes
    difficulty = Column(String(20))  # easy, medium, hard
    bloom_level = Column(String(20))  # remember, understand, apply, analyze
    topic = Column(String(255))
    
    # MCQ fields
    options = Column(JSON)  # ["A. Option 1", "B. Option 2", ...]
    correct_answer = Column(Text)  # MCQ letter ("C") OR full model answer for essay/short-answer
    explanation = Column(Text)
    
    # Short answer/Essay fields
    marking_scheme = Column(JSON)  # List of marking points
    sub_parts = Column(JSON)  # For essays: [{"part": "a", "question": "...", "marks": 3}]
    
    # Diagram support
    diagram_svg = Column(Text)  # SVG diagram if applicable
    
    # Relationships
    exam = relationship("Exam", back_populates="questions")
    passage = relationship("ExamPassage", foreign_keys=[passage_id])
    refinements = relationship(
        "QuestionRefinement",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    audit_comments = relationship(
        "ExamAuditComment",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, exam_id={self.exam_id}, type={self.type})>"
