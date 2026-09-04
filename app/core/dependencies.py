"""Dependency injection utilities."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import verify_token
from app.schemas.auth import CurrentUser
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

security = HTTPBearer()


def _token_predates_credential_change(payload: dict, user) -> bool:
    """True when the JWT was issued before the user's last credential change."""
    valid_after = getattr(user, "token_valid_after", None)
    if not valid_after:
        return False
    issued_at = payload.get("iat")
    if not issued_at:
        return True
    if isinstance(issued_at, (int, float)):
        return datetime.fromtimestamp(issued_at, tz=timezone.utc) < valid_after
    try:
        issued_dt = datetime.fromisoformat(str(issued_at))
        if issued_dt.tzinfo is None:
            issued_dt = issued_dt.replace(tzinfo=timezone.utc)
        return issued_dt < valid_after
    except ValueError:
        return True


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """
    Get current authenticated user from JWT access token.
    """
    try:
        payload = verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Expected access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("user_id")
        school_id = payload.get("school_id")

        if not user_id or not school_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await AuthService.get_user_by_id(UUID(user_id), db)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        if _token_predates_credential_change(payload, user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked by credential change. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(
            user_id=user.id,
            school_id=user.school_id,
            email=user.email,
            role=user.role,
            account_type=getattr(user, "account_type", "school_staff"),
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """
    Get current authenticated user from a refresh JWT token.
    """
    try:
        payload = verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Expected refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("user_id")
        school_id = payload.get("school_id")

        if not user_id or not school_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await AuthService.get_user_by_id(UUID(user_id), db)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        if _token_predates_credential_change(payload, user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked by credential change. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if payload.get("gen", 1) != (getattr(user, "token_generation", 1) or 1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked by logout. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(
            user_id=user.id,
            school_id=user.school_id,
            email=user.email,
            role=user.role,
            account_type=getattr(user, "account_type", "school_staff"),
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
