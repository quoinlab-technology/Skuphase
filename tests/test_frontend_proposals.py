"""Frontend proposals tests updated for retired proposals route (410 Gone stub)."""

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


def _tokens(role="school_admin"):
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u1",
            "full_name": "Adaeze Okonkwo",
            "email": "adaeze@example.com",
            "role": role,
            "account_type": "school_staff",
            "is_active": True,
            "is_verified": True,
        },
    }


def _logged_in_client(monkeypatch, role="school_admin") -> TestClient:
    client = TestClient(app)

    async def fake_auth_call(req, method, path, **kwargs):
        if path == "/auth/login":
            return FakeResp(200, _tokens(role=role))
        return FakeResp(404, {"message": "not found"})

    monkeypatch.setattr("app.frontend.routes.auth.call_api", fake_auth_call)
    r = client.post(
        "/login", data={"email": "adaeze@example.com", "password": "PassWord123!"}, follow_redirects=False
    )
    assert r.status_code in (302, 303)
    return client


def test_proposals_list_renders(monkeypatch):
    """Proposals page returns 410 Gone — route retired."""
    client = _logged_in_client(monkeypatch, role="school_admin")

    async def fake_proposals(req, method, path, **kwargs):
        if path == "/exams/generation-proposals":
            return FakeResp(410, {})
        return FakeResp(404, {"message": "not found"})

    monkeypatch.setattr("app.frontend.routes.proposals.call_api", fake_proposals)
    r = client.get("/app/proposals")
    assert r.status_code == 410


def test_proposals_new_form_renders(monkeypatch):
    """New proposals page returns 410 Gone — route retired."""
    client = _logged_in_client(monkeypatch, role="school_admin")

    r = client.get("/app/proposals/new")
    assert r.status_code == 410


def test_proposals_create_submit(monkeypatch):
    """Create submit returns 410 Gone — route retired."""
    client = _logged_in_client(monkeypatch, role="school_admin")

    async def fake_proposals(req, method, path, **kwargs):
        if path == "/exams/generation-proposals":
            return FakeResp(410, {})
        return FakeResp(404, {"message": "not found"})

    monkeypatch.setattr("app.frontend.routes.proposals.call_api", fake_proposals)
    r = client.post("/app/proposals", data={"subject": "Mathematics"})
    assert r.status_code == 410


def test_proposals_generate_by_admin(monkeypatch):
    """Generate returns 410 Gone — route retired."""
    client = _logged_in_client(monkeypatch, role="school_admin")

    r = client.post("/app/proposals/p1/generate", data={"type": "standard"})
    assert r.status_code == 410


def test_proposals_htmx_partial_filters(monkeypatch):
    """HTMX partial returns 410 Gone — route retired."""
    client = _logged_in_client(monkeypatch, role="school_admin")

    r = client.get("/app/proposals?status=open")
    assert r.status_code == 410
