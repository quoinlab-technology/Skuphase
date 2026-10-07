"""Preserve full curriculum topic text.

Revision ID: 0016_widen_curriculum_topic
Revises: 0015_curriculum_authoring
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_widen_curriculum_topic"
down_revision: Union[str, None] = "0015_curriculum_authoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "scheme_of_works",
        "topic",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Existing values longer than 255 characters cannot be safely restored to
    # varchar without an explicit data-loss decision by the operator.
    op.alter_column(
        "scheme_of_works",
        "topic",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
