"""Add school-scoped scheme-of-work overrides for curriculum authoring.

Seeded NERDC curriculum rows are shared national reference data with no
school_id. Allowing an edit in place would let one school silently change the
curriculum every other tenant sees. This table stores a per-school overlay
instead, so schools can repair imported text and attach local notes without
mutating shared data.

Revision ID: 0015_curriculum_authoring
Revises: 0014_fix_curriculum_jsonb
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_curriculum_authoring"
down_revision: Union[str, None] = "0014_fix_curriculum_jsonb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheme_of_work_overrides",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "school_id",
            sa.UUID(),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scheme_of_work_id",
            sa.UUID(),
            sa.ForeignKey("scheme_of_works.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(255), nullable=True),
        sa.Column("subtopics", postgresql.JSONB(), nullable=True),
        sa.Column("teacher_notes", sa.Text(), nullable=True),
        sa.Column("resources", postgresql.JSONB(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_scheme_of_work_overrides_school_id",
        "scheme_of_work_overrides",
        ["school_id"],
    )
    op.create_index(
        "ix_scheme_of_work_overrides_scheme_of_work_id",
        "scheme_of_work_overrides",
        ["scheme_of_work_id"],
    )
    op.create_index(
        "uq_scheme_override_school_week",
        "scheme_of_work_overrides",
        ["school_id", "scheme_of_work_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("scheme_of_work_overrides")
