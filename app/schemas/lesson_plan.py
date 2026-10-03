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
