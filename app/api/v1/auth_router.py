"""Authentication and identity API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
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
    ChangePasswordRequest,
    EmailVerificationRequest,
    ResendVerificationRequest,
    AcceptInviteRequest,
    NotificationPrefs,
    NotificationPrefsResponse,
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
    except IntegrityError as e:
        await db.rollback()
        err_msg = str(e.orig if hasattr(e, "orig") else e).lower()
        if "schools_contact_email_key" in err_msg or "contact_email" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A school with contact email '{request.contact_email}' is already registered. Please sign in or use a different email.",
            )
        if "users_email_key" in err_msg or "email" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{request.admin_user.email}' already exists. Please sign in instead.",
            )
        if "schools_name_key" in err_msg or "name" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A school with name '{request.school_name}' already exists. Please choose a different school name.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed: an organization or user with these credentials already exists.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"School registration error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration failed: {str(e)}")


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
    except IntegrityError as e:
        await db.rollback()
        err_msg = str(e.orig if hasattr(e, "orig") else e).lower()
        if "email" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account or workspace with email '{request.email}' already exists. Please sign in instead.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed: an account with these credentials already exists.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Individual teacher registration error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration failed: {str(e)}")


def _client_ip(http_request: Request) -> str:
    """Resolve the client IP, preferring proxy headers (FastAPI Cloud/Render)."""
    forwarded_for = http_request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or "unknown"
    return http_request.client.host if http_request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLogin,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Authenticate user and return JWT access and refresh tokens.
    """
    client_ip = _client_ip(http_request)
    if await _login_locked_out(db, request.email, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
        )
    try:
        result = await AuthService.login(request.email, request.password, db)
        await _login_success(db, request.email, client_ip)
        return result
    except ValueError as e:
        await _login_failure(db, request.email, client_ip)
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


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Change password for authenticated user.
    """
    try:
        return await AuthService.change_password(
            user_id=current_user.user_id,
            current_password=request.old_password,
            new_password=request.new_password,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password change failed")


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


@router.get("/me/preferences", response_model=NotificationPrefsResponse)
async def get_notification_preferences(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get the current user's notification preferences. Unset keys fall back
    to NotificationPrefs defaults (audit2 Phase 2).
    """
    from app.models.user import User

    user = await db.get(User, current_user.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    stored = getattr(user, "notification_prefs", None) or {}
    prefs = NotificationPrefs(**{
        key: bool(stored[key]) for key in NotificationPrefs.model_fields if key in stored
    })
    return NotificationPrefsResponse(message="Preferences loaded", preferences=prefs)


@router.put("/me/preferences", response_model=NotificationPrefsResponse)
async def update_notification_preferences(
    prefs: NotificationPrefs,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Persist the current user's notification preferences (audit2 Phase 2).
    """
    from app.models.user import User

    user = await db.get(User, current_user.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.notification_prefs = prefs.model_dump()
    await db.commit()
    logger.info(f"Notification preferences updated for user '{current_user.email}'")
    return NotificationPrefsResponse(message="Preferences saved successfully", preferences=prefs)


@router.post("/logout")
async def logout(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Revoke outstanding refresh tokens (token-generation bump) and acknowledge
    logout. Clients must also discard stored tokens.
    """
    await AuthService.logout(current_user.user_id, db)
    logger.info(f"User '{current_user.email}' logged out")
    return {"message": "Logged out successfully"}
