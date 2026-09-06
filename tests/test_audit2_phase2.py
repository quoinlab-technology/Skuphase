"""Audit2 Phase 2 regression tests (see AUDIT2_IMPLEMENTATION_PLAN.md §Phase 2).

Covers the Settings parity work:
- Tab rail now has 6 tabs (Notifications + API & Integrations added).
- Notifications tab renders 6 toggles seeded from GET /auth/me/preferences.
- POST ?tab=notifications persists prefs via PUT (works for individual
  teachers too — per-user setting, before the school-admin gate).
- API & Integrations renders the coming-soon stub with a support CTA.
"""

import re

import pytest
from starlette.testclient import TestClient

from app.main import app


class FakeResp:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload if payload is not None else {}

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class ApiStub:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    async def __call__(self, req, method, path, json=None, params=None):
        self.calls.append({"method": method, "path": path, "json": json})
        for m, prefix, resp in self.routes:
            if m == method and path.startswith(prefix):
                return resp
        return FakeResp(200, {})


@pytest.fixture
def client():
    return TestClient(app)


def _login(client, monkeypatch, role="school_admin", account_type="school_staff"):
    tokens = {
        "access_token": "at", "refresh_token": "rt", "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u1", "full_name": "Amina", "email": "a@b.com",
            "role": role, "account_type": account_type,
            "is_active": True, "is_verified": True,
        },
    }
    stub = ApiStub([("POST", "/auth/login", FakeResp(200, tokens))])
    monkeypatch.setattr("app.frontend.routes.auth.call_api", stub)
    r = client.post("/login", data={"email": "a@b.com", "password": "pw"})
    assert r.status_code in (200, 303)
    return stub


# ---------------------------------------------------------------------------
# Notifications tab: 6 toggles, seeded from saved prefs
# ---------------------------------------------------------------------------


def test_notifications_tab_renders_six_toggles(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr("app.frontend.routes.settings.call_api", _settings_stub())

    r = client.get("/app/settings?tab=notifications")
    assert r.status_code == 200
    body = r.text
    assert "Save Preferences" in body
    for key in ("exam_generation_completed", "new_audit_comments",
                "proposal_status_changes", "document_processing_done",
                "user_joins_school", "preflight_check_failed"):
        assert f'name="{key}"' in body, f"missing toggle: {key}"


def test_notifications_tab_seeds_from_saved_prefs(client, monkeypatch):
    _login(client, monkeypatch)
    saved = {"exam_generation_completed": False, "preflight_check_failed": False}
    monkeypatch.setattr(
        "app.frontend.routes.settings.call_api", _settings_stub(saved)
    )

    r = client.get("/app/settings?tab=notifications")
    assert r.status_code == 200
    body = r.text
    assert "checked" in body
    # The saved-False toggles must render unchecked (their defaults are True)
    for key, expected_on in saved.items():
        m = re.search(rf'<input[^>]*name="{key}"[^>]*>', body)
        assert m, f"toggle input not found for {key}"
        is_checked = "checked" in m.group(0)
        assert is_checked == expected_on, f"{key}: expected checked={expected_on}"

# ---------------------------------------------------------------------------
# POST ?tab=notifications: persists via PUT, individual teachers included
# ---------------------------------------------------------------------------


def test_save_notifications_puts_prefs_and_redirects(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("PUT", "/auth/me/preferences", FakeResp(200, {"preferences": {}}))])
    monkeypatch.setattr("app.frontend.routes.settings.call_api", stub)

    r = client.post(
        "/app/settings?tab=notifications",
        data={"exam_generation_completed": "1", "new_audit_comments": "1",
              "preflight_check_failed": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/app/settings?tab=notifications" in r.headers["location"]

    puts = [c for c in stub.calls if c["method"] == "PUT"]
    assert len(puts) == 1
    payload = puts[0]["json"]
    # unchecked boxes are absent from the form -> False
    assert payload == {
        "exam_generation_completed": True,
        "new_audit_comments": True,
        "proposal_status_changes": False,
        "document_processing_done": False,
        "user_joins_school": False,
        "preflight_check_failed": True,
    }


def test_individual_teacher_can_save_notifications(client, monkeypatch):
    _login(client, monkeypatch, role="individual_teacher",
           account_type="individual_teacher")
    stub = ApiStub([("PUT", "/auth/me/preferences", FakeResp(200, {"preferences": {}}))])
    monkeypatch.setattr("app.frontend.routes.settings.call_api", stub)

    r = client.post(
        "/app/settings?tab=notifications",
        data={"exam_generation_completed": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert any(c["method"] == "PUT" for c in stub.calls)


def test_save_notifications_failure_shows_flash(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("PUT", "/auth/me/preferences",
                     FakeResp(500, {"message": "Storage unavailable."}))])
    monkeypatch.setattr("app.frontend.routes.settings.call_api", stub)

    r = client.post("/app/settings?tab=notifications", data={})
    assert r.status_code == 200  # redirected, then page rendered with flash
    assert "Storage unavailable." in r.text


# ---------------------------------------------------------------------------
# API & Integrations stub
# ---------------------------------------------------------------------------


def test_integrations_tab_renders_coming_soon_stub(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr("app.frontend.routes.settings.call_api", _settings_stub())

    r = client.get("/app/settings?tab=integrations")
    assert r.status_code == 200
    body = r.text
    assert "API access is coming soon" in body
    assert "Contact Support" in body
    assert 'href="/about"' in body


def _settings_stub(prefs: dict | None = None):
    return ApiStub([("GET", "/auth/me/preferences",
                     FakeResp(200, {"preferences": prefs or {}}))])


# ---------------------------------------------------------------------------
# Tab rail: 6 tabs incl. Notifications and API & Integrations
# ---------------------------------------------------------------------------


def test_settings_tab_rail_has_six_tabs(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr("app.frontend.routes.settings.call_api", _settings_stub())

    r = client.get("/app/settings")
    assert r.status_code == 200
    body = r.text
    for label in ("School Profile", "My Account", "Notifications",
                  "Integrations", "Academic Policy", "Security"):
        assert label in body, f"missing settings tab: {label}"
    assert "tab=notifications" in body
    assert "tab=integrations" in body
