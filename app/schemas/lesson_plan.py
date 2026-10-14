"""Schemas for teacher lesson planning."""
import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    ai_lesson_note: str | None = Field(None, max_length=20000)
    hod_feedback: str | None = Field(None, max_length=5000)
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


class WeeklyExerciseQuestion(BaseModel):
    """Normalized worksheet item; accepts legacy ``text`` and mark suffixes."""

    question_number: int | None = Field(None, ge=1, le=100)
    type: str = Field("short_answer", pattern="^(short_answer|mcq)$", max_length=40)
    question_text: str = Field(..., min_length=1, max_length=3000)
    marks: int = Field(1, ge=1, le=100)
    answer_lines: int = Field(2, ge=0, le=12)
    answer_options: list[str] | None = Field(None, max_length=10)
    answer_key: str | None = Field(None, max_length=3000)
    explanation: str | None = Field(None, max_length=5000)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_question(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if not data.get("question_text") and data.get("text"):
            data["question_text"] = data.pop("text")
        text = str(data.get("question_text") or "").strip()
        mark_suffix = re.search(r"\s*\[(\d+)\s+marks?\]\s*$", text, re.IGNORECASE)
        if mark_suffix:
            data["marks"] = int(mark_suffix.group(1))
            data["question_text"] = text[:mark_suffix.start()].strip()
        return data

    @model_validator(mode="after")
    def validate_multiple_choice(self):
        if self.type == "mcq" and len([item for item in (self.answer_options or []) if item.strip()]) < 2:
            raise ValueError("Multiple-choice questions require at least two answer options")
        return self


class WeeklyExerciseCreate(BaseModel):
    lesson_plan_id: UUID
    title: str = Field(..., min_length=3, max_length=255)
    instructions: str | None = Field(None, max_length=2000)
    questions: list[WeeklyExerciseQuestion] = Field(..., min_length=1, max_length=100)


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
