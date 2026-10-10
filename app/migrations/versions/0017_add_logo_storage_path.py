"""Track the Supabase object key for safe school-logo replacement/removal."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_add_logo_storage_path"
down_revision: Union[str, None] = "0016_widen_curriculum_topic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("school_settings")}
    if "logo_storage_path" not in columns:
        op.add_column("school_settings", sa.Column("logo_storage_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("school_settings", "logo_storage_path")
