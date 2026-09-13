"""Add usage_count to question_bank_items.

Revision ID: 0006_add_bank_usage_count
Revises: 0005_widen_correct_answer
Create Date: 2026-09-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006_add_bank_usage_count'
down_revision: Union[str, None] = '0005_widen_correct_answer'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c['name'] for c in insp.get_columns('question_bank_items')]
    if 'usage_count' not in columns:
        op.add_column(
            'question_bank_items',
            sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0')
        )


def downgrade() -> None:
    op.drop_column('question_bank_items', 'usage_count')
