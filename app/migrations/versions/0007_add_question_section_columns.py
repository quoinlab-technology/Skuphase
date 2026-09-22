"""Add section_number and section_name to questions.

Revision ID: 0007_add_qn_section_cols
Revises: 0006_add_bank_usage_count
Create Date: 2026-09-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007_add_qn_section_cols'
down_revision: Union[str, None] = '0006_add_bank_usage_count'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c['name'] for c in insp.get_columns('questions')]
    if 'section_number' not in columns:
        op.add_column(
            'questions',
            sa.Column('section_number', sa.Integer(), nullable=False, server_default='1')
        )
    if 'section_name' not in columns:
        op.add_column(
            'questions',
            sa.Column('section_name', sa.String(length=50), nullable=True)
        )


def downgrade() -> None:
    op.drop_column('questions', 'section_name')
    op.drop_column('questions', 'section_number')
