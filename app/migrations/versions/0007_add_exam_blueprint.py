"""Persist the generation blueprint alongside each exam.

Revision ID: 0007_add_exam_blueprint
Revises: 0006_add_bank_usage_count
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_add_exam_blueprint"
down_revision: Union[str, None] = "0006_add_bank_usage_count"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {column["name"] for column in sa.inspect(conn).get_columns("exams")}
    if "blueprint" not in columns:
        op.add_column("exams", sa.Column("blueprint", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("exams", "blueprint")
