"""Add question refinements table.

Revision ID: 0002_add_question_refinements
Revises: 0001_initial_schema
Create Date: 2026-02-28 15:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_add_question_refinements"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_refinements",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refined_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("refined_text", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["refined_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_question_refinements_question_id",
        "question_refinements",
        ["question_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_question_refinements_question_id", table_name="question_refinements")
    op.drop_table("question_refinements")
