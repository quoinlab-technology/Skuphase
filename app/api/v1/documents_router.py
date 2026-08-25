"""Document management API endpoints."""

import asyncio
import uuid
import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.dependencies import get_current_user
from app.core.database import get_db_session, async_session_maker
from app.config.settings import get_settings
from app.models.user import User
from app.models.asset import LearningAsset
from app.schemas.document import (
    DocumentUploadRequest,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentProcessRequest,
    DocumentProcessResponse,
    SearchRequest,
    SearchResponse,
)
from app.schemas.asset import LearningAssetResponse
from app.services.document_service import DocumentService
from app.services.school_service import SchoolService


logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize router
router = APIRouter()

# Configuration for file storage
UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
    summary="Upload a document",
    description="Upload a document to the school. File will be processed asynchronously.",
    tags=["Documents"],
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    """
    Upload a document to the school.
    
    Supported document types:
    - curriculum: Curriculum documents
    - lesson_note: Lesson notes and materials
    - past_paper: Past exam papers
    - scheme_of_work: Scheme of work documents
    
    File Storage:
    - Files are saved to: uploads/documents/{school_id}/{document_id}/{filename}
    - Maximum file size: 50MB
    - Extracted content is stored in database during processing
    """
    try:
        # Verify user has admin role
        if current_user.role != "school_admin":
            raise HTTPException(
                status_code=403,
                detail="Only school administrators can upload documents",
            )
        
        # Validate document type
        valid_types = ["curriculum", "lesson_note", "past_paper", "scheme_of_work"]
        if document_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}",
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a name")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Basic file size validation (e.g., max 50MB)
        max_size = 50 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum of {max_size / 1024 / 1024}MB",
            )
        
        # Generate document ID and create file path
        document_id = uuid.uuid4()
        school_id = current_user.school_id
        
        try:
            # Create directory structure: uploads/documents/{school_id}/{document_id}/
            file_directory = UPLOAD_DIR / str(school_id) / str(document_id)
            file_directory.mkdir(parents=True, exist_ok=True)
            
            # Save file to disk
            file_path = file_directory / file.filename
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Store path in database - use forward slashes for consistency
            # Path format: uploads/documents/{school_id}/{document_id}/{filename}
            relative_path = str(file_path).replace("\\", "/")
            if relative_path.startswith("uploads"):
                # Already relative
                pass
            else:
                # If absolute path, try to make it relative
                try:
                    relative_path = str(file_path.relative_to(Path.cwd())).replace("\\", "/")
                except ValueError:
                    # If relative_to fails (different drives on Windows), use the path as-is
                    relative_path = str(file_path).replace("\\", "/")
            
            mime_type = file.content_type or "application/octet-stream"
            
        except Exception as e:
            logger.error(f"Failed to save file to disk: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}",
            )
        
        # Upload document metadata to database
        response = await DocumentService.upload_document(
            school_id=school_id,
            document_type=document_type,
            file_name=file.filename,
            file_path=relative_path,
            db=db,
            file_size=file_size,
            mime_type=mime_type,
            content="",  # Will be populated during processing
            document_id=document_id,
        )
        
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}",
        )


@router.get(
    "/",
    response_model=DocumentListResponse,
    status_code=200,
    summary="List documents",
    description="List all documents in the school with pagination.",
    tags=["Documents"],
)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    document_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """
    List all documents in the school.
    
    Supports filtering by document_type:
    - curriculum
    - lesson_note
    - past_paper
    - scheme_of_work
    """
    try:
        response = await DocumentService.list_documents(
            school_id=current_user.school_id,
            db=db,
            skip=skip,
            limit=limit,
            document_type=document_type,
        )
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    status_code=200,
    summary="Get document details",
    description="Get detailed information about a specific document.",
    tags=["Documents"],
)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentDetailResponse:
    """Get detailed information about a specific document."""
    try:
        response = await DocumentService.get_document(
            document_id=document_id,
            school_id=current_user.school_id,
            db=db,
        )
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}",
        )


