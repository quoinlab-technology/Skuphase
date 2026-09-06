"""Add per-user notification preferences (audit2 Phase 2).

- users.notification_prefs: nullable JSON dict keyed by NotificationPrefs
  field names (e.g. exam_generation_completed).  NULL falls back to the
  schema defaults so existing rows need no backfill.

Revision ID: 0004_user_notification_prefs
Revises: 0003_exam_passages_language
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_user_notification_prefs'
down_revision: Union[str, None] = '0003_exam_passages_language'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('notification_prefs', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'notification_prefs')