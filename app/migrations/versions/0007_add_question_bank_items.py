"""Add question bank items table.

Revision ID: 0007_question_bank_items
Revises: 0006_exam_quality_snaps
Create Date: 2026-03-02 14:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0007_question_bank_items"
down_revision: Union[str, None] = "0006_exam_quality_snaps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_bank_items",
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_exam_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=100), nullable=False),
        sa.Column("grade_level", sa.String(length=50), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("question_type", sa.String(length=30), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("marks", sa.Integer(), nullable=False),
        sa.Column("options", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("correct_answer", sa.String(length=1), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("marking_scheme", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("sub_parts", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("diagram_svg", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_exam_id"], ["exams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_question_id"], ["questions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_question_bank_items_school_subject_grade",
        "question_bank_items",
        ["school_id", "subject", "grade_level"],
        unique=False,
    )
    op.create_index(
        "ix_question_bank_items_topic",
        "question_bank_items",
        ["topic"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_question_bank_items_topic", table_name="question_bank_items")
    op.drop_index("ix_question_bank_items_school_subject_grade", table_name="question_bank_items")
    op.drop_table("question_bank_items")
