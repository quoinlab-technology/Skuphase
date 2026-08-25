"""Add exam workflow state and LLM call budget columns.

Revision ID: 0005_exam_workflow_budget
Revises: 0004_exam_generation_props
Create Date: 2026-03-02 12:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_exam_workflow_budget"
down_revision: Union[str, None] = "0004_exam_generation_props"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column(
            "workflow_state",
            sa.String(length=40),
            nullable=False,
            server_default="generation_requested",
        ),
    )
    op.add_column(
        "exams",
        sa.Column(
            "llm_call_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "exams",
        sa.Column(
            "llm_call_limit",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )


def downgrade() -> None:
    op.drop_column("exams", "llm_call_limit")
    op.drop_column("exams", "llm_call_count")
    op.drop_column("exams", "workflow_state")
