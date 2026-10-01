"""Curriculum and Scheme of Work API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.curriculum_service import CurriculumService
from app.schemas.curriculum import (
    ClassListResponse,
    BoardListResponse,
    SubjectListResponse,
    TermListResponse,
    WeekListResponse,
    CurriculumSearchResult,
)

router = APIRouter()


@router.get("/boards", response_model=BoardListResponse)
async def list_boards(db: AsyncSession = Depends(get_db_session)):
    """Get educational boards available in the seeded curriculum database."""
    return BoardListResponse(boards=await CurriculumService.get_boards(db))


@router.get("/classes", response_model=ClassListResponse)
async def list_classes(
    board: str = Query("NERDC", description="Educational board (e.g. NERDC)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get all available class levels (from Pre-Nursery to Primary 6).
    """
    classes = await CurriculumService.get_all_classes(db, board=board)
    return ClassListResponse(classes=classes)


@router.get("/subjects", response_model=SubjectListResponse)
async def list_subjects(
    class_level: str = Query(..., description="Class level (e.g. Primary 4, JSS 1)"),
    board: str = Query("NERDC", description="Educational board (e.g. NERDC)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get all available subjects for a specific class level.
    """
    subjects = await CurriculumService.get_subjects_by_class(class_level=class_level, db=db, board=board)
    return SubjectListResponse(class_level=class_level, subjects=subjects)


@router.get("/terms", response_model=TermListResponse)
async def list_terms():
    """
    Get academic terms (First Term, Second Term, Third Term).
    """
    terms = await CurriculumService.get_terms()
    return TermListResponse(terms=terms)


@router.get("/weeks", response_model=WeekListResponse)
async def list_weeks(
    class_level: str = Query(..., description="Class level (e.g. Primary 4)"),
    subject: str = Query(..., description="Subject name (e.g. Mathematics)"),
    term: str = Query(..., description="Academic term (e.g. First Term)"),
    board: str = Query("NERDC", description="Educational board (e.g. NERDC)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get weekly breakdown of topics and behavioral learning objectives for selected subject and term.
    """
    weeks = await CurriculumService.get_weeks_by_subject(
        class_level=class_level,
        subject_name=subject,
        term=term,
        db=db,
        board=board,
    )
    return WeekListResponse(
        class_level=class_level,
        subject_name=subject,
        term=term,
        weeks=weeks,
    )


@router.get("/search", response_model=List[CurriculumSearchResult])
async def search_curriculum(
    q: str = Query(..., min_length=2, description="Search keyword in topics and objectives"),
    class_level: Optional[str] = Query(None, description="Optional class level filter"),
    subject: Optional[str] = Query(None, description="Optional subject filter"),
    board: Optional[str] = Query(None, description="Optional educational board filter"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Search topics and learning objectives across the entire curriculum database.
    """
    return await CurriculumService.search_topics(
        query=q,
        db=db,
        class_level=class_level,
        subject_name=subject,
        board=board,
        limit=limit,
    )
