"""School management schemas."""

from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SchoolSettingsUpdate(BaseModel):
    """Update school settings."""
    
    logo_url: Optional[str] = None
    colors: Optional[Dict[str, str]] = None  # e.g., {"primary": "#0066cc", "secondary": "#ff6600"}
    llm_provider: Optional[str] = Field(None, pattern="^(grok|openrouter|openai)$")
    exam_format: Optional[str] = None  # e.g., "multiple_choice", "essay", "mixed"
    document_style: Optional[Dict[str, Any]] = None


class SchoolSettingsResponse(BaseModel):
    """School settings response."""
    
    school_id: UUID
    logo_url: Optional[str] = None
    colors: Optional[Dict[str, str]] = None
    llm_provider: Optional[str] = None
    exam_format: Optional[str] = None
    document_style: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SchoolDetailResponse(BaseModel):
    """Detailed school information."""
    
    school_id: UUID
    name: str
    contact_email: str
    contact_phone: str
    address: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    settings: Optional[SchoolSettingsResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


class SchoolUpdateRequest(BaseModel):
    """Update school information."""
    
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
