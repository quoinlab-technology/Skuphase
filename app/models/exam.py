"""Exam and question models."""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime, Boolean, Float 
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
    
    # Relationships
    school = relationship("School", back_populates="exams")
    created_by = relationship("User", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    context = relationship("ExamContext", back_populates="exam", cascade="all, delete-orphan")
    audit_comments = relationship(
        "ExamAuditComment",
        back_populates="exam",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, subject={self.subject}, grade_level={self.grade_level})>"


class Question(BaseModel):
    """Individual exam question."""
    
    __tablename__ = "questions"
    
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    
    question_number = Column(Integer, nullable=False)
    type = Column(String(30), nullable=False)  # multiple_choice, short_answer, essay
    
    question_text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)
    
    # Question attributes
    difficulty = Column(String(20))  # easy, medium, hard
    bloom_level = Column(String(20))  # remember, understand, apply, analyze
    topic = Column(String(255))
    
    # MCQ fields
    options = Column(JSON)  # ["A. Option 1", "B. Option 2", ...]
    correct_answer = Column(String(1))  # A, B, C, D
    explanation = Column(Text)
    
    # Short answer/Essay fields
    marking_scheme = Column(JSON)  # List of marking points
    sub_parts = Column(JSON)  # For essays: [{"part": "a", "question": "...", "marks": 3}]
    
    # Diagram support
    diagram_svg = Column(Text)  # SVG diagram if applicable
    
    # Relationships
    exam = relationship("Exam", back_populates="questions")
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
    asset_refs = relationship(
        "QuestionAssetRef",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Question(id={self.id}, exam_id={self.exam_id}, type={self.type})>"


class ExamContext(BaseModel):
    """Links generated exam to source documents for citations."""
    
    __tablename__ = "exam_context"
    
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("school_documents.id", ondelete="CASCADE"), nullable=False)
    
    relevance_score = Column(Float)
    extracted_context = Column(Text)  # Actual text retrieved from document
    context_type = Column(String(50))  # curriculum_reference, past_paper_pattern, lesson_note_alignment
    
    # Relationships
    exam = relationship("Exam", back_populates="context")
    document = relationship("SchoolDocument", back_populates="exam_context")
    
    def __repr__(self) -> str:
        return f"<ExamContext(exam_id={self.exam_id}, document_id={self.document_id})>"
