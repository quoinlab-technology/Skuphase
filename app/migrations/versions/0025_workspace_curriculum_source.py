"""Set one default curriculum source for each workspace."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0025_workspace_curriculum_source"
down_revision: Union[str, None] = "0024_exam_metadata_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("school_settings")}
    if "curriculum_board" not in columns:
        op.add_column(
            "school_settings",
            sa.Column(
                "curriculum_board",
                sa.String(length=50),
                nullable=False,
                server_default="NERDC",
            ),
        )

    exam_columns = {column["name"] for column in inspector.get_columns("exams")}
    if "curriculum_board" not in exam_columns:
        op.add_column("exams", sa.Column("curriculum_board", sa.String(length=50), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("school_settings")}
    if "curriculum_board" in columns:
        op.drop_column("school_settings", "curriculum_board")
    exam_columns = {column["name"] for column in inspector.get_columns("exams")}
    if "curriculum_board" in exam_columns:
        op.drop_column("exams", "curriculum_board")
