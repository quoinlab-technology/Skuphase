"""School management API routes."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.schemas.auth import CurrentUser
from app.schemas.school import (
    SchoolSettingsUpdate,
    SchoolSettingsResponse,
    SchoolDetailResponse,
    SchoolUpdateRequest,
)
from app.services.school_service import SchoolService


router = APIRouter()


@router.get("/{school_id}", response_model=SchoolDetailResponse)
async def get_school(
    school_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get school details including settings.

    User must belong to this school to view details.
    """
    # Verify user belongs to this school
    if current_user.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this school",
        )

    try:
        response = await SchoolService.get_school(
            school_id=school_id,
            db=db,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get school: {str(e)}")


@router.put("/{school_id}", response_model=SchoolDetailResponse)
async def update_school(
    school_id: uuid.UUID,
    request: SchoolUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update school information.

    Only school_admin users can update school information.
    """
    # Verify user belongs to this school
    if current_user.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this school",
        )

    # Check if current user is a school admin
    if current_user.role != "school_admin":
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can update school information",
        )

    try:
        response = await SchoolService.update_school(
            school_id=school_id,
            request=request,
            db=db,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update school: {str(e)}")


@router.get("/{school_id}/settings", response_model=SchoolSettingsResponse)
async def get_school_settings(
    school_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get school settings.

    User must belong to this school to view settings.
    """
    # Verify user belongs to this school
    if current_user.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this school",
        )

    try:
        response = await SchoolService.get_settings(
            school_id=school_id,
            db=db,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@router.put("/{school_id}/settings", response_model=SchoolSettingsResponse)
async def update_school_settings(
    school_id: uuid.UUID,
    request: SchoolSettingsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update school settings.

    Only school_admin users can update settings.
    """
    # Verify user belongs to this school
    if current_user.school_id != school_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this school",
        )

    # Check if current user is a school admin
    if current_user.role != "school_admin":
        raise HTTPException(
            status_code=403,
            detail="Only school administrators can update school settings",
        )

    try:
        response = await SchoolService.update_settings(
            school_id=school_id,
            request=request,
            db=db,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
