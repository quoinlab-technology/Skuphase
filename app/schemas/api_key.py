from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    scopes: List[str] = Field(default_factory=lambda: ["curriculum:read", "library:read"])
    quota_monthly: int = Field(default=1000, ge=1, le=1_000_000)
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    prefix: str
    scopes: List[str]
    quota_monthly: int
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str = Field(..., description="Shown once; store it securely")
