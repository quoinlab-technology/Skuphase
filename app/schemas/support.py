"""Schemas for school feedback and durable notifications."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    category: str = Field(..., min_length=2, max_length=40)
    severity: str = Field(default="normal", pattern="^(critical|high|normal|low)$")
    subject: str = Field(..., min_length=3, max_length=180)
    description: str = Field(..., min_length=5, max_length=10000)
    page_url: str | None = Field(default=None, max_length=500)
    context: dict[str, Any] = Field(default_factory=dict)


class FeedbackStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(new|acknowledged|investigating|waiting_on_school|resolved|closed)$")
    resolution_note: str | None = Field(default=None, max_length=5000)


class NotificationResponse(BaseModel):
    notification_id: UUID
    kind: str
    title: str
    body: str
    severity: str
    target_url: str | None = None
    is_read: bool
    created_at: datetime
