"""Usage tracking and logging models."""

from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class UsageLog(BaseModel):
    """Log of user actions for billing, rate limiting, and analytics."""
    
    __tablename__ = "usage_logs"
    
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    action = Column(String(50), nullable=False)  # exam_generation, refinement, export, document_upload
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)  # Estimated LLM cost in USD
    provider = Column(String(50))  # grok, openrouter
    
    log_metadata = Column(Text)  # JSON metadata
    
    # Relationships
    school = relationship("School", back_populates="usage_logs")
    user = relationship("User", back_populates="usage_logs")
    
    def __repr__(self) -> str:
        return f"<UsageLog(school_id={self.school_id}, action={self.action})>"
