"""Frontend Curriculum module tests (/app/curriculum)."""

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


def _teacher_tokens():
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u2",
            "full_name": "Teacher Emeka",
            "email": "emeka@greenfield.edu.ng",
            "role": "teacher",
            "school_id": "s1",
            "school_name": "Greenfield Academy",
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
    r = client.post("/login", data={"email": "emeka@greenfield.edu.ng", "password": "PassWord123!"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    return client


def test_curriculum_unauthenticated_redirects():
    client = TestClient(app)
    r = client.get("/app/curriculum", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location", "")


def test_curriculum_authenticated_renders(monkeypatch):
    client = _logged_in_client(monkeypatch, _teacher_tokens())

    async def fake_call(req, method, path, **kwargs):
        if path == "/auth/me":
            return FakeResp(200, _teacher_tokens()["user"])
        if path == "/curriculum/classes":
            return FakeResp(200, {"classes": ["Primary 1", "Primary 2", "Primary 3", "Primary 4"]})
        if path == "/curriculum/subjects":
            return FakeResp(200, {"class_level": "Primary 4", "subjects": [{"id": "1", "subject_name": "Mathematics"}]})
        if path == "/curriculum/weeks":
            return FakeResp(200, {"weeks": [{"week_number": 1, "topic": "Place Values", "learning_objectives": ["Identify units", "Count to 1000"]}]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.curriculum.call_api", fake_call)

    r = client.get("/app/curriculum")
    assert r.status_code == 200
    assert "National Curriculum" in r.text
    assert "Primary 4" in r.text
    assert "Place Values" in r.text


def test_curriculum_search(monkeypatch):
    client = _logged_in_client(monkeypatch, _teacher_tokens())

    async def fake_call(req, method, path, **kwargs):
        if path == "/auth/me":
            return FakeResp(200, _teacher_tokens()["user"])
        if path == "/curriculum/classes":
            return FakeResp(200, {"classes": ["Primary 4"]})
        if path == "/curriculum/search":
            return FakeResp(200, [{"class_level": "Primary 4", "subject_name": "Mathematics", "term": "first", "week_number": 3, "topic": "Fractions and Decimals", "learning_objectives": ["Add fractions"]}])
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.curriculum.call_api", fake_call)

    r = client.get("/app/curriculum?q=Fractions")
    assert r.status_code == 200
    assert "Search results for" in r.text
    assert "Fractions and Decimals" in r.text
