"""Plan and subscription models."""

from sqlalchemy import Column, String, Numeric, Integer, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel


class Plan(BaseModel):
    """Subscription plan with limits and features."""
    
    __tablename__ = "plans"
    
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    price_ngn = Column(Numeric(10, 2), nullable=False)  # Price in Naira
    
    # Usage limits (per month)
    max_exams_per_month = Column(Integer, nullable=False)
    max_refinements_per_month = Column(Integer, nullable=False)
    max_exports_per_month = Column(Integer, nullable=False)
    max_documents_per_month = Column(Integer, nullable=False)
    max_embedding_tokens_per_month = Column(Integer, nullable=False)
    max_llm_tokens_per_month = Column(Integer, nullable=False)
    
    # Features
    allow_custom_templates = Column(Boolean, default=False)
    allow_multiple_admins = Column(Boolean, default=False)
    allow_api_access = Column(Boolean, default=False)
    
    # Relationships
    subscriptions = relationship("SchoolSubscription", back_populates="plan")
    
    def __repr__(self) -> str:
        return f"<Plan(id={self.id}, name={self.name})>"


class SchoolSubscription(BaseModel):
    """Links a school to a plan with billing information."""
    
    __tablename__ = "school_subscriptions"
    
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    
    status = Column(String(20), default="active")  # active, suspended, cancelled, trial
    start_date = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    billing_cycle = Column(String(20), default="monthly")  # monthly, yearly
    auto_renew = Column(Boolean, default=True)
    
    # Relationships
    school = relationship("School", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    
    def __repr__(self) -> str:
        return f"<SchoolSubscription(school_id={self.school_id}, plan_id={self.plan_id})>"
