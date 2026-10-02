"""Persist the generation blueprint alongside each exam.

Revision ID: 0010_add_exam_blueprint
Revises: 0009_add_api_keys
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_add_exam_blueprint"
down_revision: Union[str, None] = "0009_add_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {column["name"] for column in sa.inspect(conn).get_columns("exams")}
    if "blueprint" not in columns:
        op.add_column("exams", sa.Column("blueprint", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("exams", "blueprint")
