"""Question feedback and refinement history models."""

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class QuestionRefinement(BaseModel):
    """Stores refinement history for generated questions."""

    __tablename__ = "question_refinements"

    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    refined_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    feedback = Column(Text, nullable=False)
    original_text = Column(Text, nullable=False)
    refined_text = Column(Text, nullable=False)

    question = relationship("Question", back_populates="refinements")
    refined_by = relationship("User")


class ExamAuditComment(BaseModel):
    """Teacher/auditor comments against an exam or specific question."""

    __tablename__ = "exam_audit_comments"

    exam_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=True,
    )
    author_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment_text = Column(Text, nullable=False)
    suggested_question_text = Column(Text, nullable=True)
    suggested_marking_scheme = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="open")
    resolved_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    exam = relationship("Exam", back_populates="audit_comments")
    question = relationship("Question", back_populates="audit_comments")
    author = relationship(
        "User",
        foreign_keys=[author_user_id],
        back_populates="audit_comments",
    )
    resolved_by = relationship(
        "User",
        foreign_keys=[resolved_by_user_id],
        back_populates="resolved_audit_comments",
    )
