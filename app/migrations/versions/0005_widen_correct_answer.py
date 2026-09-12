"""Widen correct_answer to TEXT (audit fix for essay/short-answer questions).

Essays and short-answer questions store their full model answer in
``correct_answer`` (only MCQs hold a single letter "A".."D"). The column was
sized ``VARCHAR(1)`` which rejected those long answers and made generation
fail at store time after a successful LLM call. Widen to TEXT for both
``questions`` and ``question_bank_items``.

Revision ID: 0005_widen_correct_answer
Revises: 0004_user_notification_prefs
Create Date: 2026-09-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_widen_correct_answer'
down_revision: Union[str, None] = '0004_user_notification_prefs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _widen(table_name: str) -> None:
    op.alter_column(
        table_name,
        'correct_answer',
        existing_type=sa.String(length=1),
        type_=sa.Text(),
        existing_nullable=True,
    )


def upgrade() -> None:
    _widen('questions')
    _widen('question_bank_items')


def downgrade() -> None:
    # Restoring the original VARCHAR(1) is destructive to any stored essay
    # answers; it will only be invoked on a rollback to the pre-fix schema.
    op.alter_column(
        'question_bank_items',
        'correct_answer',
        existing_type=sa.Text(),
        type_=sa.String(length=1),
        existing_nullable=True,
    )
    op.alter_column(
        'questions',
        'correct_answer',
        existing_type=sa.Text(),
        type_=sa.String(length=1),
        existing_nullable=True,
    )