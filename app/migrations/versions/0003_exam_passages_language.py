"""Exam passages, language of instruction, true/false support (phase 5).

- exam_passages: teacher-supplied comprehension passages, one per section.
  Questions link via questions.passage_id (SET NULL on passage delete).
- exams.language: language of instruction for generated papers (F-25).
- Questions A-E + true_false are validation-level only (no schema change).

Revision ID: 0003_exam_passages_language
Revises: 0002_auth_curation_ordering
Create Date: 2026-08-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_exam_passages_language'
down_revision: Union[str, None] = '0002_auth_curation_ordering'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exam_passages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('exam_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('section_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_exam_passages_exam_id'), 'exam_passages', ['exam_id'], unique=False
    )
    op.add_column('questions', sa.Column('passage_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_questions_passage_id',
        'questions',
        'exam_passages',
        ['passage_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_questions_passage_id', 'questions', ['passage_id'], unique=False
    )
    op.add_column(
        'exams',
        sa.Column('language', sa.String(length=20), nullable=False, server_default='English'),
    )


def downgrade() -> None:
    op.drop_column('exams', 'language')
    op.drop_index('ix_questions_passage_id', table_name='questions')
    op.drop_constraint('fk_questions_passage_id', 'questions', type_='foreignkey')
    op.drop_column('questions', 'passage_id')
    op.drop_index(op.f('ix_exam_passages_exam_id'), table_name='exam_passages')
    op.drop_table('exam_passages')