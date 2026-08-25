"""Add exam quality snapshots table.

Revision ID: 0006_exam_quality_snaps
Revises: 0005_exam_workflow_budget
Create Date: 2026-03-02 13:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0006_exam_quality_snaps"
down_revision: Union[str, None] = "0005_exam_workflow_budget"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_quality_snapshots",
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quality_status", sa.String(length=20), nullable=False),
        sa.Column("overall_score", sa.String(length=10), nullable=False),
        sa.Column("report_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_quality_snapshots_exam_id",
        "exam_quality_snapshots",
        ["exam_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_exam_quality_snapshots_exam_id", table_name="exam_quality_snapshots")
    op.drop_table("exam_quality_snapshots")
