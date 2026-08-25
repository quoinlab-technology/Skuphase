"""Exam generation proposal models."""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ExamGenerationProposal(BaseModel):
    """Teacher/auditor proposal queued for admin-driven generation."""

    __tablename__ = "exam_generation_proposals"

    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    used_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    used_at = Column(DateTime(timezone=True), nullable=True)

    subject = Column(String(100), nullable=False)
    grade_level = Column(String(50), nullable=False)
    document_ids = Column(JSON, nullable=False, default=list)  # optional supplements
    desired_outcomes = Column(Text, nullable=False)
    custom_instructions = Column(Text, nullable=True)
    draft_questions = Column(Text, nullable=True)
    term = Column(String(20), nullable=True)  # scheme-of-work alignment
    selected_weeks = Column(JSON, nullable=True)  # list[int]
    status = Column(String(20), nullable=False, default="open")

    school = relationship("School")
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    used_by = relationship("User", foreign_keys=[used_by_user_id])
