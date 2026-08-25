"""Durable background job model (Postgres-backed queue, no broker)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import BaseModel


class GenerationJob(BaseModel):
    """A queued exam-generation job.

    States: pending -> running -> succeeded | failed.
    Transient provider errors re-queue with exponential backoff; permanent
    validation/parse failures mark the job (and exam) failed immediately.
    """

    __tablename__ = "generation_jobs"

    exam_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_error = Column(Text, nullable=True)
    run_at = Column(DateTime(timezone=True), nullable=True)
    request_data = Column(JSONB, nullable=False)

    def __repr__(self) -> str:
        return f"<GenerationJob(id={self.id}, exam_id={self.exam_id}, status={self.status})>"
