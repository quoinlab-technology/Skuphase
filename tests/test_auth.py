import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_user_from_refresh_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.school_id = uuid4()
        self.email = "admin@testschool.edu"
        self.role = "school_admin"
        self.full_name = "Test Admin"
        self.is_active = True
        self.is_verified = True
        self.account_type = "school_staff"


@pytest.mark.asyncio
async def test_refresh_dependency_accepts_refresh_token():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="refresh-token")
    db = AsyncMock()
    user = DummyUser()

    with patch("app.core.dependencies.verify_token") as mock_verify, patch(
        "app.core.dependencies.AuthService.get_user_by_id", new_callable=AsyncMock
    ) as mock_get_user:
        mock_verify.return_value = {
            "user_id": str(user.id),
            "school_id": str(user.school_id),
            "token_type": "refresh",
        }
        mock_get_user.return_value = user

        current = await get_current_user_from_refresh_token(credentials=credentials, db=db)

        assert current.user_id == user.id
        assert current.school_id == user.school_id
        assert current.email == user.email


@pytest.mark.asyncio
async def test_refresh_dependency_rejects_access_token():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")
    db = AsyncMock()

    with patch("app.core.dependencies.verify_token") as mock_verify:
        mock_verify.return_value = {
            "user_id": str(uuid4()),
            "school_id": str(uuid4()),
            "token_type": "access",
        }

        with pytest.raises(HTTPException) as exc:
            await get_current_user_from_refresh_token(credentials=credentials, db=db)

        assert exc.value.status_code == 401
