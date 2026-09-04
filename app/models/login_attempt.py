"""Login throttling attempts (DB-backed, shared across workers/instances)."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class LoginAttempt(Base):
    """One login attempt (successful or not) for throttling.

    5+ failures for the same (email, ip) within the rolling window locks that
    pair out. Kept in Postgres so throttling survives restarts and is shared
    across uvicorn workers and app instances.
    """

    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email_lower = Column(String(255), nullable=False)
    ip = Column(String(64), nullable=False, default="unknown")
    attempted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_login_attempts_lookup", "email_lower", "ip", "attempted_at"),
    )
