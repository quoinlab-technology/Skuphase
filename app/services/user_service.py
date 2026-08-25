"""User service module for school staff and invitation management."""

import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.user import (
    UserInviteRequest,
    UserUpdateRequest,
    UserStatusUpdateRequest,
    UserDetailResponse,
    UserListResponse,
    InviteResponse,
    PendingInviteResponse,
    PendingInviteListResponse,
    UserRemovalResponse,
)
from app.core.security import hash_password


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserService:
    """Service for user and staff management."""

    @staticmethod
    async def invite_user(
        request: UserInviteRequest,
        school_id: uuid.UUID,
        db: AsyncSession,
        invited_by_id: uuid.UUID,
    ) -> InviteResponse:
        """Invite a new teacher/staff to the school."""
        try:
            # Check existing user
            existing_user = await db.execute(
                select(User).filter(User.email == request.email)
            )
            user_obj = existing_user.scalar_one_or_none()
            if user_obj:
                if user_obj.school_id == school_id:
                    raise ValueError(f"User with email {request.email} already belongs to this school")
                else:
                    raise ValueError(f"User with email {request.email} already has an account")

            invite_token = secrets.token_urlsafe(32)
            user = User(
                id=uuid.uuid4(),
                school_id=school_id,
                email=request.email,
                full_name=request.full_name,
                hashed_password=hash_password(secrets.token_urlsafe(16)),  # Temporary placeholder
                role=request.role,
                account_type="school_staff",
                is_active=False,  # Inactive until invitation is accepted
                is_verified=False,
                verification_token=invite_token,
                verification_token_expires_at=utc_now() + timedelta(days=7),
                invited_by_id=invited_by_id,
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

            return InviteResponse(
                message=f"Invitation generated for {user.email}.",
                user_email=user.email,
                role=user.role,
                invitation_sent=True,
                invite_token=invite_token,
            )

        except IntegrityError as e:
            await db.rollback()
            raise ValueError(f"Database error: {str(e)}")
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def list_users(
        school_id: uuid.UUID,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> UserListResponse:
        """Get all users in a school with optional status filtering."""
        conditions = [User.school_id == school_id]
        if is_active is not None:
            conditions.append(User.is_active == is_active)

        count_result = await db.execute(
            select(func.count()).select_from(User).filter(and_(*conditions))
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(User)
            .filter(and_(*conditions))
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        users = result.scalars().all()

        user_details = [
            UserDetailResponse(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=user.role,
                account_type=user.account_type,
                is_active=user.is_active,
                is_verified=user.is_verified,
                last_login=user.last_login,
                created_at=user.created_at,
            )
            for user in users
        ]

        return UserListResponse(
            total=total,
            users=user_details,
        )

    @staticmethod
    async def list_pending_invites(
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> PendingInviteListResponse:
        """Get all pending (unaccepted) staff invitations for the school."""
        stmt = (
            select(User)
            .where(
                and_(
                    User.school_id == school_id,
                    User.invitation_accepted_at.is_(None),
                    User.verification_token.is_not(None),
                )
            )
            .order_by(User.created_at.desc())
        )
        result = await db.execute(stmt)
        pending_users = result.scalars().all()

        invites = [
            PendingInviteResponse(
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                invited_at=u.created_at,
                is_accepted=False,
            )
            for u in pending_users
        ]
        return PendingInviteListResponse(total=len(invites), invites=invites)

    @staticmethod
    async def resend_invite(
        user_id: uuid.UUID,
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> InviteResponse:
        """Regenerate invitation token for pending staff."""
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.school_id == school_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found in this school")

        if user.invitation_accepted_at:
            raise ValueError("User has already accepted the invitation and activated their account")

        new_token = secrets.token_urlsafe(32)
        user.verification_token = new_token
        user.verification_token_expires_at = utc_now() + timedelta(days=7)
        await db.commit()

        return InviteResponse(
            message=f"Invitation link refreshed for {user.email}.",
            user_email=user.email,
            role=user.role,
            invitation_sent=True,
            invite_token=new_token,
        )

    @staticmethod
    async def update_user_status(
        user_id: uuid.UUID,
        school_id: uuid.UUID,
        request: UserStatusUpdateRequest,
        db: AsyncSession,
    ) -> UserDetailResponse:
        """Activate or deactivate a user account."""
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.school_id == school_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found in this school")

        user.is_active = request.is_active
        await db.commit()

        return UserDetailResponse(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            account_type=user.account_type,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            created_at=user.created_at,
        )

    @staticmethod
    async def update_user_role(
        user_id: uuid.UUID,
        school_id: uuid.UUID,
        request: UserUpdateRequest,
        db: AsyncSession,
    ) -> UserDetailResponse:
        """Update a user's role within a school."""
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.school_id == school_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found in school {school_id}")

        user.role = request.role
        await db.commit()

        return UserDetailResponse(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            account_type=user.account_type,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            created_at=user.created_at,
        )

    @staticmethod
    async def remove_user(
        user_id: uuid.UUID,
        school_id: uuid.UUID,
        db: AsyncSession,
    ) -> UserRemovalResponse:
        """Remove a user from a school."""
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.school_id == school_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found in school {school_id}")

        if user.role == "school_admin":
            admin_count = await db.execute(
                select(func.count()).select_from(User).where(
                    and_(
                        User.school_id == school_id,
                        User.role == "school_admin",
                    )
                )
            )
            if (admin_count.scalar() or 0) <= 1:
                raise ValueError("Cannot remove the last school administrator")

        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()

        return UserRemovalResponse(
            message=f"User {user.email} removed from school successfully.",
            user_id=user_id,
            removed=True,
        )
