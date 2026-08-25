"""Schemas package."""

from app.schemas.auth import (
    AdminUserRegistration,
    SchoolRegistrationRequest,
    UserResponse,
    SubscriptionResponse,
    SchoolRegistrationResponse,
    UserLogin,
    TokenResponse,
    GoogleOAuthRequest,
    CurrentUser,
)
from app.schemas.user import (
    UserInviteRequest,
    UserUpdateRequest,
    UserDetailResponse,
    UserListResponse,
    InviteResponse,
    UserRemovalResponse,
)
from app.schemas.school import (
    SchoolSettingsUpdate,
    SchoolSettingsResponse,
    SchoolDetailResponse,
    SchoolUpdateRequest,
)

__all__ = [
    # Auth schemas
    "AdminUserRegistration",
    "SchoolRegistrationRequest",
    "UserResponse",
    "SubscriptionResponse",
    "SchoolRegistrationResponse",
    "UserLogin",
    "TokenResponse",
    "GoogleOAuthRequest",
    "CurrentUser",
    # User schemas
    "UserInviteRequest",
    "UserUpdateRequest",
    "UserDetailResponse",
    "UserListResponse",
    "InviteResponse",
    "UserRemovalResponse",
    # School schemas
    "SchoolSettingsUpdate",
    "SchoolSettingsResponse",
    "SchoolDetailResponse",
    "SchoolUpdateRequest",
]
    