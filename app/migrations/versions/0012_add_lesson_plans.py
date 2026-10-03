"""Add scheme-grounded teacher lesson plans.

Revision ID: 0012_add_lesson_plans
Revises: 0011_add_question_content_blocks
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0012_add_lesson_plans"
down_revision: Union[str, None] = "0011_add_question_content_blocks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lesson_plans",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.UUID(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("curriculum_id", sa.UUID(), sa.ForeignKey("curriculums.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_id", sa.UUID(), sa.ForeignKey("scheme_of_works.id", ondelete="CASCADE"), nullable=False),
        sa.Column("term", sa.String(20), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("learning_objectives", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("activities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("resources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("assessment_notes", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
    )
    op.create_index("ix_lesson_plans_school_id", "lesson_plans", ["school_id"])
    op.create_index("ix_lesson_plans_curriculum_id", "lesson_plans", ["curriculum_id"])
    op.create_index("ix_lesson_plans_scheme_id", "lesson_plans", ["scheme_id"])


def downgrade() -> None:
    op.drop_table("lesson_plans")
