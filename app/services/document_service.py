"""Document service for RAG operations."""

import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, delete

from app.config.settings import get_settings
from app.models.document import SchoolDocument, DocumentChunk
from app.models.asset import LearningAsset, DocumentVisualRef
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentChunkResponse,
    SearchResponse,
    DocumentProcessResponse,
    DocumentMetadata,
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentService:
    """Service for document management and RAG operations."""

    VECTOR_DIMENSION = 1024

    @staticmethod
    async def upload_document(
        school_id: uuid.UUID,
        document_type: str,
        file_name: str,
        file_path: str,
        db: AsyncSession,
        file_size: int = 0,
        mime_type: str = "application/pdf",
        content: str = "",
        document_id: Optional[uuid.UUID] = None,
    ) -> DocumentUploadResponse:
        """
        Upload a document to the school.

        Args:
            school_id: School ID
            document_type: Type of document
            file_name: Name of the file
            file_path: Path to file in storage (relative or absolute)
            db: Database session
            file_size: File size in bytes
            mime_type: MIME type of file
            content: Extracted text content
            document_id: Optional pre-generated document ID

        Returns:
            DocumentUploadResponse
        """
        try:
            doc_id = document_id or uuid.uuid4()
            document = SchoolDocument(
                id=doc_id,
                school_id=school_id,
                document_type=document_type,
                file_name=file_name,
                file_path=file_path,
                content=content,
                file_size=file_size,
                mime_type=mime_type,
                processing_status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
            return DocumentUploadResponse(
                message=f"Document '{file_name}' uploaded successfully. Processing will begin shortly.",
                document_id=document.id,
                file_name=document.file_name,
                processing_status=document.processing_status,
            )
        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to upload document: {str(e)}")


    @staticmethod
    async def list_documents(
        school_id: uuid.UUID,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        document_type: Optional[str] = None,
    ) -> DocumentListResponse:
        """
        List documents for a school.

        Args:
            school_id: School ID
            db: Database session
            skip: Number to skip
            limit: Max results
            document_type: Filter by type

        Returns:
            DocumentListResponse
        """
        # Build query
        query = select(SchoolDocument).filter(SchoolDocument.school_id == school_id)
        
        if document_type:
            query = query.filter(SchoolDocument.document_type == document_type)
        
        # Get total count without materializing all rows
        count_query = select(func.count()).select_from(SchoolDocument).filter(
            SchoolDocument.school_id == school_id
        )
        if document_type:
            count_query = count_query.filter(SchoolDocument.document_type == document_type)
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get paginated results
        result = await db.execute(
            query.offset(skip).limit(limit)
        )
        documents = result.scalars().all()
        
        doc_details = [
            DocumentDetailResponse(
                id=doc.id,
                school_id=doc.school_id,
                document_type=doc.document_type,
                file_name=doc.file_name,
                file_path=doc.file_path,
                processing_status=doc.processing_status,
                processing_error=doc.processing_error,
                metadata=DocumentMetadata(
                    page_count=doc.page_count,
                    file_size=doc.file_size,
                    mime_type=doc.mime_type,
                ),
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]
        
        return DocumentListResponse(
            total=total,
            documents=doc_details,
        )

    @staticmethod
    async def get_document(
        document_id: uuid.UUID,
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> DocumentDetailResponse:
        """
        Get document details.

        Args:
            document_id: Document ID
            school_id: School ID (for access verification)
            db: Database session

        Returns:
            DocumentDetailResponse

        Raises:
            ValueError: If document not found or access denied
        """
        result = await db.execute(
            select(SchoolDocument).filter(
                and_(
                    SchoolDocument.id == document_id,
                    SchoolDocument.school_id == school_id,
                )
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        return DocumentDetailResponse(
            id=document.id,
            school_id=document.school_id,
            document_type=document.document_type,
            file_name=document.file_name,
            file_path=document.file_path,
            processing_status=document.processing_status,
            processing_error=document.processing_error,
            metadata=DocumentMetadata(
                page_count=document.page_count,
                file_size=document.file_size,
                mime_type=document.mime_type,
            ),
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @staticmethod
    async def delete_document(
        document_id: uuid.UUID,
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """
        Delete a document and its chunks.

        Args:
            document_id: Document ID
            school_id: School ID (for access verification)
            db: Database session

        Returns:
            Confirmation dict

        Raises:
            ValueError: If document not found or access denied
        """
        # Verify document exists and belongs to school
        result = await db.execute(
            select(SchoolDocument).filter(
                and_(
                    SchoolDocument.id == document_id,
                    SchoolDocument.school_id == school_id,
                )
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        try:
            # Delete document (cascades to chunks)
            await db.delete(document)
            await db.commit()
            
            return {
                "message": f"Document '{document.file_name}' deleted successfully",
                "document_id": str(document_id),
                "deleted": True,
            }
        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to delete document: {str(e)}")

    @staticmethod
    async def create_chunks(
        document_id: uuid.UUID,
        chunks_data: List[dict],
        db: AsyncSession,
    ) -> DocumentProcessResponse:
        """
        Create document chunks from extracted text.

        Args:
            document_id: Document ID
            chunks_data: List of {content, embedding, metadata}
            db: Database session

        Returns:
            DocumentProcessResponse

        Raises:
            ValueError: If document not found
        """
        # Verify document exists
        result = await db.execute(
            select(SchoolDocument).filter(SchoolDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        try:
            chunk_count = 0
            
            for idx, chunk_data in enumerate(chunks_data):
                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk_data.get("content", ""),
                    embedding=chunk_data.get("embedding"),  # Store as JSON
                    chunk_metadata=chunk_data.get("metadata", {}),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(chunk)
                chunk_count += 1
            
            # Update document status
            await db.execute(
                update(SchoolDocument)
                .where(SchoolDocument.id == document_id)
                .values(
                    processing_status="completed",
                    updated_at=datetime.utcnow(),
                )
            )
            
            await db.commit()
            
            return DocumentProcessResponse(
                message=f"Document processed successfully with {chunk_count} chunks created",
                document_id=document_id,
                chunks_created=chunk_count,
                processing_status="completed",
            )
        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to create chunks: {str(e)}")

    @staticmethod
    async def search_chunks(
        school_id: uuid.UUID,
        query: str,
        db: AsyncSession,
        document_type: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchResponse:
        """
        Search document chunks using semantic similarity.
        
        Note: This is a basic implementation that returns all chunks.
        For production, implement actual vector similarity search with pgvector.

        Args:
            school_id: School ID
            query: Search query
            db: Database session
            document_type: Filter by document type
            top_k: Top K results to return

        Returns:
            SearchResponse
        """
        rag_service = RAGService()
        chunks = await rag_service.search(
            school_id=school_id,
            query=query,
            db=db,
            document_type=document_type,
            top_k=top_k,
            use_vector=True,  # pgvector-first, text fallback when embeddings are unavailable
        )

        chunk_responses = [
            DocumentChunkResponse(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                similarity_score=chunk.get("similarity_score", 0.0),
                chunk_metadata=chunk.get("chunk_metadata"),
            )
            for chunk in chunks
        ]
        
        return SearchResponse(
            query=query,
            total_chunks_found=len(chunk_responses),
            chunks=chunk_responses,
        )

    @staticmethod
    async def update_document_status(
        document_id: uuid.UUID,
        processing_status: str,
        processing_error: Optional[str] = None,
        page_count: Optional[int] = None,
        db: AsyncSession = None,
    ) -> None:
        """
        Update document processing status.

        Args:
            document_id: Document ID
            processing_status: New status
            processing_error: Error message if failed
            page_count: Page count (if extracted)
            db: Database session
        """
        try:
            values_to_update = {
                "processing_status": processing_status,
                "updated_at": datetime.utcnow(),
            }
            
            if processing_error:
                values_to_update["processing_error"] = processing_error
            
            if page_count:
                values_to_update["page_count"] = page_count
            
            await db.execute(
                update(SchoolDocument)
                .where(SchoolDocument.id == document_id)
                .values(**values_to_update)
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to update document status: {str(e)}")

    @staticmethod
    async def process_document_file(
        document_id: uuid.UUID,
        file_path: str,
        school_id: uuid.UUID,
        db: AsyncSession,
        generate_embeddings: bool = True,
    ) -> DocumentProcessResponse:
        """
        Process a document file (extract text, chunk, embed).
        
        Args:
            document_id: Document ID
            file_path: Path to document file
            school_id: School ID
            db: Database session
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            DocumentProcessResponse
            
        Raises:
            ValueError: If document not found or processing fails
        """
        # Import here to avoid circular dependencies and optional dependencies
        try:
            from app.services.document_processor import DocumentProcessor
            from app.services.embedding_service import EmbeddingService
        except ImportError as e:
            raise ValueError(f"Required processing libraries not available: {str(e)}")
        
        # Verify document exists
        result = await db.execute(
            select(SchoolDocument).filter(
                and_(
                    SchoolDocument.id == document_id,
                    SchoolDocument.school_id == school_id,
                )
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        try:
            # Update status to processing
            await db.execute(
                update(SchoolDocument)
                .where(SchoolDocument.id == document_id)
                .values(processing_status="in_progress", updated_at=datetime.utcnow())
            )
            await db.commit()

            # Idempotency: clear previous chunks before reprocessing.
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            await db.commit()
            
            # Extract and chunk document
            processor = DocumentProcessor()
            asset_output_dir = (
                Path("uploads/assets") / str(school_id) / str(document_id) / "auto"
            )
            process_result = processor.process_pdf(
                file_path=file_path,
                asset_output_dir=str(asset_output_dir),
                extract_images=settings.pdf_image_extraction_enabled,
                enable_ocr=settings.ocr_enabled,
            )
            
            if not process_result["success"]:
                raise ValueError(process_result["error"])
            
            # Update document with extracted content
            await db.execute(
                update(SchoolDocument)
                .where(SchoolDocument.id == document_id)
                .values(
                    content=process_result["full_text"],
                    page_count=process_result["page_count"],
                    updated_at=datetime.utcnow(),
                )
            )
            await db.commit()
            
            # Generate embeddings if requested
            chunk_count = len(process_result["chunks"])
            
            if generate_embeddings and chunk_count > 0:
                try:
                    embedding_service = EmbeddingService()
                    embeddings = await embedding_service.embed_texts(
                        process_result["chunks"]
                    )
                    
                    # Create chunks with embeddings in small batches to avoid database hangs
                    # Smaller batch size (10) to prevent memory issues with large embeddings
                    BATCH_SIZE = 50
                    for idx, (chunk_text, embedding) in enumerate(
                        zip(process_result["chunks"], embeddings)
                    ):
                        if len(embedding) != DocumentService.VECTOR_DIMENSION:
                            raise ValueError(
                                f"Embedding dimension mismatch for chunk {idx}: "
                                f"got {len(embedding)}, expected {DocumentService.VECTOR_DIMENSION}"
                            )

                        chunk = DocumentChunk(
                            id=uuid.uuid4(),
                            document_id=document_id,
                            chunk_index=idx,
                            content=chunk_text,
                            embedding=embedding,  # Store as list (pgvector will handle)
                            chunk_metadata={
                                "chunk_position": idx,
                                "chunk_size": len(chunk_text),
                                "tokens": len(chunk_text.split()),
                            },
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(chunk)
                        
                        # Flush and commit in small batches to avoid database hangs
                        if (idx + 1) % BATCH_SIZE == 0:
                            await db.flush()  # Write to database without committing
                            await db.commit()  # Commit the batch
                            logger.info(f"✅ Committed batch of {BATCH_SIZE} chunks (total: {idx + 1}/{chunk_count})")
                    
                    # Commit any remaining chunks
                    await db.flush()
                    await db.commit()
                    
                    logger.info(
                        f"✅ Processed document {document_id}: "
                        f"{chunk_count} chunks with {DocumentService.VECTOR_DIMENSION}-dim embeddings"
                    )
                    
                except Exception as e:
                    # Log embedding error but don't fail
                    logger.warning(
                        f"Failed to generate embeddings for document {document_id}: {str(e)}"
                    )
                    
                    # Create chunks without embeddings
                    for idx, chunk_text in enumerate(process_result["chunks"]):
                        chunk = DocumentChunk(
                            id=uuid.uuid4(),
                            document_id=document_id,
                            chunk_index=idx,
                            content=chunk_text,
                            embedding=None,
                            chunk_metadata={
                                "chunk_position": idx,
                                "chunk_size": len(chunk_text),
                            },
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(chunk)
                    
                    await db.commit()
            else:
                # Create chunks without embeddings
                for idx, chunk_text in enumerate(process_result["chunks"]):
                    chunk = DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=document_id,
                        chunk_index=idx,
                        content=chunk_text,
                        embedding=None,
                        chunk_metadata={
                            "chunk_position": idx,
                            "chunk_size": len(chunk_text),
                        },
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(chunk)
                
                    await db.commit()

            extracted_images = process_result.get("extracted_images", [])
            if extracted_images:
                await db.execute(
                    delete(DocumentVisualRef).where(
                        DocumentVisualRef.document_id == document_id
                    )
                )
                await db.execute(
                    delete(LearningAsset).where(
                        and_(
                            LearningAsset.school_id == school_id,
                            LearningAsset.source_document_id == document_id,
                            LearningAsset.asset_source == "lesson_note",
                        )
                    )
                )
                await db.commit()

                for index, image_data in enumerate(extracted_images, start=1):
                    page_number = int(image_data.get("page_number") or 0)
                    reference_code = (
                        f"DOC-{str(document_id)[:8].upper()}-"
                        f"P{page_number:03d}-I{index:03d}-"
                        f"{uuid.uuid4().hex[:4].upper()}"
                    )
                    asset = LearningAsset(
                        id=uuid.uuid4(),
                        school_id=school_id,
                        uploaded_by_user_id=None,
                        source_document_id=document_id,
                        asset_type="image",
                        asset_source="lesson_note",
                        file_name=image_data.get("file_name") or f"asset_{index}.png",
                        file_path=str(image_data.get("file_path") or "").replace("\\", "/"),
                        mime_type=None,
                        reference_code=reference_code,
                        title=f"Extracted visual - page {page_number}",
                        description=None,
                        ocr_text=image_data.get("ocr_text"),
                        subject=None,
                        grade_level=None,
                        topic=None,
                        tags=["auto_extracted"],
                        is_ai_usable=False,
                        processing_status="needs_review",
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(asset)
                    await db.flush()

                    db.add(
                        DocumentVisualRef(
                            id=uuid.uuid4(),
                            document_id=document_id,
                            chunk_id=None,
                            asset_id=asset.id,
                            page_number=page_number if page_number > 0 else None,
                            anchor_text=image_data.get("ocr_text"),
                            display_order=index,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                    )

                await db.commit()
            
            # Update document status to completed
            await db.execute(
                update(SchoolDocument)
                .where(SchoolDocument.id == document_id)
                .values(processing_status="completed", updated_at=datetime.utcnow())
            )
            await db.commit()
            
            return DocumentProcessResponse(
                message=f"Document processed successfully with {chunk_count} chunks",
                document_id=document_id,
                chunks_created=chunk_count,
                processing_status="completed",
            )
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            
            # Update status to failed
            try:
                await db.execute(
                    update(SchoolDocument)
                    .where(SchoolDocument.id == document_id)
                    .values(
                        processing_status="failed",
                        processing_error=str(e),
                        updated_at=datetime.utcnow(),
                    )
                )
                await db.commit()
            except:
                pass
            
            raise ValueError(f"Document processing failed: {str(e)}")