@router.get(
    "/{document_id}/visual-assets",
    response_model=list[LearningAssetResponse],
    status_code=200,
    summary="List extracted visual assets for a document",
    description="Returns learning assets extracted or linked from a document.",
    tags=["Documents"],
)
async def list_document_visual_assets(
    document_id: uuid.UUID,
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[LearningAssetResponse]:
    """List visual assets attached to a source document."""
    # Validate document ownership
    _ = await DocumentService.get_document(
        document_id=document_id,
        school_id=current_user.school_id,
        db=db,
    )

    query = select(LearningAsset).where(
        and_(
            LearningAsset.school_id == current_user.school_id,
            LearningAsset.source_document_id == document_id,
        )
    )
    if not include_inactive:
        query = query.where(LearningAsset.is_active.is_(True))
    query = query.order_by(LearningAsset.created_at.asc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete(
    "/{document_id}",
    status_code=200,
    summary="Delete a document",
    description="Delete a document and all its chunks.",
    tags=["Documents"],
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Delete a document and all its associated chunks.
    
    Only school administrators can delete documents.
    """
    try:
        # Verify user has admin role
        if current_user.role != "school_admin":
            raise HTTPException(
                status_code=403,
                detail="Only school administrators can delete documents",
            )
        
        response = await DocumentService.delete_document(
            document_id=document_id,
            school_id=current_user.school_id,
            db=db,
        )
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}",
        )


@router.post(
    "/{document_id}/process",
    response_model=dict,
    status_code=202,
    summary="Process a document (async)",
    description="Start processing a document in the background. Returns immediately with processing status.",
    tags=["Documents"],
)
async def process_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Start processing a document in the background.
    
    This endpoint:
    1. Validates the document exists and belongs to the school
    2. Starts background processing (extract text, chunk, embed)
    3. Returns immediately with status "processing"
    4. Client can poll GET /documents/{id} to check status
    
    Processing happens asynchronously:
    - Status updates: pending → in_progress → completed/failed
    - Check document.processing_status to track progress
    
    Returns:
        202 Accepted with processing status
    """
    try:
        # Verify user has admin role
        if current_user.role != "school_admin":
            raise HTTPException(
                status_code=403,
                detail="Only school administrators can process documents",
            )
        
        # Get document to verify ownership and get file path
        document = await DocumentService.get_document(
            document_id=document_id,
            school_id=current_user.school_id,
            db=db,
        )
        
        # Check if already processing
        if document.processing_status == "in_progress":
            return {
                "message": "Document is already being processed",
                "document_id": str(document_id),
                "processing_status": "in_progress",
            }
        
        # Check if already completed
        if document.processing_status == "completed":
            return {
                "message": "Document has already been processed",
                "document_id": str(document_id),
                "processing_status": "completed",
            }
        
        # Add background task
        background_tasks.add_task(
            process_document_background,
            document_id=document_id,
            file_path=document.file_path,
            school_id=current_user.school_id,
        )
        
        # Update status to in_progress immediately
        await DocumentService.update_document_status(
            document_id=document_id,
            processing_status="in_progress",
            db=db,
        )
        
        return {
            "message": "Document processing started in background",
            "document_id": str(document_id),
            "processing_status": "in_progress",
            "poll_endpoint": f"/api/v1/documents/{document_id}",
            "estimated_time_seconds": 15,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start document processing: {str(e)}",
        )


async def process_document_background(
    document_id: uuid.UUID,
    file_path: str,
    school_id: uuid.UUID,
):
    """
    Background task to process a document.

    This runs asynchronously after the HTTP response is sent.
    """
    attempts = max(1, settings.background_retry_attempts)
    base_delay = max(0.5, float(settings.background_retry_base_delay_seconds))

    for attempt in range(1, attempts + 1):
        async with async_session_maker() as db:
            try:
                logger.info(
                    "Starting background processing for document %s (attempt %s/%s)",
                    document_id,
                    attempt,
                    attempts,
                )
                await DocumentService.update_document_status(
                    document_id=document_id,
                    processing_status="in_progress",
                    processing_error=None,
                    db=db,
                )
                await DocumentService.process_document_file(
                    document_id=document_id,
                    file_path=file_path,
                    school_id=school_id,
                    db=db,
                    generate_embeddings=True,
                )
                logger.info("Background processing completed for document %s", document_id)
                return
            except Exception as e:
                logger.error(
                    "Background processing failed for document %s (attempt %s/%s): %s",
                    document_id,
                    attempt,
                    attempts,
                    str(e),
                )
                if attempt >= attempts:
                    try:
                        await DocumentService.update_document_status(
                            document_id=document_id,
                            processing_status="failed",
                            processing_error=str(e),
                            db=db,
                        )
                    except Exception as update_error:
                        logger.error(f"Failed to update error status: {str(update_error)}")
                    return

        await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
