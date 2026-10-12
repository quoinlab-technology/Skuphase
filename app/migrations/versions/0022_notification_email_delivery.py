"""Track queued notification email delivery attempts."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0022_notification_email_delivery"
down_revision: Union[str, None] = "0021_audit_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("notifications")}
    if "email_attempts" not in columns:
        op.add_column("notifications", sa.Column("email_attempts", sa.Integer(), server_default="0", nullable=False))
    if "email_run_at" not in columns:
        op.add_column("notifications", sa.Column("email_run_at", sa.DateTime(timezone=True), nullable=True))
    if "email_last_error" not in columns:
        op.add_column("notifications", sa.Column("email_last_error", sa.Text(), nullable=True))
    if "email_sent_at" not in columns:
        op.add_column("notifications", sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_notifications_email_delivery",
        "notifications",
        ["email_status", "email_run_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_email_delivery", table_name="notifications")
    op.drop_column("notifications", "email_sent_at")
    op.drop_column("notifications", "email_last_error")
    op.drop_column("notifications", "email_run_at")
    op.drop_column("notifications", "email_attempts")
