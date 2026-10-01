"""Add tenant partner API keys."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0009_add_api_keys"
down_revision: Union[str, None] = "0008_add_document_style"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.UUID(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False, unique=True),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("quota_monthly", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_keys_school_id", "api_keys", ["school_id"])
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"], unique=True)

def downgrade() -> None:
    op.drop_table("api_keys")
