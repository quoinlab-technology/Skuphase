"""User model."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class User(BaseModel):
    """School staff or independent teacher user."""
    
    __tablename__ = "users"
    
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255))  # BCrypt hash 
    full_name = Column(String(255), nullable=False)
    
    role = Column(String(20), nullable=False)  # teacher, school_admin, parent, auditor
    account_type = Column(String(30), default="school_staff", nullable=False)  # school_staff, individual_teacher, superadmin
    
    # OAuth
    google_id = Column(String(255), unique=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Email verification
    verification_token = Column(String(255), nullable=True, index=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password Reset
    reset_password_token = Column(String(255), nullable=True, index=True)
    reset_password_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Invitation tracking
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invitation_accepted_at = Column(DateTime(timezone=True), nullable=True)

    # JWTs issued before this instant are rejected (set on credential changes).
    token_valid_after = Column(DateTime(timezone=True), nullable=True)

    # Refresh-token generation counter; incremented on logout so all
    # outstanding refresh tokens become invalid instantly (audit F-06).
    token_generation = Column(Integer, nullable=False, default=1)

    last_login = Column(DateTime(timezone=True))

    # Per-user notification preferences (audit2 Phase 2). JSON dict keyed by
    # NotificationPrefs field names; None falls back to schema defaults.
    notification_prefs = Column(JSON, nullable=True)

    # Relationships
    school = relationship("School", back_populates="users")
    exams = relationship("Exam", back_populates="created_by")
    usage_logs = relationship("UsageLog", back_populates="user")
    audit_comments = relationship(
        "ExamAuditComment",
        foreign_keys="ExamAuditComment.author_user_id",
        back_populates="author",
    )
    resolved_audit_comments = relationship(
        "ExamAuditComment",
        foreign_keys="ExamAuditComment.resolved_by_user_id",
        back_populates="resolved_by",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, school_id={self.school_id})>"
