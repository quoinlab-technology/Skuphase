"""Library API routes for formulas and assessment diagrams."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.library import (
    DiagramMetadata,
    DiagramRenderSpec,
    FormulaItem,
    RenderedDiagramResponse,
)
from app.services.library_service import LibraryService

router = APIRouter()


@router.get("/formulas", response_model=List[FormulaItem])
async def list_formulas(
    subject: Optional[str] = Query(None, description="Filter formulas by subject"),
    q: Optional[str] = Query(None, description="Search query across name, topic, or LaTeX"),
):
    """List or search curriculum formulas and equations."""
    return LibraryService.list_formulas(subject=subject, query=q)


@router.get("/formulas/{formula_id}", response_model=FormulaItem)
async def get_formula(formula_id: str):
    """Get a specific formula by ID."""
    formula = LibraryService.get_formula(formula_id)
    if not formula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formula '{formula_id}' not found",
        )
    return formula


@router.get("/diagrams", response_model=List[DiagramMetadata])
async def list_diagrams(
    subject: Optional[str] = Query(None, description="Filter diagrams by subject"),
    q: Optional[str] = Query(None, description="Search query across title, category, topics"),
):
    """List or search registered assessment diagrams."""
    return LibraryService.list_diagrams(subject=subject, query=q)


@router.get("/diagrams/{diagram_id}", response_model=DiagramMetadata)
async def get_diagram(diagram_id: str):
    """Get metadata and parameter schema for a specific diagram."""
    diag = LibraryService.get_diagram_metadata(diagram_id)
    if not diag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagram '{diagram_id}' not found",
        )
    return diag


@router.post("/diagrams/{diagram_id}/render", response_model=RenderedDiagramResponse)
async def render_diagram(
    diagram_id: str,
    spec: DiagramRenderSpec,
):
    """Render a diagram according to the provided specification.

    Handles study vs exam modes, callout masking, parameter validation,
    and returns sanitized SVG with suggested marking criteria.
    """
    try:
        return LibraryService.render_diagram(diagram_id, spec)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagram generation failed: {e}",
        )
