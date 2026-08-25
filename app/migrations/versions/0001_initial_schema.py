"""Initial schema baseline.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-28 14:15:00
"""

import logging
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

logger = logging.getLogger("alembic.migration")

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Try to enable pgvector extension.
    # Uses a SAVEPOINT so a missing extension does NOT abort the whole migration.
    # RAG/vector-search features require pgvector in production.
    # Install guide: https://github.com/pgvector/pgvector#installation
    try:
        conn.execute(text("SAVEPOINT sp_pgvector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("RELEASE SAVEPOINT sp_pgvector"))
        logger.info("pgvector extension enabled successfully.")
    except Exception as exc:
        conn.execute(text("ROLLBACK TO SAVEPOINT sp_pgvector"))
        logger.warning(
            "pgvector extension NOT installed on PostgreSQL server. "
            "Vector similarity search (RAG) will be unavailable until you install it. "
            "See https://github.com/pgvector/pgvector for installation instructions. "
            "(Error: %s)",
            exc,
        )

    # Import lazily to ensure models are loaded in Alembic context.
    from app.core.database import Base
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=conn)


def downgrade() -> None:
    from app.core.database import Base
    from app import models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

