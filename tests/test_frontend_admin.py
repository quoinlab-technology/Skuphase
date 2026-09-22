"""Frontend Admin module tests: staff, settings, ops (FRONTEND_SPEC sec 6.11-6.13)."""

import pytest
from starlette.testclient import TestClient

from app.main import app


class FakeResp:
    def __init__(self, status: int, payload=None):
        self.status_code = status
        self._payload = payload if payload is not None else {}

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


def _admin_tokens():
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u1",
            "full_name": "Admin Grace",
            "email": "admin@greenfield.edu.ng",
            "role": "school_admin",
            "school_id": "s1",
            "school_name": "Greenfield Academy",
            "account_type": "school_staff",
            "is_active": True,
            "is_verified": True,
        },
    }


def _teacher_tokens():
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u2",
            "full_name": "Teacher Bob",
            "email": "bob@greenfield.edu.ng",
            "role": "teacher",
            "school_id": "s1",
            "account_type": "school_staff",
            "is_active": True,
            "is_verified": True,
        },
    }


def _logged_in_client(monkeypatch, tokens) -> TestClient:
    client = TestClient(app)

    async def fake_auth_call(req, method, path, **kwargs):
        if path == "/auth/login":
            return FakeResp(200, tokens)
        return FakeResp(404, {"message": "not found"})

    monkeypatch.setattr("app.frontend.routes.auth.call_api", fake_auth_call)
    r = client.post("/login", data={"email": "admin@greenfield.edu.ng", "password": "PassWord123!"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    return client


def test_staff_list_renders_for_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_users_call(req, method, path, **kwargs):
        if path == "/users":
            return FakeResp(200, {"users": [{"id": "u1", "full_name": "Admin Grace", "email": "admin@greenfield.edu.ng", "role": "school_admin", "is_active": True, "is_verified": True}]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.staff.call_api", fake_users_call)
    resp = client.get("/app/staff")
    assert resp.status_code == 200
    assert "Users" in resp.text
    assert "Admin Grace" in resp.text


def test_staff_list_forbidden_for_teacher(monkeypatch):
    client = _logged_in_client(monkeypatch, _teacher_tokens())
    resp = client.get("/app/staff", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/app"


def test_settings_page_renders_for_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_school_call(req, method, path, **kwargs):
        if "/schools/s1/settings" in path:
            return FakeResp(200, {"active_term": "First Term", "academic_year": "2025/2026", "min_pass_mark": 50})
        if "/schools/s1" in path:
            return FakeResp(200, {"name": "Greenfield Academy", "contact_email": "admin@greenfield.edu.ng"})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.settings.call_api", fake_school_call)
    resp = client.get("/app/settings")
    assert resp.status_code == 200
    assert "School Settings" in resp.text
    assert "Greenfield Academy" in resp.text


def test_ops_page_renders_for_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_ops_call(req, method, path, **kwargs):
        if "/ops/health" in path:
            return FakeResp(200, {"status": "ok", "version": "1.0.0"})
        if "/ops/stats" in path:
            return FakeResp(200, {"active_workers": 2, "queue_depth": 0, "jobs_processed_24h": 45})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.ops.call_api", fake_ops_call)
    resp = client.get("/app/ops")
    assert resp.status_code == 200
    assert "System Operations" in resp.text
    assert "Active Workers" in resp.text


def test_settings_tab_htmx_partial(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_school_call(req, method, path, **kwargs):
        if "/schools/s1/settings" in path:
            return FakeResp(200, {"active_term": "First Term", "academic_year": "2025/2026", "min_pass_mark": 50})
        if "/schools/s1" in path:
            return FakeResp(200, {"name": "Greenfield Academy", "contact_email": "admin@greenfield.edu.ng"})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.settings.call_api", fake_school_call)
    resp = client.get("/ui/settings/tab?tab=security")
    assert resp.status_code == 200
    assert "settings-content" in resp.text
    assert "Change Password" in resp.text
    assert "hx-push-url" in resp.headers


def test_staff_list_htmx_partial(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_users_call(req, method, path, **kwargs):
        if path == "/users/":
            return FakeResp(200, {
                "users": [
                    {"id": "u1", "full_name": "Admin Grace", "email": "admin@greenfield.edu.ng", "role": "school_admin", "is_active": True, "is_verified": True},
                    {"id": "u2", "full_name": "Suspended Sam", "email": "sam@greenfield.edu.ng", "role": "teacher", "is_active": False, "is_verified": True},
                ]
            })
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.staff.call_api", fake_users_call)
    resp = client.get("/ui/staff/list?status=active")
    assert resp.status_code == 200
    assert "staff-content" in resp.text
    assert "Admin Grace" in resp.text
    assert "Suspended Sam" not in resp.text
    assert "hx-push-url" in resp.headers


def test_ops_panel_htmx_partial(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_ops_call(req, method, path, **kwargs):
        if "/ops/health" in path:
            return FakeResp(200, {"status": "ok", "version": "1.0.0"})
        if "/ops/stats" in path:
            return FakeResp(200, {"active_workers": 3, "queue_depth": 0, "jobs_processed_24h": 50})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.ops.call_api", fake_ops_call)
    resp = client.get("/ui/ops/panel")
    assert resp.status_code == 200
    assert "ops-panel" in resp.text
    assert "System Status" in resp.text

