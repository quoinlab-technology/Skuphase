"""Authentication schemas for request/response validation."""

from uuid import UUID
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# Password validator helper
def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters')
    if not any(c.isupper() for c in v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not any(c.islower() for c in v):
        raise ValueError('Password must contain at least one lowercase letter')
    if not any(c.isdigit() for c in v):
        raise ValueError('Password must contain at least one digit')
    return v


# Registration Schemas
class AdminUserRegistration(BaseModel):
    """Admin user registration within school context."""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)


class SchoolRegistrationRequest(BaseModel):
    """School onboarding request with admin user creation."""
    school_name: str = Field(..., min_length=3, max_length=100)
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    plan_id: Optional[UUID] = None
    admin_user: AdminUserRegistration


class IndividualTeacherRegistrationRequest(BaseModel):
    """Independent teacher / tutor registration (no formal school required)."""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    phone_number: Optional[str] = None
    workspace_name: Optional[str] = None  # e.g., "Musa Tutorial Center" or default to "[Name]'s Workspace"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)


class UserResponse(BaseModel):
    """User response model."""
    user_id: UUID
    full_name: str
    email: str
    role: str
    account_type: str = "school_staff"
    is_active: bool
    is_verified: bool = False
    created_at: datetime
    # School branding — populated at login for school users so the frontend
    # session user dict carries these without an extra round-trip.
    school_id: Optional[UUID] = None
    school_name: Optional[str] = None
    school_address: Optional[str] = None
    school_logo_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class SubscriptionResponse(BaseModel):
    """Subscription response model."""
    plan_id: Optional[UUID] = None
    plan_name: Optional[str] = None
    status: str
    start_date: datetime
    end_date: datetime


class NotificationPrefs(BaseModel):
    """Per-user notification preferences (audit2 Phase 2, Settings → Notifications).

    Stored as a JSON dict on User.notification_prefs; missing keys fall back
    to these defaults, which mirror the prototype (Settings.png–Settings6.png).
    """
    exam_generation_completed: bool = True
    new_audit_comments: bool = True
    proposal_status_changes: bool = True
    document_processing_done: bool = False
    user_joins_school: bool = False
    preflight_check_failed: bool = True


class NotificationPrefsResponse(BaseModel):
    """Envelope for GET/PUT /auth/me/preferences."""
    message: str
    preferences: NotificationPrefs

    
    model_config = ConfigDict(from_attributes=True)


class SchoolRegistrationResponse(BaseModel):
    """Response for successful school registration."""
    school_id: UUID
    school_name: str
    admin_user: UserResponse
    subscription: Optional[SubscriptionResponse] = None
    message: str


class IndividualRegistrationResponse(BaseModel):
    """Response for individual teacher registration."""
    user_id: UUID
    school_id: UUID  # Personal workspace ID
    workspace_name: str
    user: UserResponse
    message: str


# Login Schemas
class UserLogin(BaseModel):
    """Standard email/password login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: Optional[UserResponse] = None


class TokenRefreshRequest(BaseModel):
    """Explicit refresh token payload."""
    refresh_token: str


class GoogleOAuthRequest(BaseModel):
    """Google OAuth callback request."""
    code: str
    redirect_uri: Optional[str] = None


# Password Reset Schemas
class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset via email."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Submit new password with reset token."""
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Authenticated change password request."""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)


# Email Verification Schemas
class EmailVerificationRequest(BaseModel):
    """Verify email with token."""
    token: str


class ResendVerificationRequest(BaseModel):
    """Resend email verification token."""
    email: EmailStr


# Staff Invitation Acceptance
class AcceptInviteRequest(BaseModel):
    """Accept staff invitation and configure account password."""
    token: str
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        return validate_password_strength(v)


# Current User Dependency Response
class CurrentUser(BaseModel):
    """Current authenticated user context."""
    user_id: UUID
    school_id: UUID
    email: str
    role: str
    account_type: str = "school_staff"
    full_name: str
    is_active: bool
    is_verified: bool = False
