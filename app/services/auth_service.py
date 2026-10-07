"""Authentication service for school and individual teacher lifecycle."""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import School, User, Plan, SchoolSubscription, SchoolSettings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from app.config.settings import get_settings
from app.services.mailer import send_email
from app.utils.email_templates import (
    build_invite_email,
    build_reset_password_email,
    build_verify_email,
)
from app.schemas.auth import (
    SchoolRegistrationRequest,
    SchoolRegistrationResponse,
    IndividualTeacherRegistrationRequest,
    IndividualRegistrationResponse,
    UserResponse,
    SubscriptionResponse,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    """Authentication and identity service."""

    @staticmethod
    async def _send_registration_verification(email: str, token: str) -> bool:
        """Send the post-registration verification link without failing signup."""
        base_url = get_settings().app_base_url.rstrip("/")
        verify_url = f"{base_url}/verify-email?token={token}"
        try:
            delivered = await send_email(
                to=email,
                subject="Verify your SkuPhase email",
                html=build_verify_email(verify_url),
            )
            if not delivered:
                logger.warning("Registration verification email unavailable for %s", email)
            return delivered
        except Exception:
            logger.exception("Registration verification email failed for %s", email)
            return False

    @staticmethod
    async def get_user_by_id(user_id: UUID, db: AsyncSession) -> Optional[User]:
        """Fetch an active user by ID (used by auth dependencies).

        Raises ValueError when the user does not exist so callers can map it
        to a 401 without leaking whether the account exists.
        """
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

    @staticmethod
    async def register_school(
        request: SchoolRegistrationRequest,
        db: AsyncSession,
    ) -> SchoolRegistrationResponse:
        """Register a new school organization with admin user."""
        password = request.admin_user.password
        if len(password.encode('utf-8')) > 72:
            password = password[:72]

        # Check existing school
        result = await db.execute(select(School).filter(School.name == request.school_name))
        if result.scalar_one_or_none():
            raise ValueError(f"School with name '{request.school_name}' already exists")

        # Check existing school contact email
        email_check = await db.execute(select(School).filter(School.contact_email == request.contact_email))
        if email_check.scalar_one_or_none():
            raise ValueError(f"A school with contact email '{request.contact_email}' already exists. Please sign in or use a different email.")

        # Check existing user
        result = await db.execute(select(User).filter(User.email == request.admin_user.email))
        if result.scalar_one_or_none():
            raise ValueError(f"An account with email '{request.admin_user.email}' already exists. Please sign in instead.")

        plan_id = request.plan_id
        plan_obj = None
        if plan_id:
            plan = await db.execute(select(Plan).filter(Plan.id == plan_id))
            plan_obj = plan.scalar_one_or_none()

        try:
            school = School(
                name=request.school_name,
                contact_email=request.contact_email,
                contact_phone=request.contact_phone,
                address=request.address,
                is_personal_workspace=False,
            )
            db.add(school)
            await db.flush()

            verification_token = secrets.token_urlsafe(32)
            user = User(
                school_id=school.id,
                email=request.admin_user.email,
                hashed_password=hash_password(password),
                full_name=request.admin_user.full_name,
                role="school_admin",
                account_type="school_staff",
                is_active=True,
                is_verified=False,
                verification_token=verification_token,
                verification_token_expires_at=utc_now() + timedelta(days=3),
            )
            db.add(user)

            settings = SchoolSettings(
                school_id=school.id,
                logo_url=None,
                primary_color="#0066CC",
                secondary_color="#00CC99",
                primary_llm_provider="grok",
                fallback_llm_provider="openrouter",
                exam_format="nigerian",
            )
            db.add(settings)

            # Trial subscription
            sub = SchoolSubscription(
                school_id=school.id,
                plan_id=plan_obj.id if plan_obj else None,
                status="trial",
                start_date=utc_now(),
                end_date=utc_now() + timedelta(days=30),
                billing_cycle="monthly",
            )
            db.add(sub)

            await db.commit()
            logger.info(f"School '{request.school_name}' registered successfully")
            await AuthService._send_registration_verification(user.email, verification_token)

            return SchoolRegistrationResponse(
                school_id=school.id,
                school_name=school.name,
                admin_user=UserResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    role=user.role,
                    account_type=user.account_type,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at,
                ),
                subscription=SubscriptionResponse(
                    plan_id=plan_obj.id if plan_obj else None,
                    plan_name=plan_obj.name if plan_obj else "Trial Plan",
                    status=sub.status,
                    start_date=sub.start_date,
                    end_date=sub.end_date,
                ) if sub else None,
                message="School registered successfully. Verification token generated.",
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Error registering school: {str(e)}")
            raise

    @staticmethod
    async def register_individual_teacher(
        request: IndividualTeacherRegistrationRequest,
        db: AsyncSession,
    ) -> IndividualRegistrationResponse:
        """Register an independent teacher/tutor with a dedicated personal workspace."""
        password = request.password
        if len(password.encode('utf-8')) > 72:
            password = password[:72]

        # Check existing user
        result = await db.execute(select(User).filter(User.email == request.email))
        if result.scalar_one_or_none():
            raise ValueError(f"An account with email '{request.email}' already exists. Please sign in instead.")

        # Check existing school contact email
        school_email_check = await db.execute(select(School).filter(School.contact_email == request.email))
        if school_email_check.scalar_one_or_none():
            raise ValueError(f"A workspace or school with email '{request.email}' already exists. Please sign in instead.")

        workspace_name = request.workspace_name or f"{request.full_name}'s Workspace"
        # Ensure unique workspace name
        base_name = workspace_name
        counter = 1
        while True:
            existing_school = await db.execute(select(School).filter(School.name == workspace_name))
            if not existing_school.scalar_one_or_none():
                break
            workspace_name = f"{base_name} ({counter})"
            counter += 1

        try:
            school = School(
                name=workspace_name,
                contact_email=request.email,
                contact_phone=request.phone_number,
                is_personal_workspace=True,
            )
            db.add(school)
            await db.flush()

            verification_token = secrets.token_urlsafe(32)
            user = User(
                school_id=school.id,
                email=request.email,
                hashed_password=hash_password(password),
                full_name=request.full_name,
                role="teacher",
                account_type="individual_teacher",
                is_active=True,
                is_verified=False,
                verification_token=verification_token,
                verification_token_expires_at=utc_now() + timedelta(days=3),
            )
            db.add(user)

            settings = SchoolSettings(
                school_id=school.id,
                logo_url=None,
                primary_color="#4F46E5",
                secondary_color="#10B981",
                primary_llm_provider="grok",
                fallback_llm_provider="openrouter",
                exam_format="nigerian",
            )
            db.add(settings)

            # Free individual tier subscription
            sub = SchoolSubscription(
                school_id=school.id,
                plan_id=None,
                status="active",
                start_date=utc_now(),
                end_date=utc_now() + timedelta(days=365),
                billing_cycle="yearly",
            )
            db.add(sub)

            await db.commit()
            logger.info(f"Individual teacher '{request.email}' registered with personal workspace '{workspace_name}'")
            await AuthService._send_registration_verification(user.email, verification_token)

            return IndividualRegistrationResponse(
                user_id=user.id,
                school_id=school.id,
                workspace_name=school.name,
                user=UserResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    role=user.role,
                    account_type=user.account_type,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at,
                ),
                message="Account created successfully. Verification token generated.",
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Error registering individual teacher: {str(e)}")
            raise

    @staticmethod
    async def login(
        email: str,
        password: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Authenticate user and issue access and refresh tokens."""
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Your account is deactivated. Please contact support or your school administrator.")

        if not user.is_verified:
            raise ValueError("Please verify your email address before signing in. Check your inbox or request a new verification email.")

        user.last_login = utc_now()
        await db.commit()

        access_token = create_access_token({
            "sub": user.email,
            "user_id": str(user.id),
            "school_id": str(user.school_id),
            "email": user.email,
            "role": user.role,
            "account_type": user.account_type,
            "full_name": user.full_name,
            "token_type": "access",
        })

        refresh_token = create_access_token({
            "sub": user.email,
            "user_id": str(user.id),
            "school_id": str(user.school_id),
            "token_type": "refresh",
            "gen": user.token_generation or 1,
        }, expires_delta=timedelta(days=get_settings().refresh_token_expire_days))

        # Fetch school branding to include in the session user dict.
        # This avoids a separate round-trip from the frontend on every page load.
        _school_name = None
        _school_address = None
        _school_logo_url = None
        try:
            school_res = await db.execute(select(School).where(School.id == user.school_id))
            school_obj = school_res.scalar_one_or_none()
            if school_obj:
                _school_name = school_obj.name
                _school_address = school_obj.address
            settings_res = await db.execute(
                select(SchoolSettings).where(SchoolSettings.school_id == user.school_id)
            )
            settings_obj = settings_res.scalar_one_or_none()
            if settings_obj:
                _school_logo_url = settings_obj.logo_url
        except Exception as _branding_err:
            logger.warning("Could not fetch school branding at login: %s", _branding_err)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": get_settings().access_token_expire_minutes * 60,
            "user": UserResponse(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=user.role,
                account_type=user.account_type,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                school_id=user.school_id,
                school_name=_school_name,
                school_address=_school_address,
                school_logo_url=_school_logo_url,
            ),
        }


    @staticmethod
    async def refresh_access_token(refresh_token_str: str, db: AsyncSession) -> Dict[str, Any]:
        """Validate refresh token and issue a fresh access token pair."""
        try:
            payload = decode_token(refresh_token_str)
            if not payload or payload.get("token_type") != "refresh":
                raise ValueError("Invalid token type. Expected refresh token.")
            
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid refresh token claims.")

            result = await db.execute(select(User).filter(User.id == UUID(user_id)))
            user = result.scalar_one_or_none()
            if not user or not user.is_active:
                raise ValueError("User account is inactive or not found.")

            # Revocation check (audit F-06): logout bumps token_generation,
            # instantly invalidating all outstanding refresh tokens.
            current_gen = getattr(user, "token_generation", 1) or 1
            if payload.get("gen", 1) != current_gen:
                raise ValueError("Refresh token has been revoked. Please log in again.")

            new_access_token = create_access_token({
                "sub": user.email,
                "user_id": str(user.id),
                "school_id": str(user.school_id),
                "email": user.email,
                "role": user.role,
                "account_type": user.account_type,
                "full_name": user.full_name,
                "token_type": "access",
            })

            new_refresh_token = create_access_token({
                "sub": user.email,
                "user_id": str(user.id),
                "school_id": str(user.school_id),
                "token_type": "refresh",
                "gen": current_gen,
            }, expires_delta=timedelta(days=get_settings().refresh_token_expire_days))

            # Refresh school branding alongside the new tokens
            _school_name = None
            _school_address = None
            _school_logo_url = None
            try:
                school_res = await db.execute(select(School).where(School.id == user.school_id))
                school_obj = school_res.scalar_one_or_none()
                if school_obj:
                    _school_name = school_obj.name
                    _school_address = school_obj.address
                settings_res = await db.execute(
                    select(SchoolSettings).where(SchoolSettings.school_id == user.school_id)
                )
                settings_obj = settings_res.scalar_one_or_none()
                if settings_obj:
                    _school_logo_url = settings_obj.logo_url
            except Exception as _branding_err:
                logger.warning("Could not fetch school branding during token refresh: %s", _branding_err)

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": get_settings().access_token_expire_minutes * 60,
                "user": UserResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    role=user.role,
                    account_type=getattr(user, "account_type", "school_staff"),
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at,
                    school_id=user.school_id,
                    school_name=_school_name,
                    school_address=_school_address,
                    school_logo_url=_school_logo_url,
                ),
            }
        except Exception as e:
            raise ValueError(f"Token refresh failed: {str(e)}")


    @staticmethod
    async def logout(user_id: UUID, db: AsyncSession) -> None:
        """Bump the user's refresh-token generation, revoking outstanding
        refresh tokens immediately (access tokens expire naturally)."""
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return
        user.token_generation = (user.token_generation or 1) + 1
        await db.commit()

    @staticmethod
    async def request_password_reset(email: str, db: AsyncSession) -> Dict[str, str]:
        """Generate a password reset token for user."""
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            # Prevent email enumeration: return generic success message
            return {"message": "If this email is registered, password reset instructions have been sent."}

        reset_token = secrets.token_urlsafe(32)
        user.reset_password_token = reset_token
        user.reset_password_token_expires_at = utc_now() + timedelta(hours=1)
        await db.commit()

        logger.info(f"Password reset token created for user {email}")

        base_url = get_settings().app_base_url.rstrip("/")
        reset_url = f"{base_url}/reset-password?token={reset_token}"
        delivered = await send_email(
            to=email,
            subject="Reset your SkuPhase password",
            html=build_reset_password_email(reset_url),
        )
        if not delivered:
            logger.warning(
                "Password reset email could not be delivered to %s "
                "(token persisted; expires in 1 hour)",
                email,
            )

        # SECURITY: the token is NEVER returned in the HTTP response.
        return {
            "message": "If this email is registered, password reset instructions have been sent."
        }

    @staticmethod
    async def reset_password(token: str, new_password: str, db: AsyncSession) -> Dict[str, str]:
        """Apply new password using valid reset token."""
        result = await db.execute(
            select(User).filter(User.reset_password_token == token)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Invalid or expired password reset token.")

        if user.reset_password_token_expires_at and user.reset_password_token_expires_at < utc_now():
            raise ValueError("Password reset token has expired. Please request a new one.")

        password = new_password
        if len(password.encode('utf-8')) > 72:
            password = password[:72]

        user.hashed_password = hash_password(password)
        user.reset_password_token = None
        user.reset_password_token_expires_at = None
        # Invalidate any JWTs issued before this credential change.
        if hasattr(user, "token_valid_after"):
            user.token_valid_after = utc_now()
        await db.commit()

        return {"message": "Password reset successfully. You can now login."}

    @staticmethod
    async def change_password(
        user_id: UUID,
        current_password: str,
        new_password: str,
        db: AsyncSession,
    ) -> Dict[str, str]:
        """Change password for an authenticated user."""
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect.")
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters.")
        pwd = new_password
        if len(pwd.encode('utf-8')) > 72:
            pwd = pwd[:72]
        user.hashed_password = hash_password(pwd)
        if hasattr(user, "token_valid_after"):
            user.token_valid_after = utc_now()
        await db.commit()
        return {"message": "Password changed successfully."}

    @staticmethod
    async def verify_email(token: str, db: AsyncSession) -> Dict[str, str]:
        """Verify user email address via token."""
        result = await db.execute(
            select(User).filter(User.verification_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("Invalid verification token.")

        if user.verification_token_expires_at and user.verification_token_expires_at < utc_now():
            raise ValueError("Verification token has expired. Please request a new verification email.")

        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        await db.commit()

        return {"message": "Email verified successfully."}

    @staticmethod
    async def resend_verification(email: str, db: AsyncSession) -> Dict[str, str]:
        """Resend email verification token."""
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return {"message": "If the account exists, a new verification link has been sent."}

        if user.is_verified:
            return {"message": "Email is already verified."}

        token = secrets.token_urlsafe(32)
        user.verification_token = token
        user.verification_token_expires_at = utc_now() + timedelta(days=3)
        await db.commit()

        base_url = get_settings().app_base_url.rstrip("/")
        verify_url = f"{base_url}/verify-email?token={token}"
        delivered = await send_email(
            to=email,
            subject="Verify your SkuPhase email",
            html=build_verify_email(verify_url),
        )
        if not delivered:
            logger.warning(
                "Verification email could not be delivered to %s "
                "(token persisted; expires in 3 days)",
                email,
            )

        # SECURITY: the token is NEVER returned in the HTTP response.
        return {"message": "A new verification link has been sent."}

    @staticmethod
    async def accept_invitation(
        token: str,
        password: str,
        full_name: Optional[str],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Complete onboarding for an invited staff teacher."""
        result = await db.execute(
            select(User).filter(User.verification_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("Invalid or expired invitation token.")

        pwd = password
        if len(pwd.encode('utf-8')) > 72:
            pwd = pwd[:72]

        user.hashed_password = hash_password(pwd)
        if full_name:
            user.full_name = full_name
        user.is_active = True
        user.is_verified = True
        user.invitation_accepted_at = utc_now()
        user.verification_token = None
        user.verification_token_expires_at = None
        # First credential set invalidates any tokens issued before activation.
        if hasattr(user, "token_valid_after"):
            user.token_valid_after = utc_now()
        await db.commit()

        return {
            "message": "Invitation accepted successfully. You may now log in.",
            "user_id": str(user.id),
            "email": user.email,
        }
