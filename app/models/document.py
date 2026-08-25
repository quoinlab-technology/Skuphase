"""School document models for RAG."""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


# NOTE: The embedding column is defined as JSON in the Python model.
# When pgvector is installed on the PostgreSQL server, migration 0009 will
# ALTER the column to VECTOR(1024) for efficient cosine similarity search.
# This design allows migrations to succeed without pgvector and then upgrade
# the column type to vector once pgvector is installed.


class SchoolDocument(BaseModel):
    """Curriculum material uploaded by school for RAG."""
    
    __tablename__ = "school_documents"
    
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    
    document_type = Column(String(50), nullable=False)  # curriculum, lesson_note, past_paper, scheme_of_work
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))  # Storage path
    content = Column(Text)  # Extracted text content
    
    # Metadata
    page_count = Column(Integer)
    file_size = Column(Integer)  # In bytes
    mime_type = Column(String(50))  # application/pdf, application/msword, etc
    
    # Processing status
    processing_status = Column(String(20), default="pending")  # pending, in_progress, completed, failed
    processing_error = Column(Text)  # Error message if processing failed
    
    # Relationships
    school = relationship("School", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    learning_assets = relationship("LearningAsset", back_populates="source_document")
    visual_refs = relationship(
        "DocumentVisualRef",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    exam_context = relationship("ExamContext", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<SchoolDocument(id={self.id}, file_name={self.file_name})>"


class DocumentChunk(BaseModel):
    """Text chunks from documents with embeddings for RAG retrieval.

    The 'embedding' column starts as JSON (a plain float array).
    Migration 0009 upgrades it to PostgreSQL vector(1024) when pgvector is
    installed on the server, enabling HNSW cosine-similarity search.
    """
    
    __tablename__ = "document_chunks"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("school_documents.id", ondelete="CASCADE"), nullable=False)
    
    chunk_index = Column(Integer, nullable=False)  # Order of chunk in document
    content = Column(Text, nullable=False)  # Actual text content

    # JSON-typed embedding — migration 0009 converts to vector(1024) when pgvector is available.
    embedding = Column(JSON, nullable=True)
    
    # Metadata
    chunk_metadata = Column(JSON)  # Page number, section, etc
    
    # Relationships
    document = relationship("SchoolDocument", back_populates="chunks")
    visual_refs = relationship("DocumentVisualRef", back_populates="chunk")
    
    def __repr__(self) -> str:
        return f"<DocumentChunk(document_id={self.document_id}, chunk_index={self.chunk_index})>"
