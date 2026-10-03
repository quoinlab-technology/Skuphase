"""Schemas for teacher lesson planning."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LessonPlanCreate(BaseModel):
    curriculum_id: UUID
    scheme_id: UUID
    title: str = Field(..., min_length=3, max_length=255)
    learning_objectives: list[str] = Field(default_factory=list, max_length=30)
    activities: list[str] = Field(default_factory=list, max_length=30)
    resources: list[str] = Field(default_factory=list, max_length=30)
    assessment_notes: str | None = Field(None, max_length=5000)

    @field_validator("learning_objectives", "activities", "resources")
    @classmethod
    def clean_items(cls, values):
        return [str(value).strip() for value in values if str(value).strip()]


class LessonPlanUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    learning_objectives: list[str] | None = Field(None, max_length=30)
    activities: list[str] | None = Field(None, max_length=30)
    resources: list[str] | None = Field(None, max_length=30)
    assessment_notes: str | None = Field(None, max_length=5000)
    status: str | None = Field(None, pattern="^(draft|submitted|approved|returned)$")


class LessonPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    school_id: UUID
    created_by_user_id: UUID | None = None
    curriculum_id: UUID
    scheme_id: UUID
    term: str
    week_number: int
    title: str
    learning_objectives: list[str] = Field(default_factory=list)
    activities: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    assessment_notes: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    ai_lesson_note: str | None = None
    hod_feedback: str | None = None
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None


class WeeklyExerciseCreate(BaseModel):
    lesson_plan_id: UUID
    title: str = Field(..., min_length=3, max_length=255)
    instructions: str | None = Field(None, max_length=2000)
    questions: list[dict] = Field(..., min_length=1, max_length=100)


class WeeklyExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    school_id: UUID
    lesson_plan_id: UUID
    created_by_user_id: UUID | None = None
    title: str
    instructions: str | None = None
    questions: list[dict] = Field(default_factory=list)
    status: str
    created_at: datetime
    updated_at: datetime


class CoverageUpdate(BaseModel):
    status: str = Field(..., pattern="^(planned|in_progress|completed|verified)$")
    teacher_notes: str | None = Field(None, max_length=5000)


class CoverageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    school_id: UUID
    curriculum_id: UUID
    scheme_id: UUID
    teacher_id: UUID | None = None
    status: str
    teacher_notes: str | None = None
    completed_at: datetime | None = None
    verified_by_user_id: UUID | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LessonNoteRequest(BaseModel):
    lesson_plan_id: UUID
    additional_guidance: str | None = Field(None, max_length=2000)
