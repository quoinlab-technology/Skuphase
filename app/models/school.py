"""School and tenant models."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime

from app.models.base import BaseModel


class School(BaseModel):
    """School entity - primary tenant / workspace."""
    
    __tablename__ = "schools"
    
    name = Column(String(100), nullable=False, unique=True)
    contact_email = Column(String(255), nullable=False, unique=True)
    contact_phone = Column(String(20))
    address = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    is_personal_workspace = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="school", cascade="all, delete-orphan")
    subscriptions = relationship("SchoolSubscription", back_populates="school", cascade="all, delete-orphan")
    settings = relationship("SchoolSettings", back_populates="school", uselist=False, cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="school", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="school", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<School(id={self.id}, name={self.name})>"


class SchoolSettings(BaseModel):
    """School settings for exam generation, branding, and LLM provider preferences."""
    
    __tablename__ = "school_settings"
    
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), primary_key=True)
    
    # Branding
    logo_url = Column(String(500))
    primary_color = Column(String(7))  # Hex color
    secondary_color = Column(String(7))
    
    # LLM Provider preferences
    primary_llm_provider = Column(String(50), default="grok")  # grok, openrouter
    fallback_llm_provider = Column(String(50), default="openrouter")
    
    # Exam settings
    default_total_marks = Column(String(3), default="100")
    exam_format = Column(String(50), default="nigerian")  # Nigerian WAEC format
    
    # Relationships
    school = relationship("School", back_populates="settings")
    
    def __repr__(self) -> str:
        return f"<SchoolSettings(school_id={self.school_id})>"
