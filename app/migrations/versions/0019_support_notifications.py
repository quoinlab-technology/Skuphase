"""Add durable feedback tickets and in-app notifications."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0019_support_notifications"
down_revision: Union[str, None] = "0018_platform_memberships"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("kind", sa.String(length=60), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("target_url", sa.String(length=500), nullable=True),
            sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("email_status", sa.String(length=20), server_default="not_requested", nullable=False),
            sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notifications_recipient_read", "notifications", ["recipient_user_id", "read_at", "created_at"])
    if "feedback_tickets" not in tables:
        op.create_table(
            "feedback_tickets",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("requester_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("category", sa.String(length=40), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("subject", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("page_url", sa.String(length=500), nullable=True),
            sa.Column("context", postgresql.JSON(astext_type=sa.Text()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_feedback_tickets_school_status", "feedback_tickets", ["school_id", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_tickets_school_status", table_name="feedback_tickets")
    op.drop_table("feedback_tickets")
    op.drop_index("ix_notifications_recipient_read", table_name="notifications")
    op.drop_table("notifications")
