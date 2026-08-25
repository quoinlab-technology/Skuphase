"""Quality report snapshot models."""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ExamQualitySnapshot(BaseModel):
    """Stored quality/coverage report snapshot for an exam."""

    __tablename__ = "exam_quality_snapshots"

    exam_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    quality_status = Column(String(20), nullable=False)
    overall_score = Column(String(10), nullable=False)
    report_data = Column(JSON, nullable=False)

    exam = relationship("Exam")
    school = relationship("School")
    created_by = relationship("User")
