"""Pydantic schemas for Curriculum and Scheme of Work."""

import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class SchemeOfWorkResponse(BaseModel):
    """Weekly scheme of work details."""
    id: uuid.UUID
    curriculum_id: uuid.UUID
    term: str
    week_number: int
    topic: str
    subtopics: List[str] = Field(default_factory=list)
    raw_content: Optional[str] = None
    is_exam_or_break: bool = False

    class Config:
        from_attributes = True


class CurriculumSubjectResponse(BaseModel):
    """Subject available in a class curriculum."""
    id: uuid.UUID
    board: str
    class_level: str
    subject_name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True


class ClassListResponse(BaseModel):
    """List of available classes."""
    classes: List[str]


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


class CurriculumSearchQuery(BaseModel):
    """Search query for curriculum topics."""
    query: str
    class_level: Optional[str] = None
    subject_name: Optional[str] = None
    limit: int = 20


class CurriculumSearchResult(BaseModel):
    """Curriculum search hit."""
    id: uuid.UUID
    board: str
    class_level: str
    subject_name: str
    term: str
    week_number: int
    topic: str
    subtopics: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
