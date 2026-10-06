"""Pydantic schemas for Curriculum and Scheme of Work."""

import uuid
from typing import List, Optional
import json
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchemeOfWorkResponse(BaseModel):
    """Weekly scheme of work details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    curriculum_id: uuid.UUID
    term: str
    week_number: int
    topic: str
    subtopics: List[str] = Field(default_factory=list)
    raw_content: Optional[str] = None
    is_exam_or_break: bool = False

    # School-local authoring state, populated by the school-aware endpoints.
    # Defaults keep the shared public read endpoint backward compatible.
    has_override: bool = False
    is_archived: bool = False
    seeded_topic: Optional[str] = None
    teacher_notes: Optional[str] = None
    resources: List[str] = Field(default_factory=list)

    @field_validator("subtopics", mode="before")
    @classmethod
    def _parse_subtopics(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [v]
            except Exception:
                return [v] if v.strip() else []
        return v or []


class CurriculumSubjectResponse(BaseModel):
    """Subject available in a class curriculum."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    board: str
    class_level: str
    subject_name: str
    category: Optional[str] = None


class ClassListResponse(BaseModel):
    """List of available classes."""
    classes: List[str]


class BoardListResponse(BaseModel):
    """Educational boards represented in the curriculum database."""

    boards: List[str]


class SubjectListResponse(BaseModel):
    """List of available subjects for a class."""
    class_level: str
    subjects: List[CurriculumSubjectResponse]


class TermListResponse(BaseModel):
    """List of academic terms."""
    terms: List[str]


class WeekListResponse(BaseModel):
    """List of weeks for selected subject, class, and term."""
    class_level: str
    subject_name: str
    term: str
    weeks: List[SchemeOfWorkResponse]


class CurriculumSearchResult(BaseModel):
    """Curriculum search hit."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    board: str
    class_level: str
    subject_name: str


class SchemeOfWorkOverrideRequest(BaseModel):
    """School corrections to a seeded scheme week.

    ``topic``/``subtopics`` are admin-only (they amend shared curriculum text);
    ``teacher_notes``/``resources`` may be written by teachers as well. Sending
    ``None`` for a correction field restores the seeded value.
    """

    topic: Optional[str] = Field(default=None, max_length=255)
    subtopics: Optional[List[str]] = None
    teacher_notes: Optional[str] = None
    resources: Optional[List[str]] = None
    is_archived: Optional[bool] = None

    @field_validator("topic")
    @classmethod
    def _topic_not_blank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Topic cannot be blank. Clear the field to keep the seeded text.")
        return v.strip() if v else v

    @field_validator("subtopics", "resources")
    @classmethod
    def _clean_lines(cls, v):
        if v is None:
            return None
        return [str(item).strip() for item in v if str(item).strip()]


class SchemeOfWorkDetailResponse(BaseModel):
    """A seeded scheme week merged with the caller's school override."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    curriculum_id: uuid.UUID
    term: str
    week_number: int
    topic: str
    subtopics: List[str] = Field(default_factory=list)
    raw_content: Optional[str] = None
    is_exam_or_break: bool = False

    # Seeded (shared) values, so the UI can show what was corrected.
    seeded_topic: str
    seeded_subtopics: List[str] = Field(default_factory=list)

    # School overlay state.
    has_override: bool = False
    is_archived: bool = False
    teacher_notes: Optional[str] = None
    resources: List[str] = Field(default_factory=list)
    updated_by_user_id: Optional[uuid.UUID] = None

    # Permission hints for the UI.
    can_edit_canonical: bool = False
    can_edit_local: bool = False


class SchemeOfWorkOverrideListResponse(BaseModel):
    """All overrides the school has authored, for the authoring index."""

    overrides: List[SchemeOfWorkDetailResponse]
    total: int

    term: str
    week_number: int
    topic: str
    subtopics: List[str] = Field(default_factory=list)
