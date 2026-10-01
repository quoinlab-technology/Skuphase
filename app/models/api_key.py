"""Tenant-scoped partner API credentials."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ApiKey(BaseModel):
    __tablename__ = "api_keys"
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(16), nullable=False, unique=True, index=True)
    key_hash = Column(String(64), nullable=False, unique=True)
    scopes = Column(JSON, nullable=False, default=list, server_default="[]")
    quota_monthly = Column(Integer, nullable=False, default=1000, server_default="1000")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    school = relationship("School")
