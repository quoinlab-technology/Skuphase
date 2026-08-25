"""Add curriculum and auth enhancement tables and columns.

Revision ID: 0010_curriculum_and_auth_enhancements
Revises: 0009_embedding_upgrade_1024
Create Date: 2026-08-24 10:00:00
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_curriculum_and_auth_enhancements"
down_revision: Union[str, None] = "0009_embedding_upgrade_1024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_personal_workspace to schools
    op.add_column(
        "schools",
        sa.Column("is_personal_workspace", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # 2. Add auth and invitation columns to users
    op.add_column(
        "users",
        sa.Column("account_type", sa.String(length=30), server_default="school_staff", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("verification_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("verification_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("reset_password_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("reset_password_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("invitation_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_verification_token", "users", ["verification_token"])
    op.create_index("ix_users_reset_password_token", "users", ["reset_password_token"])

    # 3. Create curriculums table
    op.create_table(
        "curriculums",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("country", sa.String(length=10), server_default="NG", nullable=False),
        sa.Column("board", sa.String(length=50), server_default="NERDC", nullable=False),
        sa.Column("class_level", sa.String(length=50), nullable=False),
        sa.Column("subject_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_curriculums_board", "curriculums", ["board"])
    op.create_index("ix_curriculums_class_level", "curriculums", ["class_level"])
    op.create_index("ix_curriculums_subject_name", "curriculums", ["subject_name"])
    op.create_index("ix_curriculums_lookup", "curriculums", ["board", "class_level", "subject_name"], unique=True)

    # 4. Create scheme_of_works table
    op.create_table(
        "scheme_of_works",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("curriculum_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("curriculums.id", ondelete="CASCADE"), nullable=False),
        sa.Column("term", sa.String(length=20), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("subtopics", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("is_exam_or_break", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scheme_of_works_curriculum_id", "scheme_of_works", ["curriculum_id"])
    op.create_index("ix_scheme_of_works_term", "scheme_of_works", ["term"])
    op.create_index("ix_scheme_of_works_week_number", "scheme_of_works", ["week_number"])
    op.create_index("ix_scheme_lookup", "scheme_of_works", ["curriculum_id", "term", "week_number"], unique=True)


def downgrade() -> None:
    op.drop_table("scheme_of_works")
    op.drop_table("curriculums")
    op.drop_index("ix_users_reset_password_token", table_name="users")
    op.drop_index("ix_users_verification_token", table_name="users")
    op.drop_column("users", "invitation_accepted_at")
    op.drop_column("users", "invited_by_id")
    op.drop_column("users", "reset_password_token_expires_at")
    op.drop_column("users", "reset_password_token")
    op.drop_column("users", "verification_token_expires_at")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "account_type")
    op.drop_column("schools", "is_personal_workspace")
