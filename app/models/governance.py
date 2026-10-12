"""Private company governance records for incident and safe support operations."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class IncidentRecord(BaseModel):
    """A tracked service or security incident with an explicit lifecycle."""

    __tablename__ = "platform_incidents"

    title = Column(String(180), nullable=False)
    service = Column(String(60), nullable=False)
    severity = Column(String(20), nullable=False, default="minor")
    status = Column(String(30), nullable=False, default="open", index=True)
    summary = Column(Text, nullable=False)
    impact = Column(Text, nullable=True)
    public_message = Column(Text, nullable=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict, server_default="{}")

    __table_args__ = (Index("ix_platform_incidents_severity_status", "severity", "status", "created_at"),)


class SupportAccessGrant(BaseModel):
    """Time-limited, explicit support access approval (no silent impersonation)."""

    __tablename__ = "platform_support_access_grants"

    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    operator_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    granted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true", index=True)

    __table_args__ = (Index("ix_support_access_school_active", "school_id", "is_active", "expires_at"),)


class CurriculumVersion(BaseModel):
    """Auditable curriculum import/version metadata and validation state."""

    __tablename__ = "platform_curriculum_versions"

    version = Column(String(80), nullable=False, unique=True)
    board = Column(String(50), nullable=False, default="NERDC")
    source_document = Column(String(500), nullable=True)
    source_hash = Column(String(128), nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    notes = Column(Text, nullable=True)
    manifest = Column(JSON, nullable=False, default=dict, server_default="{}")
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_curriculum_versions_board_status", "board", "status", "created_at"),)
