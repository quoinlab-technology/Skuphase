"""Company-platform access models.

Platform membership is deliberately separate from school roles.  A member may
still have a normal school account, but platform access must be explicitly
granted and can be revoked without changing their school role.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class PlatformMembership(BaseModel):
    """Explicit access grant for the private SkuPhase operations console."""

    __tablename__ = "platform_memberships"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(30), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    granted_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_platform_memberships_user"),
        Index("ix_platform_memberships_active_role", "is_active", "role"),
    )

    def __repr__(self) -> str:
        return f"<PlatformMembership(user_id={self.user_id}, role={self.role}, active={self.is_active})>"
