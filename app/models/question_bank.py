"""Question bank models for reusable school questions."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class QuestionBankItem(BaseModel):
    """Reusable question bank item.

    Tenancy model (curriculum-first, no auto-sharing):
    - Platform-owned questions are ingested ONLY via the admin ingestion
      script: ``owner_type='platform'`` with ``school_id IS NULL``. They form
      the shared few-shot corpus used by ExamGenerator.
    - School-contributed questions have ``owner_type='school'`` and a real
      ``school_id``; they are visible only to their school and are NEVER
      injected into other schools' prompts.
    """

    __tablename__ = "question_bank_items"

    # --- Ownership / tenancy ---------------------------------------------
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=True,  # NULL for platform-owned questions
    )
    # platform | school — no default on purpose: every creation site must
    # state ownership explicitly (regression guard for cross-tenant leaks).
    owner_type = Column(String(20), nullable=False)

    source_exam_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Curriculum alignment (shared corpus tie-in) ----------------------
    curriculum_id = Column(
        UUID(as_uuid=True),
        ForeignKey("curriculums.id", ondelete="SET NULL"),
        nullable=True,
    )
    week_index = Column(Integer, nullable=True)  # scheme_of_works week_number
    exam_type = Column(String(30), nullable=True)  # WAEC, NECO, mock, internal
    source_year = Column(Integer, nullable=True)

    subject = Column(String(100), nullable=False)
    grade_level = Column(String(50), nullable=False)
    topic = Column(String(255), nullable=True)
    difficulty = Column(String(20), nullable=True)

    question_type = Column(String(30), nullable=False)
    question_text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)
    options = Column(JSON, nullable=True)
    correct_answer = Column(String(1), nullable=True)
    explanation = Column(Text, nullable=True)
    marking_scheme = Column(JSON, nullable=True)
    sub_parts = Column(JSON, nullable=True)
    diagram_svg = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    # Owner curation queue: platform rows are 'approved' by definition;
    # school-contributed rows start 'pending' and only an explicit owner
    # promotion (app/scripts/promote_bank_items.py) flips them to
    # owner_type='platform' — school rows can never enter the shared
    # few-shot corpus without that manual owner action.
    review_status = Column(String(20), nullable=False, default="approved")

    school = relationship("School")
    source_exam = relationship("Exam")
    source_question = relationship("Question")
    created_by = relationship("User")
    curriculum = relationship("Curriculum", foreign_keys=[curriculum_id])
