from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.schools_router import update_school_settings
from app.schemas.school import SchoolSettingsUpdate
from app.services.school_service import SchoolService


@pytest.mark.asyncio
async def test_personal_owner_can_update_only_personal_document_branding(monkeypatch):
    school_id = uuid4()
    expected = object()
    update = AsyncMock(return_value=expected)
    monkeypatch.setattr(SchoolService, "update_settings", update)

    result = await update_school_settings(
        school_id,
        SchoolSettingsUpdate(
            personal_document_branding_enabled=True,
            document_display_name="Tutor Ada",
            logo_url="https://storage.example/logo.png",
        ),
        current_user=SimpleNamespace(
            school_id=school_id,
            role="teacher",
            account_type="individual_teacher",
        ),
        db=object(),
    )

    assert result is expected
    update.assert_awaited_once()


@pytest.mark.asyncio
async def test_personal_owner_cannot_update_school_wide_document_style(monkeypatch):
    school_id = uuid4()
    update = AsyncMock()
    monkeypatch.setattr(SchoolService, "update_settings", update)

    with pytest.raises(HTTPException) as raised:
        await update_school_settings(
            school_id,
            SchoolSettingsUpdate(document_style={"font_size": 12}),
            current_user=SimpleNamespace(
                school_id=school_id,
                role="teacher",
                account_type="individual_teacher",
            ),
            db=object(),
        )

    assert raised.value.status_code == 403
    update.assert_not_awaited()


@pytest.mark.asyncio
async def test_school_teacher_cannot_change_shared_document_branding(monkeypatch):
    school_id = uuid4()
    update = AsyncMock()
    monkeypatch.setattr(SchoolService, "update_settings", update)

    with pytest.raises(HTTPException) as raised:
        await update_school_settings(
            school_id,
            SchoolSettingsUpdate(document_display_name="Different School Name"),
            current_user=SimpleNamespace(
                school_id=school_id,
                role="teacher",
                account_type="school_staff",
            ),
            db=object(),
        )

    assert raised.value.status_code == 403
    update.assert_not_awaited()
