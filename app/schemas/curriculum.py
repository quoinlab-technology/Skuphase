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
    term: str
    week_number: int
    topic: str
    subtopics: List[str] = Field(default_factory=list)
