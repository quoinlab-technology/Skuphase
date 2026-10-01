"""Add admin-controlled document export style profile."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_add_document_style"
down_revision: Union[str, None] = "0007_add_qn_section_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "document_style" not in {c["name"] for c in inspector.get_columns("school_settings")}:
        op.add_column(
            "school_settings",
            sa.Column("document_style", sa.JSON(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    op.drop_column("school_settings", "document_style")
