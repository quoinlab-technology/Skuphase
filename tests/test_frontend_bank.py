"""Frontend Question Bank tests (FRONTEND_SPEC sec 6.10 & UI_design/Question-Bank.png)."""

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
            "full_name": "Emeka Obi",
            "email": "emeka@example.com",
            "role": role,
            "account_type": "school_staff",
            "is_active": True,
            "is_verified": True,
        },
    }


BANK_ITEM = {
    "id": "b1",
    "subject": "Mathematics",
    "grade_level": "Primary 4",
    "topic": "Fractions",
    "difficulty": "medium",
    "question_text": "What is 1/2 + 1/4?",
    "marks": 2,
    "options": ["3/4", "2/6", "1/4", "1/8"],
    "correct_answer": "A",
    "explanation": "Convert to a common denominator of 4: 2/4 + 1/4 = 3/4.",
    "usage_count": 3,
}


def _logged_in_client(monkeypatch, role="school_admin") -> TestClient:
    client = TestClient(app)

    async def fake_auth_call(req, method, path, **kwargs):
        if path == "/auth/login":
            return FakeResp(200, _tokens(role=role))
        return FakeResp(404, {"message": "not found"})

    monkeypatch.setattr("app.frontend.routes.auth.call_api", fake_auth_call)
    r = client.post("/login", data={"email": "emeka@example.com", "password": "PassWord123!"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    return client


def test_question_bank_renders(monkeypatch):
    client = _logged_in_client(monkeypatch)

    async def fake_bank_call(req, method, path, **kwargs):
        if "/exams/question-bank/items" in path and method == "GET":
            return FakeResp(200, [BANK_ITEM])
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.bank.call_api", fake_bank_call)
    resp = client.get("/app/bank")
    assert resp.status_code == 200
    assert "Question Bank" in resp.text
    assert "What is 1/2 + 1/4?" in resp.text
    assert "Primary 4 · Mathematics" in resp.text


def test_question_bank_update_item(monkeypatch):
    client = _logged_in_client(monkeypatch)

    async def fake_update_call(req, method, path, **kwargs):
        if "/exams/question-bank/items/b1" in path and method == "PUT":
            return FakeResp(200, {**BANK_ITEM, "marks": 5})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.bank.call_api", fake_update_call)
    resp = client.post(
        "/app/bank/items/b1",
        data={
            "question_text": "What is 1/2 + 1/4?",
            "difficulty": "medium",
            "marks": "5",
            "correct_answer": "A",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/app/bank"
