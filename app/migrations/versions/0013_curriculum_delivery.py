"""Add weekly exercises, syllabus coverage, and lesson-note workflow.

Revision ID: 0013_curriculum_delivery
Revises: 0012_add_lesson_plans
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0013_curriculum_delivery"
down_revision: Union[str, None] = "0012_add_lesson_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lesson_plans", sa.Column("ai_lesson_note", sa.Text()))
    op.add_column("lesson_plans", sa.Column("hod_feedback", sa.Text()))
    op.add_column("lesson_plans", sa.Column("approved_by_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.add_column("lesson_plans", sa.Column("approved_at", sa.DateTime(timezone=True)))
    op.create_table(
        "weekly_exercises",
        sa.Column("id", sa.UUID(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.UUID(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_plan_id", sa.UUID(), sa.ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("instructions", sa.Text()),
        sa.Column("questions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
    )
    op.create_table(
        "syllabus_coverage",
        sa.Column("id", sa.UUID(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.UUID(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curriculum_id", sa.UUID(), sa.ForeignKey("curriculums.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_id", sa.UUID(), sa.ForeignKey("scheme_of_works.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("teacher_notes", sa.Text()), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("verified_by_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )
    for table, column in (("weekly_exercises", "school_id"), ("weekly_exercises", "lesson_plan_id"), ("syllabus_coverage", "school_id"), ("syllabus_coverage", "curriculum_id"), ("syllabus_coverage", "scheme_id")):
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("syllabus_coverage")
    op.drop_table("weekly_exercises")
    op.drop_column("lesson_plans", "approved_at")
    op.drop_column("lesson_plans", "approved_by_user_id")
    op.drop_column("lesson_plans", "hod_feedback")
    op.drop_column("lesson_plans", "ai_lesson_note")
