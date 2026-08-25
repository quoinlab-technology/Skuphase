"""Add learning assets and reference tables.

Revision ID: 0008_learning_assets_refs
Revises: 0007_question_bank_items
Create Date: 2026-03-04 20:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0008_learning_assets_refs"
down_revision: Union[str, None] = "0007_question_bank_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_assets",
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("asset_source", sa.String(length=40), nullable=False, server_default="lesson_note"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("reference_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(length=100), nullable=True),
        sa.Column("grade_level", sa.String(length=50), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_ai_usable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processing_status", sa.String(length=20), nullable=False, server_default="needs_review"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["school_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "reference_code", name="uq_learning_assets_school_reference"),
    )
    op.create_index(
        "ix_learning_assets_school_subject_grade",
        "learning_assets",
        ["school_id", "subject", "grade_level"],
        unique=False,
    )
    op.create_index(
        "ix_learning_assets_school_status",
        "learning_assets",
        ["school_id", "processing_status", "is_active"],
        unique=False,
    )

    op.create_table(
        "document_visual_refs",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("anchor_text", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["learning_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["school_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_visual_refs_document_page",
        "document_visual_refs",
        ["document_id", "page_number"],
        unique=False,
    )

    op.create_table(
        "question_asset_refs",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usage_type", sa.String(length=30), nullable=False, server_default="required"),
        sa.Column("caption_override", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["learning_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "asset_id", name="uq_question_asset_refs_question_asset"),
    )
    op.create_index(
        "ix_question_asset_refs_question_order",
        "question_asset_refs",
        ["question_id", "display_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_question_asset_refs_question_order", table_name="question_asset_refs")
    op.drop_table("question_asset_refs")

    op.drop_index("ix_document_visual_refs_document_page", table_name="document_visual_refs")
    op.drop_table("document_visual_refs")

    op.drop_index("ix_learning_assets_school_status", table_name="learning_assets")
    op.drop_index("ix_learning_assets_school_subject_grade", table_name="learning_assets")
    op.drop_table("learning_assets")
