"""Support and in-app notification persistence models."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class Notification(BaseModel):
    """Durable user notification; a toast is only an optional presentation."""

    __tablename__ = "notifications"

    recipient_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=True)
    kind = Column(String(60), nullable=False)
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="info")
    target_url = Column(String(500), nullable=True)
    payload = Column(JSON, nullable=False, default=dict, server_default="{}")
    read_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    email_status = Column(String(20), nullable=False, default="not_requested", server_default="'not_requested'")

    __table_args__ = (
        Index("ix_notifications_recipient_read", "recipient_user_id", "read_at", "created_at"),
    )


class FeedbackTicket(BaseModel):
    """School-user feedback or support case visible to platform staff."""

    __tablename__ = "feedback_tickets"

    requester_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=True)
    category = Column(String(40), nullable=False)
    severity = Column(String(20), nullable=False, default="normal")
    status = Column(String(30), nullable=False, default="new", index=True)
    subject = Column(String(180), nullable=False)
    description = Column(Text, nullable=False)
    page_url = Column(String(500), nullable=True)
    context = Column(JSON, nullable=False, default=dict, server_default="{}")
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_feedback_tickets_school_status", "school_id", "status", "created_at"),
    )
