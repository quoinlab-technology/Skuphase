"""Document management schemas."""

from uuid import UUID
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DocumentUploadRequest(BaseModel):
    """Request to upload a document."""
    
    document_type: str = Field(..., pattern="^(curriculum|lesson_note|past_paper|scheme_of_work)$")
    file_name: str = Field(..., min_length=1, max_length=255)


class DocumentMetadata(BaseModel):
    """Document metadata response."""
    
    page_count: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    """Detailed document response."""
    
    id: UUID
    school_id: UUID
    document_type: str
    file_name: str
    file_path: Optional[str] = None
    processing_status: Literal["pending", "in_progress", "completed", "failed"]
    processing_error: Optional[str] = None
    metadata: Optional[DocumentMetadata] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """List of documents response."""
    
    total: int
    documents: List[DocumentDetailResponse]


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    
    message: str
    document_id: UUID
    file_name: str
    processing_status: Literal["pending", "in_progress", "completed", "failed"]


class DocumentChunkResponse(BaseModel):
    """Document chunk response for RAG retrieval."""
    
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    similarity_score: Optional[float] = None
    chunk_metadata: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    """RAG search request."""
    
    query: str = Field(..., min_length=1, max_length=1000)
    document_type: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResponse(BaseModel):
    """RAG search response with relevant chunks."""
    
    query: str
    total_chunks_found: int
    chunks: List[DocumentChunkResponse]


class DocumentProcessRequest(BaseModel):
    """Request to process a document (extract text and create embeddings)."""
    
    document_id: UUID


class DocumentProcessResponse(BaseModel):
    """Response after document processing."""
    
    message: str
    document_id: UUID
    chunks_created: int
    processing_status: Literal["pending", "in_progress", "completed", "failed"]
