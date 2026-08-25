"""RAG service for semantic search with vector embeddings."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

try:  # optional dependency - vector search degrades gracefully without it
    from pgvector.sqlalchemy import Vector  # noqa: F401
except ImportError:  # pragma: no cover
    Vector = None
except ImportError:  # pragma: no cover - pgvector not installed
    Vector = None

from app.models.document import DocumentChunk, SchoolDocument
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RAGService:
    """Retrieval-Augmented Generation service for semantic search."""

    VECTOR_DIMENSION = 1024
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize RAG service.
        
        Args:
            embedding_service: Service for generating embeddings
        """
        if embedding_service is not None:
            self.embedding_service = embedding_service
        else:
            try:
                self.embedding_service = EmbeddingService()
            except Exception as e:
                logger.warning(f"Embedding service unavailable at startup, using text fallback: {str(e)}")
                self.embedding_service = None
    
    async def search_by_embedding(
        self,
        school_id: UUID,
        query_embedding: List[float],
        db: AsyncSession,
        document_type: Optional[str] = None,
        document_ids: Optional[List[UUID]] = None,
        top_k: int = 5,
    ) -> List[dict]:
        """
        Search documents using vector similarity (requires pgvector).
        
        Args:
            school_id: School ID for filtering
            query_embedding: Query embedding vector
            db: Database session
            document_type: Optional document type filter
            top_k: Number of results to return
            
        Returns:
            List of matching chunks with similarity scores
        """
        # Build base query with vector similarity
        query = select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            DocumentChunk.chunk_metadata,
            # Calculate similarity (1 - cosine distance)
            (1 - (DocumentChunk.embedding.cosine_distance(query_embedding))).label("similarity")
        ).join(
            SchoolDocument,
            DocumentChunk.document_id == SchoolDocument.id
        ).where(
            SchoolDocument.school_id == school_id
        )
        
        # Apply document type filter if provided
        if document_type:
            query = query.where(SchoolDocument.document_type == document_type)

        # Restrict to explicitly selected documents when provided
        if document_ids:
            query = query.where(SchoolDocument.id.in_(document_ids))
        
        # Order by similarity and limit results
        query = query.order_by(
            DocumentChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await db.execute(query)
        rows = result.all()
        
        # Format results
        chunks = [
            {
                "chunk_id": str(row.id),
                "document_id": str(row.document_id),
                "chunk_index": row.chunk_index,
                "content": row.content,
                "similarity_score": float(row.similarity),
                "chunk_metadata": row.chunk_metadata or {},
            }
            for row in rows
        ]

        if chunks:
            similarities = [c["similarity_score"] for c in chunks]
            source_docs = {c["document_id"] for c in chunks}
            logger.info(
                "Vector search telemetry: top_k=%s returned=%s docs=%s max_sim=%.4f min_sim=%.4f",
                top_k,
                len(chunks),
                len(source_docs),
                max(similarities),
                min(similarities),
            )
        else:
            logger.info("Vector search telemetry: top_k=%s returned=0", top_k)
        return chunks
    
    async def search_by_text(
        self,
        school_id: UUID,
        db: AsyncSession,
        query: Optional[str] = None,
        document_type: Optional[str] = None,
        document_ids: Optional[List[UUID]] = None,
        top_k: int = 5,
    ) -> List[dict]:
        """
        Search documents using basic text matching (fallback).
        
        This is a simple implementation for when vector search is not available.
        
        Args:
            school_id: School ID for filtering
            db: Database session
            query: Search query text
            document_type: Optional document type filter
            top_k: Number of results to return
            
        Returns:
            List of matching chunks
        """
        try:
            base_query = select(DocumentChunk).join(
                SchoolDocument,
                DocumentChunk.document_id == SchoolDocument.id
            ).where(
                SchoolDocument.school_id == school_id
            )
            
            if document_type:
                base_query = base_query.where(
                    SchoolDocument.document_type == document_type
                )

            if document_ids:
                base_query = base_query.where(SchoolDocument.id.in_(document_ids))
            
            result = await db.execute(base_query)
            chunks = result.scalars().all()
            
            # Simple text matching
            if query:
                query_lower = query.lower()
                matching_chunks = [
                    c for c in chunks
                    if query_lower in c.content.lower()
                ]
            else:
                matching_chunks = chunks
            
            # Format results (no similarity score for basic search)
            formatted = [
                {
                    "chunk_id": str(c.id),
                    "document_id": str(c.document_id),
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "similarity_score": 0.0,
                    "chunk_metadata": c.chunk_metadata or {},
                }
                for c in matching_chunks[:top_k]
            ]
            
            logger.info(
                "Text search telemetry (fallback): top_k=%s returned=%s",
                top_k,
                len(formatted),
            )
            return formatted
            
        except Exception as e:
            logger.error(f"Text search failed: {str(e)}")
            return []
    
    async def search(
        self,
        school_id: UUID,
        query: str,
        db: AsyncSession,
        document_type: Optional[str] = None,
        document_ids: Optional[List[UUID]] = None,
        top_k: int = 5,
        use_vector: bool = True,
    ) -> List[dict]:
        """
        Search documents with query (embedding-based or text-based).
        
        Args:
            school_id: School ID for filtering
            query: Search query
            db: Database session
            document_type: Optional document type filter
            top_k: Number of results to return
            use_vector: Use vector search if available (fallback to text)
            
        Returns:
            List of matching chunks with similarity scores
        """
        try:
            # Generate query embedding if using vector search
            if use_vector and self.embedding_service is not None:
                try:
                    query_embedding = await self.embedding_service.embed_text(query)

                    # Guardrail: schema expects 1024-dimensional vectors (BGE-M3) for pgvector similarity.
                    if len(query_embedding) != self.VECTOR_DIMENSION:
                        raise ValueError(
                            f"Embedding dimension mismatch: got {len(query_embedding)}, "
                            f"expected {self.VECTOR_DIMENSION}"
                        )

                    return await self.search_by_embedding(
                        school_id=school_id,
                        query_embedding=query_embedding,
                        db=db,
                        document_type=document_type,
                        document_ids=document_ids,
                        top_k=top_k,
                    )
                except Exception as e:
                    logger.warning(f"Vector search unavailable, falling back to text search: {str(e)}")
            
            # Fallback to text search
            return await self.search_by_text(
                school_id=school_id,
                db=db,
                query=query,
                document_type=document_type,
                document_ids=document_ids,
                top_k=top_k,
            )
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    async def initialize_vector_extension(self, db: AsyncSession) -> bool:
        """
        Initialize pgvector extension in PostgreSQL (required for vector search).
        
        Args:
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await db.commit()
            logger.info("pgvector extension initialized")
            return True
        except Exception as e:
            logger.warning(f"Could not initialize pgvector: {str(e)}")
            return False
