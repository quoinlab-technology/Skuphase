"""RAG (Retrieval-Augmented Generation) API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.database import get_db_session
from app.models.user import User
from app.schemas.document import SearchRequest, SearchResponse
from app.services.document_service import DocumentService


router = APIRouter()


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=200,
    summary="Search documents using RAG",
    description="Search documents using semantic similarity search across chunks.",
    tags=["RAG"],
)
async def search_documents(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """
    Search documents using semantic similarity.
    
    The search queries document chunks and returns the most relevant ones
    based on semantic similarity to the query text.
    
    Optional filters:
    - document_type: Filter by curriculum, lesson_note, past_paper, or scheme_of_work
    - top_k: Maximum number of chunks to return (default: 5, max: 50)
    """
    try:
        # Validate top_k
        top_k = request.top_k or 5
        if top_k < 1 or top_k > 50:
            raise HTTPException(
                status_code=400,
                detail="top_k must be between 1 and 50",
            )
        
        # Validate query
        if not request.query or len(request.query.strip()) < 2:
            raise HTTPException(
                status_code=400,
                detail="Query must be at least 2 characters long",
            )
        
        # Validate document_type if provided
        if request.document_type:
            valid_types = ["curriculum", "lesson_note", "past_paper", "scheme_of_work"]
            if request.document_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}",
                )
        
        # Search documents
        response = await DocumentService.search_chunks(
            school_id=current_user.school_id,
            query=request.query,
            db=db,
            document_type=request.document_type,
            top_k=top_k,
        )
        
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@router.get(
    "/health",
    status_code=200,
    summary="RAG service health check",
    description="Check if the RAG service is operational.",
    tags=["RAG"],
)
async def health_check() -> dict:
    """Check RAG service health."""
    return {
        "status": "operational",
        "service": "RAG (Retrieval-Augmented Generation)",
        "features": [
            "Document search",
            "Semantic similarity",
            "Multi-document context",
        ],
    }
