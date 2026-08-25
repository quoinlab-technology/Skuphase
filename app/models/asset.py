"""Asset models for visual and formula references."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class LearningAsset(BaseModel):
    """School-scoped asset used by lesson notes and exam generation."""

    __tablename__ = "learning_assets"

    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("school_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    asset_type = Column(String(30), nullable=False)  # image, diagram, formula, table
    asset_source = Column(
        String(40),
        nullable=False,
        default="lesson_note",
    )  # lesson_note, exam_requirement, question_bank, manual

    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)

    reference_code = Column(String(64), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True)

    subject = Column(String(100), nullable=True)
    grade_level = Column(String(50), nullable=True)
    topic = Column(String(255), nullable=True)
    tags = Column(JSON, nullable=True)

    is_ai_usable = Column(Boolean, nullable=False, default=False)
    processing_status = Column(
        String(20),
        nullable=False,
        default="needs_review",
    )  # needs_review, approved, rejected
    is_active = Column(Boolean, nullable=False, default=True)

    school = relationship("School", back_populates="learning_assets")
    uploaded_by = relationship("User", back_populates="learning_assets")
    source_document = relationship("SchoolDocument", back_populates="learning_assets")
    document_refs = relationship(
        "DocumentVisualRef",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    question_refs = relationship(
        "QuestionAssetRef",
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class DocumentVisualRef(BaseModel):
    """Links a lesson-note page/chunk to a visual asset record."""

    __tablename__ = "document_visual_refs"

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("school_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number = Column(Integer, nullable=True)
    anchor_text = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)

    document = relationship("SchoolDocument", back_populates="visual_refs")
    chunk = relationship("DocumentChunk", back_populates="visual_refs")
    asset = relationship("LearningAsset", back_populates="document_refs")


class QuestionAssetRef(BaseModel):
    """Links an exam question to an approved learning asset."""

    __tablename__ = "question_asset_refs"

    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learning_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    usage_type = Column(
        String(30),
        nullable=False,
        default="required",
    )  # required, supporting, optional
    caption_override = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_mandatory = Column(Boolean, nullable=False, default=True)

    question = relationship("Question", back_populates="asset_refs")
    asset = relationship("LearningAsset", back_populates="question_refs")
