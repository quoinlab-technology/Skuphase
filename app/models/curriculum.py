"""Curriculum and Scheme of Work models."""

import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Curriculum(BaseModel):
    """
    Canonical Curriculum Entity.
    
    Represents an official curriculum subject definition for a specific grade level
    under an educational board (e.g. NERDC, WAEC, NECO).
    """
    __tablename__ = "curriculums"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country = Column(String(10), default="NG", nullable=False)
    board = Column(String(50), default="NERDC", nullable=False, index=True)
    class_level = Column(String(50), nullable=False, index=True)
    subject_name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=True)
    # Data-driven display/lookup ordering (Pre-Nursery=1 ... SSS 3=16) so
    # adding JSS/SSS later requires data only, no code change.
    level_order = Column(Integer, nullable=True, index=True)

    # Relationships
    schemes = relationship(
        "SchemeOfWork",
        back_populates="curriculum",
        cascade="all, delete-orphan",
        order_by="SchemeOfWork.week_number",
    )

    __table_args__ = (
        Index("ix_curriculums_lookup", "board", "class_level", "subject_name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Curriculum(id={self.id}, board={self.board}, class={self.class_level}, subject={self.subject_name})>"


class SchemeOfWork(BaseModel):
    """
    Weekly Scheme of Work breakdown.
    
    Contains topic titles, subtopics, and behavioral learning objectives per week for each term.
    """
    __tablename__ = "scheme_of_works"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    curriculum_id = Column(
        UUID(as_uuid=True),
        ForeignKey("curriculums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    term = Column(String(20), nullable=False, index=True)  # First Term, Second Term, Third Term
    week_number = Column(Integer, nullable=False, index=True)  # 1 to 13
    topic = Column(String(255), nullable=False)
    subtopics = Column(JSONB, default=list, nullable=False)  # List of detailed learning objectives
    raw_content = Column(Text, nullable=True)
    is_exam_or_break = Column(Boolean, default=False, nullable=False)

    # Relationships
    curriculum = relationship("Curriculum", back_populates="schemes")

    __table_args__ = (
        Index("ix_scheme_lookup", "curriculum_id", "term", "week_number", unique=True),
    )

    def __repr__(self) -> str:
        return f"<SchemeOfWork(id={self.id}, term={self.term}, week={self.week_number}, topic={self.topic})>"
