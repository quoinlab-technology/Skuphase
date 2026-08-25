"""Add exam generation proposals table.

Revision ID: 0004_exam_generation_props
Revises: 0003_add_exam_audit_comments
Create Date: 2026-03-02 11:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0004_exam_generation_props"
down_revision: Union[str, None] = "0003_add_exam_audit_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_generation_proposals",
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("used_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subject", sa.String(length=100), nullable=False),
        sa.Column("grade_level", sa.String(length=50), nullable=False),
        sa.Column("document_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("desired_outcomes", sa.Text(), nullable=False),
        sa.Column("custom_instructions", sa.Text(), nullable=True),
        sa.Column("draft_questions", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["used_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_generation_proposals_school_id",
        "exam_generation_proposals",
        ["school_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_generation_proposals_status",
        "exam_generation_proposals",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_exam_generation_proposals_status", table_name="exam_generation_proposals")
    op.drop_index("ix_exam_generation_proposals_school_id", table_name="exam_generation_proposals")
    op.drop_table("exam_generation_proposals")
