"""Schemas for learning asset APIs."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LearningAssetResponse(BaseModel):
    """Asset payload returned by API."""

    id: UUID
    school_id: UUID
    uploaded_by_user_id: Optional[UUID] = None
    source_document_id: Optional[UUID] = None
    asset_type: str
    asset_source: str
    file_name: str
    file_path: str
    mime_type: Optional[str] = None
    reference_code: str
    title: Optional[str] = None
    description: Optional[str] = None
    ocr_text: Optional[str] = None
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    topic: Optional[str] = None
    tags: Optional[List[str]] = None
    is_ai_usable: bool
    processing_status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningAssetListResponse(BaseModel):
    """Paginated list of assets."""

    total: int
    assets: List[LearningAssetResponse]


class LearningAssetUpdateRequest(BaseModel):
    """Editable fields for teacher/admin metadata updates."""

    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    subject: Optional[str] = Field(default=None, max_length=100)
    grade_level: Optional[str] = Field(default=None, max_length=50)
    topic: Optional[str] = Field(default=None, max_length=255)
    tags: Optional[List[str]] = None


class LearningAssetReviewRequest(BaseModel):
    """Admin review decision for AI usability."""

    processing_status: str = Field(
        ...,
        description="approved or rejected",
    )
    is_ai_usable: bool = Field(
        ...,
        description="Whether this asset can be used in prompt metadata injection",
    )


class LearningAssetBatchReviewRequest(BaseModel):
    """Batch review request for extracted assets."""

    asset_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Optional explicit asset ids to review",
    )
    source_document_id: Optional[UUID] = Field(
        default=None,
        description="Optional document id to review all extracted assets for that document",
    )
    processing_status: str = Field(
        ...,
        description="approved or rejected",
    )
    is_ai_usable: bool = Field(
        ...,
        description="Whether reviewed assets should be available to prompt injection",
    )
