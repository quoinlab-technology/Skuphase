"""Curriculum mappings + question bank corpus extension (curriculum-first).

Revision ID: 0011_curriculum_mappings_qb_ext
Revises: 0010_curriculum_and_auth_enhancements
Create Date: 2026-08-25

Changes:
1. ``curriculum_mappings`` — the only SCHOOL-scoped row in the curriculum domain.
   Records which official (shared/platform-owned) curriculum a school uses.
2. ``question_bank_items`` extension for the shared past-question corpus:
   - ``school_id`` becomes NULLABLE so platform-owned items can exist without a
     school (owner_type='platform').
   - ``owner_type`` ('platform' | 'school') distinguishes shared vs contributed.
   - ``curriculum_id`` FK ties an item to the canonical curriculum.
   - ``week_index`` aligns items to scheme_of_works.week_number for few-shot lookup.
   - ``exam_type`` / ``source_year`` provenance metadata.
   - ``embedding`` JSON column; re-typed to VECTOR(1024) when pgvector is
     available on the server (same guarded pattern as migration 0009).
"""

from typing import Sequence, Union

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

logger = logging.getLogger("alembic.migration")

revision: str = "0011_curriculum_mappings_qb_ext"
down_revision: Union[str, None] = "0010_curriculum_and_auth_enhancements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. curriculum_mappings
    # ------------------------------------------------------------------
    op.create_table(
        "curriculum_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "school_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "curriculum_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("curriculums.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "local_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "curriculum_id", name="uq_curriculum_mapping"),
    )
    op.create_index("ix_curriculum_mappings_school", "curriculum_mappings", ["school_id"])
    op.create_index("ix_curriculum_mappings_curriculum", "curriculum_mappings", ["curriculum_id"])

    # ------------------------------------------------------------------
    # 2. question_bank_items extension
    # ------------------------------------------------------------------
    op.alter_column(
        "question_bank_items",
        "school_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.add_column(
        "question_bank_items",
        sa.Column(
            "owner_type",
            sa.String(length=20),
            server_default="platform",
            nullable=False,
        ),
    )
    op.add_column(
        "question_bank_items",
        sa.Column(
            "curriculum_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("curriculums.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "question_bank_items", sa.Column("week_index", sa.Integer(), nullable=True)
    )
    op.add_column(
        "question_bank_items", sa.Column("exam_type", sa.String(length=30), nullable=True)
    )
    op.add_column(
        "question_bank_items", sa.Column("source_year", sa.Integer(), nullable=True)
    )
    # JSON initially (matches the Python model); upgraded below if pgvector is present.
    op.add_column(
        "question_bank_items",
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Lookup indexes for the SQL-first few-shot selector.
    op.create_index(
        "ix_qb_subject_class_week",
        "question_bank_items",
        ["subject", "grade_level", "week_index"],
    )
    op.create_index(
        "ix_qb_owner_active",
        "question_bank_items",
        ["owner_type", "is_active"],
    )
    op.create_index(
        "ix_qb_curriculum_week",
        "question_bank_items",
        ["curriculum_id", "week_index"],
    )

    # ------------------------------------------------------------------
    # 3. Proposal curriculum-alignment columns
    # ------------------------------------------------------------------
    op.add_column(
        "exam_generation_proposals",
        sa.Column("term", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "exam_generation_proposals",
        sa.Column(
            "selected_weeks",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------
    # 3. Optional pgvector upgrade for question embeddings (guarded)
    # ------------------------------------------------------------------
    conn = op.get_bind()
    has_vector = conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).scalar()

    if has_vector:
        logger.info("pgvector detected - upgrading question_bank_items.embedding to vector(1024)")
        op.execute(
            "ALTER TABLE question_bank_items "
            "ALTER COLUMN embedding TYPE vector(1024) USING NULL::vector;"
        )
        exists = conn.execute(
            text(
                "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname = 'idx_qb_embedding_hnsw'"
            )
        ).scalar()
        if not exists:
            op.execute(
                "CREATE INDEX IF NOT EXISTS idx_qb_embedding_hnsw "
                "ON question_bank_items USING hnsw (embedding vector_cosine_ops);"
            )
    else:
        logger.warning(
            "pgvector not installed - question_bank_items.embedding stays JSONB. "
            "Install pgvector and re-run this migration to enable similarity search."
        )


def downgrade() -> None:
    conn = op.get_bind()

    op.drop_index("ix_qb_curriculum_week", table_name="question_bank_items")
    op.drop_index("ix_qb_owner_active", table_name="question_bank_items")
    op.drop_index("ix_qb_subject_class_week", table_name="question_bank_items")

    op.drop_column("question_bank_items", "embedding")
    op.drop_column("question_bank_items", "source_year")
    op.drop_column("question_bank_items", "exam_type")
    op.drop_column("question_bank_items", "week_index")
    op.drop_column("question_bank_items", "curriculum_id")
    op.drop_column("question_bank_items", "owner_type")

    op.drop_column("exam_generation_proposals", "selected_weeks")
    op.drop_column("exam_generation_proposals", "term")

    # Restore NOT NULL only if no platform rows would violate it.
    orphan_count = conn.execute(
        text("SELECT COUNT(*) FROM question_bank_items WHERE school_id IS NULL")
    ).scalar()
    if not orphan_count:
        op.alter_column(
            "question_bank_items",
            "school_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )
    else:
        logger.warning(
            "%s rows have NULL school_id - cannot restore NOT NULL constraint.",
            orphan_count,
        )

    op.drop_table("curriculum_mappings")