"""Append-only audit events for sensitive platform and school operations."""

from sqlalchemy import Boolean, Column, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class AuditEvent(BaseModel):
    """Sanitized record of who performed an important action and when."""

    __tablename__ = "audit_events"

    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_role = Column(String(40), nullable=True)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(60), nullable=True)
    target_id = Column(String(120), nullable=True)
    success = Column(Boolean, nullable=False, default=True, server_default="true")
    request_id = Column(String(100), nullable=True)
    ip_address = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict, server_default="{}")
    summary = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_events_created_action", "created_at", "action"),
        Index("ix_audit_events_actor_created", "actor_user_id", "created_at"),
        Index("ix_audit_events_school_created", "school_id", "created_at"),
    )
