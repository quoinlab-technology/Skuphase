"""Authentication and identity API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user
from app.core.rate_limit import (
    is_locked_out as _login_locked_out,
    record_failure as _login_failure,
    record_success as _login_success,
)
from app.services.auth_service import AuthService
from app.schemas.auth import (
    SchoolRegistrationRequest,
    SchoolRegistrationResponse,
    IndividualTeacherRegistrationRequest,
    IndividualRegistrationResponse,
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    CurrentUser,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    EmailVerificationRequest,
    ResendVerificationRequest,
    AcceptInviteRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=SchoolRegistrationResponse, status_code=201)
async def register_school(
    request: SchoolRegistrationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a new school organization with an administrator account.
    """
    try:
        return await AuthService.register_school(request, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"School registration error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")


@router.post("/register-individual", response_model=IndividualRegistrationResponse, status_code=201)
async def register_individual_teacher(
    request: IndividualTeacherRegistrationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register an independent teacher/tutor with their own personal workspace.
    """
    try:
        return await AuthService.register_individual_teacher(request, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Individual teacher registration error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLogin,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Authenticate user and return JWT access and refresh tokens.
    """
    client_ip = http_request.client.host if http_request.client else "unknown"
    if _login_locked_out(request.email, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
        )
    try:
        result = await AuthService.login(request.email, request.password, db)
        _login_success(request.email, client_ip)
        return result
    except ValueError as e:
        _login_failure(request.email, client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Exchange a valid refresh token for a fresh access token pair.
    """
    try:
        return await AuthService.refresh_access_token(request.refresh_token, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token refresh failed")


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initiate password reset flow for user email.
    """
    try:
        return await AuthService.request_password_reset(request.email, db)
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Request failed")


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Reset password using valid reset token.
    """
    try:
        return await AuthService.reset_password(request.token, request.new_password, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password reset failed")


@router.post("/verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Verify user email address using verification token.
    """
    try:
        return await AuthService.verify_email(request.token, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Email verification failed")


@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Resend verification token to user email.
    """
    try:
        return await AuthService.resend_verification(request.email, db)
    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Request failed")


@router.post("/accept-invite")
async def accept_invite(
    request: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Complete teacher onboarding by accepting school invitation and setting account password.
    """
    try:
        return await AuthService.accept_invitation(
            token=request.token,
            password=request.password,
            full_name=request.full_name,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Accept invite error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invitation acceptance failed")


@router.get("/me", response_model=CurrentUser)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get profile information of currently authenticated user.
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Logout user (client should discard stored tokens).
    """
    logger.info(f"User '{current_user.email}' logged out")
    return {"message": "Logged out successfully"}
