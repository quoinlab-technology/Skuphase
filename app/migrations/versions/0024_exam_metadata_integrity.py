"""Persist exam titles, curriculum focus, and authoring source."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0024_exam_metadata_integrity"
down_revision: Union[str, None] = "0023_phase_four_governance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("exams")}
    if "title" not in columns:
        op.add_column("exams", sa.Column("title", sa.String(length=180), nullable=True))
    if "term" not in columns:
        op.add_column("exams", sa.Column("term", sa.String(length=30), nullable=True))
    if "focus_topics" not in columns:
        op.add_column("exams", sa.Column("focus_topics", sa.Text(), nullable=True))
    if "custom_instructions" not in columns:
        op.add_column("exams", sa.Column("custom_instructions", sa.Text(), nullable=True))
    if "selected_weeks" not in columns:
        op.add_column("exams", sa.Column("selected_weeks", sa.JSON(), nullable=True))
    if "source_type" not in columns:
        op.add_column(
            "exams",
            sa.Column("source_type", sa.String(length=20), nullable=False, server_default="manual"),
        )

    # Backfill reliable provenance from the existing LLM accounting field.
    op.execute(
        "UPDATE exams SET source_type = CASE "
        "WHEN COALESCE(llm_call_count, 0) > 0 THEN 'ai' ELSE 'manual' END"
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("exams")}
    for name in ("source_type", "selected_weeks", "custom_instructions", "focus_topics", "term", "title"):
        if name in columns:
            op.drop_column("exams", name)
