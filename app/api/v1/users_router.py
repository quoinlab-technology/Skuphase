"""User and staff management API routes."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.schemas.auth import CurrentUser
from app.schemas.user import (
    UserInviteRequest,
    UserUpdateRequest,
    UserStatusUpdateRequest,
    UserDetailResponse,
    UserListResponse,
    InviteResponse,
    PendingInviteListResponse,
    UserRemovalResponse,
)
from app.services.user_service import UserService

router = APIRouter()


def require_school_admin(current_user: CurrentUser):
    if current_user.role != "school_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school administrators are authorized to perform this operation.",
        )


@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    request: UserInviteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Invite a new teacher or staff member to the school.
    """
    require_school_admin(current_user)
    try:
        return await UserService.invite_user(
            request=request,
            school_id=current_user.school_id,
            db=db,
            invited_by_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to invite user: {str(e)}")


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None, description="Filter by active/inactive status"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all staff and teachers registered in the current school workspace.
    """
    require_school_admin(current_user)
    try:
        return await UserService.list_users(
            school_id=current_user.school_id,
            db=db,
            skip=skip,
            limit=limit,
            is_active=is_active,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list users: {str(e)}")


@router.get("/invites/pending", response_model=PendingInviteListResponse)
async def list_pending_invites(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all pending staff invitations awaiting activation.
    """
    require_school_admin(current_user)
    try:
        return await UserService.list_pending_invites(
            school_id=current_user.school_id,
            db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list pending invites: {str(e)}")


@router.post("/invites/{user_id}/resend", response_model=InviteResponse)
async def resend_invite(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Resend or refresh an invitation link for a pending teacher.
    """
    require_school_admin(current_user)
    try:
        return await UserService.resend_invite(
            user_id=user_id,
            school_id=current_user.school_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to resend invite: {str(e)}")


@router.put("/{user_id}/status", response_model=UserDetailResponse)
async def update_user_status(
    user_id: uuid.UUID,
    request: UserStatusUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Activate or deactivate a teacher/staff member account.
    """
    require_school_admin(current_user)
    if current_user.user_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own administrator account.")

    try:
        return await UserService.update_user_status(
            user_id=user_id,
            school_id=current_user.school_id,
            request=request,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update user status: {str(e)}")


@router.put("/{user_id}/role", response_model=UserDetailResponse)
async def update_user_role(
    user_id: uuid.UUID,
    request: UserUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update a staff member's role (e.g. teacher, auditor, school_admin).
    """
    require_school_admin(current_user)
    if current_user.user_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role.")

    try:
        return await UserService.update_user_role(
            user_id=user_id,
            school_id=current_user.school_id,
            request=request,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update user role: {str(e)}")


@router.delete("/{user_id}", response_model=UserRemovalResponse)
async def remove_user(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Remove a staff member from the school organization.
    """
    require_school_admin(current_user)
    if current_user.user_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove yourself from the school.")

    try:
        return await UserService.remove_user(
            user_id=user_id,
            school_id=current_user.school_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to remove user: {str(e)}")
