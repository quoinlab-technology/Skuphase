"""Auth hardening, curation queue, data-driven class ordering.

- users.token_generation: refresh-token revocation counter (audit F-06)
- login_attempts: DB-backed login throttling shared across workers (F-07)
- question_bank_items.review_status: owner curation queue (F-12 / D-NEW-1)
- curriculums.level_order: data-driven class ordering so JSS/SSS is a
  data drop, not a code change (D-NEW-2)

Revision ID: 0002_auth_curation_ordering
Revises: 0001_baseline_squash
Create Date: 2026-08-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_auth_curation_ordering'
down_revision: Union[str, None] = '0001_baseline_squash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEVEL_ORDER_SQL = """
UPDATE curriculums SET level_order = CASE class_level
    WHEN 'Pre-Nursery' THEN 1
    WHEN 'Nursery 1' THEN 2
    WHEN 'Nursery 2' THEN 3
    WHEN 'Nursery 3' THEN 4
    WHEN 'Primary 1' THEN 5
    WHEN 'Primary 2' THEN 6
    WHEN 'Primary 3' THEN 7
    WHEN 'Primary 4' THEN 8
    WHEN 'Primary 5' THEN 9
    WHEN 'Primary 6' THEN 10
    WHEN 'JSS 1' THEN 11
    WHEN 'JSS 2' THEN 12
    WHEN 'JSS 3' THEN 13
    WHEN 'SSS 1' THEN 14
    WHEN 'SSS 2' THEN 15
    WHEN 'SSS 3' THEN 16
    ELSE 99 END
"""


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('token_generation', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'question_bank_items',
        sa.Column('review_status', sa.String(length=20), nullable=False, server_default='approved'),
    )
    op.add_column('curriculums', sa.Column('level_order', sa.Integer(), nullable=True))
    op.execute(_LEVEL_ORDER_SQL)
    op.create_index(
        'ix_curriculums_level_order', 'curriculums', ['level_order'], unique=False
    )
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email_lower', sa.String(length=255), nullable=False),
        sa.Column('ip', sa.String(length=64), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_login_attempts_lookup',
        'login_attempts',
        ['email_lower', 'ip', 'attempted_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_login_attempts_lookup', table_name='login_attempts')
    op.drop_table('login_attempts')
    op.drop_index('ix_curriculums_level_order', table_name='curriculums')
    op.drop_column('curriculums', 'level_order')
    op.drop_column('question_bank_items', 'review_status')
    op.drop_column('users', 'token_generation')
