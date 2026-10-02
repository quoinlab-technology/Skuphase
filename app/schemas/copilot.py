from typing import Literal, Optional
from pydantic import BaseModel, Field

CopilotAction = Literal["options", "marking_guide", "rewrite", "diagram_prompt"]

class CopilotRequest(BaseModel):
    action: CopilotAction
    subject: str = Field(..., min_length=1, max_length=100)
    grade_level: str = Field(..., min_length=1, max_length=50)
    question: str = Field(..., min_length=3, max_length=5000)
    marks: int = Field(default=1, ge=1, le=100)
    options: Optional[list[str]] = Field(None, max_length=10)
    topic: Optional[str] = Field(None, max_length=200)

class CopilotResponse(BaseModel):
    action: CopilotAction
    content: str
    options: list[str] = Field(default_factory=list)
    marking_points: list[str] = Field(default_factory=list)
    diagram_prompt: Optional[str] = None
