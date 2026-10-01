"""Structured assessment document and blueprint contracts."""
from __future__ import annotations
from typing import Literal, Union
from pydantic import BaseModel, Field, ConfigDict

BlockType = Literal["text", "math", "svg", "table"]

class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str = Field(..., max_length=10000)

class MathBlock(BaseModel):
    type: Literal["math"] = "math"
    latex: str = Field(..., max_length=4000)
    display: bool = True

class SvgBlock(BaseModel):
    type: Literal["svg"] = "svg"
    svg: str = Field(..., max_length=200000)
    alt: str = Field(default="Assessment diagram", max_length=500)

class TableBlock(BaseModel):
    type: Literal["table"] = "table"
    rows: list[list[str]] = Field(..., min_length=1, max_length=100)
    headers: bool = True

DocumentBlock = Union[TextBlock, MathBlock, SvgBlock, TableBlock]

class QuestionDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blocks: list[DocumentBlock] = Field(..., min_length=1, max_length=100)

class BlueprintSection(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    bloom: Literal["knowledge", "understanding", "application", "analysis", "synthesis", "evaluation"]
    questions: int = Field(..., ge=1, le=100)
    marks: int = Field(..., ge=1, le=1000)

class BlueprintRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)
    grade_level: str = Field(..., min_length=1, max_length=50)
    total_questions: int = Field(..., ge=1, le=200)
    total_marks: int = Field(..., ge=1, le=1000)
    sections: list[BlueprintSection] = Field(..., min_length=1, max_length=100)

class BlueprintResponse(BaseModel):
    subject: str
    grade_level: str
    total_questions: int
    total_marks: int
    sections: list[BlueprintSection]
    topic_totals: dict[str, int]
    bloom_totals: dict[str, int]
    warnings: list[str] = Field(default_factory=list)
