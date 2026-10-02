"""Persist structured Faststrap blocks on questions.

Revision ID: 0011_add_question_content_blocks
Revises: 0010_add_exam_blueprint
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_add_question_content_blocks"
down_revision: Union[str, None] = "0010_add_exam_blueprint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {column["name"] for column in sa.inspect(conn).get_columns("questions")}
    if "content_blocks" not in columns:
        op.add_column("questions", sa.Column("content_blocks", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "content_blocks")
