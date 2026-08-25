"""Add exam audit comments table.

Revision ID: 0003_add_exam_audit_comments
Revises: 0002_add_question_refinements
Create Date: 2026-03-02 10:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0003_add_exam_audit_comments"
down_revision: Union[str, None] = "0002_add_question_refinements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_audit_comments",
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("suggested_question_text", sa.Text(), nullable=True),
        sa.Column("suggested_marking_scheme", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_audit_comments_exam_id",
        "exam_audit_comments",
        ["exam_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_audit_comments_question_id",
        "exam_audit_comments",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_audit_comments_status",
        "exam_audit_comments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_exam_audit_comments_status", table_name="exam_audit_comments")
    op.drop_index("ix_exam_audit_comments_question_id", table_name="exam_audit_comments")
    op.drop_index("ix_exam_audit_comments_exam_id", table_name="exam_audit_comments")
    op.drop_table("exam_audit_comments")
