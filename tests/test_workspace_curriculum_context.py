from types import SimpleNamespace

import pytest

from app.frontend import curriculum_context
from app.frontend.routes.exams import _reconcile_wizard_curriculum_scope


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_workspace_curriculum_uses_configured_board(monkeypatch):
    async def fake_call_api(*args, **kwargs):
        return FakeResponse(200, {"curriculum_board": "Cambridge"})

    monkeypatch.setattr(curriculum_context, "call_api", fake_call_api)
    req = SimpleNamespace(session={"user": {"school_id": "school-1"}})

    assert await curriculum_context.workspace_curriculum_board(req) == "Cambridge"


@pytest.mark.asyncio
async def test_workspace_curriculum_legacy_settings_missing_defaults_to_nerdc(monkeypatch):
    async def fake_call_api(*args, **kwargs):
        return FakeResponse(404, {"detail": "Settings not found"})

    monkeypatch.setattr(curriculum_context, "call_api", fake_call_api)
    req = SimpleNamespace(session={"user": {"school_id": "school-1"}})

    assert await curriculum_context.workspace_curriculum_board(req) == "NERDC"


@pytest.mark.asyncio
async def test_workspace_curriculum_does_not_silently_fallback_on_server_error(monkeypatch):
    async def fake_call_api(*args, **kwargs):
        return FakeResponse(503, {"detail": "settings service unavailable"})

    monkeypatch.setattr(curriculum_context, "call_api", fake_call_api)
    req = SimpleNamespace(session={"user": {"school_id": "school-1"}})

    with pytest.raises(RuntimeError, match="workspace curriculum setting"):
        await curriculum_context.workspace_curriculum_board(req)


def test_wizard_source_change_resets_stale_scope_and_week_selection():
    request = SimpleNamespace(
        state=SimpleNamespace(
            curriculum_grade_options=["Year 4", "Year 5"],
            curriculum_subject_options=["English", "Mathematics"],
        )
    )
    wizard = {
        "curriculum_board": "NERDC",
        "grade_level": "Primary 4",
        "subject": "Basic Science",
        "term": "First Term",
        "selected_weeks": ["2", "3"],
        "selected_documents": ["scheme-1"],
        "curriculum_weeks": [{"week_number": 2}],
        "curriculum_scope": "old-scope",
    }

    _reconcile_wizard_curriculum_scope(request, wizard, "Cambridge")

    assert wizard["curriculum_board"] == "Cambridge"
    assert wizard["grade_level"] == "Year 4"
    assert wizard["subject"] == "English"
    assert wizard["selected_weeks"] == []
    assert wizard["curriculum_weeks"] == []
    assert "selected_documents" not in wizard
    assert "curriculum_scope" not in wizard
