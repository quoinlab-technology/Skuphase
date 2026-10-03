"""Teacher lesson-plan records grounded in the canonical scheme of work."""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class LessonPlan(BaseModel):
    __tablename__ = "lesson_plans"

    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    curriculum_id = Column(UUID(as_uuid=True), ForeignKey("curriculums.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(UUID(as_uuid=True), ForeignKey("scheme_of_works.id", ondelete="CASCADE"), nullable=False, index=True)
    term = Column(String(20), nullable=False)
    week_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    learning_objectives = Column(JSON, nullable=False, default=list)
    activities = Column(JSON, nullable=False, default=list)
    resources = Column(JSON, nullable=False, default=list)
    assessment_notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    ai_lesson_note = Column(Text, nullable=True)
    hod_feedback = Column(Text, nullable=True)
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)


class WeeklyExercise(BaseModel):
    __tablename__ = "weekly_exercises"

    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_plan_id = Column(UUID(as_uuid=True), ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    instructions = Column(Text, nullable=True)
    questions = Column(JSON, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="draft")


class SyllabusCoverage(BaseModel):
    __tablename__ = "syllabus_coverage"

    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    curriculum_id = Column(UUID(as_uuid=True), ForeignKey("curriculums.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(UUID(as_uuid=True), ForeignKey("scheme_of_works.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="planned")
    teacher_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    verified_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
