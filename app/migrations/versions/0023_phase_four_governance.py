"""Add Phase 4 governance, support-access, and curriculum-version records."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0023_phase_four_governance"
down_revision: Union[str, None] = "0022_notification_email_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "platform_incidents" not in tables:
        op.create_table(
            "platform_incidents",
            sa.Column("id", _uuid(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("service", sa.String(60), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="minor"),
            sa.Column("status", sa.String(30), nullable=False, server_default="open"),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("impact", sa.Text()),
            sa.Column("public_message", sa.Text()),
            sa.Column("owner_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("created_by_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
            sa.Column("resolved_at", sa.DateTime(timezone=True)),
            sa.Column("resolution", sa.Text()),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        )
        op.create_index("ix_platform_incidents_severity_status", "platform_incidents", ["severity", "status", "created_at"])
    if "platform_support_access_grants" not in tables:
        op.create_table(
            "platform_support_access_grants",
            sa.Column("id", _uuid(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("school_id", _uuid(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
            sa.Column("operator_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("granted_by_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        )
        op.create_index("ix_support_access_school_active", "platform_support_access_grants", ["school_id", "is_active", "expires_at"])
    if "platform_curriculum_versions" not in tables:
        op.create_table(
            "platform_curriculum_versions",
            sa.Column("id", _uuid(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("version", sa.String(80), nullable=False, unique=True),
            sa.Column("board", sa.String(50), nullable=False, server_default="NERDC"),
            sa.Column("source_document", sa.String(500)),
            sa.Column("source_hash", sa.String(128)),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("notes", sa.Text()),
            sa.Column("manifest", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_by_user_id", _uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("published_at", sa.DateTime(timezone=True)),
            sa.Column("rolled_back_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_curriculum_versions_board_status", "platform_curriculum_versions", ["board", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_curriculum_versions_board_status", table_name="platform_curriculum_versions")
    op.drop_table("platform_curriculum_versions")
    op.drop_index("ix_support_access_school_active", table_name="platform_support_access_grants")
    op.drop_table("platform_support_access_grants")
    op.drop_index("ix_platform_incidents_severity_status", table_name="platform_incidents")
    op.drop_table("platform_incidents")
