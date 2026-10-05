"""Normalize legacy JSONB subtopics stored as JSON strings.

The original curriculum seeder serialized lists before inserting into a JSONB
column. PostgreSQL then correctly stored those values as JSON strings, which
made typed API responses and keyword search fail. New seeds pass lists
directly; this migration repairs the existing rows in place.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0014_fix_curriculum_jsonb"
down_revision: Union[str, None] = "0013_curriculum_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE scheme_of_works
        SET subtopics = (subtopics #>> '{}')::jsonb
        WHERE jsonb_typeof(subtopics) = 'string'
          AND jsonb_typeof((subtopics #>> '{}')::jsonb) = 'array'
        """
    )


def downgrade() -> None:
    # Keep repaired structured arrays intact. Re-serializing them would make
    # the application less safe and would reintroduce the original defect.
    pass
