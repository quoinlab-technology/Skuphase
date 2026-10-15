"""Add configurable workspace document identity."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0026_document_branding"
down_revision: Union[str, None] = "0025_workspace_curriculum_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("school_settings")}
    if "document_display_name" not in columns:
        op.add_column("school_settings", sa.Column("document_display_name", sa.String(length=150), nullable=True))
    if "personal_document_branding_enabled" not in columns:
        op.add_column(
            "school_settings",
            sa.Column("personal_document_branding_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("school_settings")}
    if "personal_document_branding_enabled" in columns:
        op.drop_column("school_settings", "personal_document_branding_enabled")
    if "document_display_name" in columns:
        op.drop_column("school_settings", "document_display_name")
