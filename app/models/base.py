"""Base model with common fields."""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class BaseModel(Base):
    """Base model with common fields for all entities."""
    
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
