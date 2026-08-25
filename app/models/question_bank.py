"""Question bank models for reusable school questions."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class QuestionBankItem(BaseModel):
    """Reusable question bank item.

    Tenancy model (curriculum-first):
    - Platform-owned questions (from past-paper ingestion) have ``owner_type='platform'``
      and ``school_id IS NULL`` — they belong to the SHARED corpus.
    - School-contributed questions have ``owner_type='school'`` and a real ``school_id``.
    """

    __tablename__ = "question_bank_items"

    # --- Ownership / tenancy ---------------------------------------------
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=True,  # NULL for platform-owned questions
    )
    owner_type = Column(String(20), nullable=False, default="platform")  # platform | school

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

    # --- Optional pgvector embedding (upgraded by migration 0011) ---------
    # Starts as JSON (a plain float array) in the Python model; migration 0011
    # re-types it to VECTOR(1024) when pgvector is installed on the server.
    embedding = Column(JSON, nullable=True)

    school = relationship("School")
    source_exam = relationship("Exam")
    source_question = relationship("Question")
    created_by = relationship("User")
    curriculum = relationship("Curriculum", foreign_keys=[curriculum_id])
