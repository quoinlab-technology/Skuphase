"""Upgrade embeddings to BGE-M3 (1024-dim) and add HNSW vector index.

Revision ID: 0009_embedding_upgrade_1024
Revises: 0008_learning_assets_refs
Create Date: 2026-08-15 09:00:00
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

logger = logging.getLogger("alembic.migration")

revision: str = "0009_embedding_upgrade_1024"
down_revision: Union[str, None] = "0008_learning_assets_refs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check if pgvector is available on this server.
    has_vector = conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).scalar()

    if not has_vector:
        logger.warning(
            "pgvector extension not installed — skipping embedding column upgrade and HNSW index. "
            "Install pgvector and re-run this migration to enable RAG search."
        )
        return

    # Delete old 384-dim embeddings (incompatible with new 1024-dim BGE-M3 space).
    op.execute("DELETE FROM document_chunks;")

    # Re-type embedding column to 1024 dims.
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024);")

    # Create HNSW index for fast cosine similarity search (only if not already present).
    exists = conn.execute(
        text(
            "SELECT 1 FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relname = 'idx_document_chunks_embedding_hnsw'"
        )
    ).scalar()
    if not exists:
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw "
            "ON document_chunks USING hnsw (embedding vector_cosine_ops);"
        )


def downgrade() -> None:
    conn = op.get_bind()

    has_vector = conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).scalar()

    if not has_vector:
        return

    op.execute("DELETE FROM document_chunks;")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(384);")

    exists = conn.execute(
        text(
            "SELECT 1 FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relname = 'idx_document_chunks_embedding_hnsw'"
        )
    ).scalar()
    if exists:
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_embedding_hnsw;")
