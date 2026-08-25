"""User management schemas."""

from uuid import UUID
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserInviteRequest(BaseModel):
    """Request to invite a user to the school."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(
        ...,
        pattern="^(teacher|school_admin|auditor)$",
    )


class UserUpdateRequest(BaseModel):
    """Request to update a user's role."""
    role: str = Field(..., pattern="^(teacher|school_admin|auditor)$")


class UserStatusUpdateRequest(BaseModel):
    """Request to activate or deactivate a user."""
    is_active: bool


class UserDetailResponse(BaseModel):
    """Detailed user response."""
    user_id: UUID
    full_name: str
    email: str
    role: str
    account_type: str = "school_staff"
    is_active: bool
    is_verified: bool = False
    last_login: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """List of users response."""
    total: int
    users: List[UserDetailResponse]


class InviteResponse(BaseModel):
    """Response for user invitation."""
    message: str
    user_email: str
    role: str
    invitation_sent: bool
    invite_token: Optional[str] = None


class PendingInviteResponse(BaseModel):
    """Details of a pending staff invitation."""
    user_id: UUID
    email: str
    full_name: str
    role: str
    invited_at: datetime
    is_accepted: bool = False


class PendingInviteListResponse(BaseModel):
    """List of pending invitations."""
    total: int
    invites: List[PendingInviteResponse]


class UserRemovalResponse(BaseModel):
    """Response for user removal."""
    message: str
    user_id: UUID
    removed: bool
