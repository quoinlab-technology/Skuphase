"""Frontend Proposals tests (FRONTEND_SPEC sec 6.9 & UI_design/Proposals.png)."""

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


PROPOSAL = {
    "id": "p1",
    "subject": "Mathematics",
    "grade_level": "Primary 4",
    "term": "First Term",
    "selected_weeks": [1, 2, 3],
    "desired_outcomes": "Master place values and basic fractions.",
    "custom_instructions": "Focus on word problems.",
    "status": "open",
    "created_at": "2026-05-10T10:00:00",
}


def _logged_in_client(monkeypatch, role="school_admin") -> TestClient:
    client = TestClient(app)

    async def fake_auth_call(req, method, path, **kwargs):
        if path == "/auth/login":
            return FakeResp(200, _tokens(role=role))
        return FakeResp(404, {"message": "not found"})

    monkeypatch.setattr("app.frontend.routes.auth.call_api", fake_auth_call)
    r = client.post("/login", data={"email": "adaeze@example.com", "password": "PassWord123!"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    return client


def test_proposals_list_renders(monkeypatch):
    client = _logged_in_client(monkeypatch, role="school_admin")

    async def fake_proposals_call(req, method, path, **kwargs):
        if "/exams/generation-proposals" in path:
            return FakeResp(200, [PROPOSAL])
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.proposals.call_api", fake_proposals_call)
    resp = client.get("/app/proposals")
    assert resp.status_code == 200
    assert "Generation Proposals" in resp.text
    assert "Primary 4 Mathematics" in resp.text
    assert "Generate Exam" in resp.text


def test_proposals_new_form_renders(monkeypatch):
    client = _logged_in_client(monkeypatch, role="teacher")
    resp = client.get("/app/proposals/new")
    assert resp.status_code == 200
    assert "Submit Generation Proposal" in resp.text
    assert "Desired Learning Outcomes" in resp.text


def test_proposals_create_submit(monkeypatch):
    client = _logged_in_client(monkeypatch, role="teacher")

    async def fake_create_call(req, method, path, **kwargs):
        if path == "/exams/generation-proposals" and method == "POST":
            return FakeResp(201, PROPOSAL)
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.proposals.call_api", fake_create_call)
    resp = client.post(
        "/app/proposals/new",
        data={
            "subject": "Mathematics",
            "grade_level": "Primary 4",
            "term": "First Term",
            "selected_weeks": "1, 2, 3",
            "desired_outcomes": "Understand place values and whole numbers.",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/app/proposals"


def test_proposals_generate_by_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, role="school_admin")

    async def fake_gen_call(req, method, path, **kwargs):
        if "/generate" in path and method == "POST":
            return FakeResp(202, {"exam_id": "e1", "job_id": "j1"})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.proposals.call_api", fake_gen_call)
    resp = client.post("/app/proposals/p1/generate", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/app/exams/e1"


def test_proposals_htmx_partial_filters(monkeypatch):
    client = _logged_in_client(monkeypatch, role="school_admin")

    async def fake_proposals_call(req, method, path, **kwargs):
        if "/exams/generation-proposals" in path:
            return FakeResp(200, [
                PROPOSAL,
                {
                    "id": "p2",
                    "subject": "Basic Science",
                    "grade_level": "Primary 2",
                    "term": "First Term",
                    "selected_weeks": [1],
                    "desired_outcomes": "Living things.",
                    "status": "rejected",
                    "created_at": "2026-05-11T10:00:00",
                }
            ])
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.proposals.call_api", fake_proposals_call)

    # Test filtering by status=open
    resp = client.get("/ui/proposals/list?status=open")
    assert resp.status_code == 200
    assert "Primary 4 Mathematics" in resp.text
    assert "Primary 2 Basic Science" not in resp.text
    assert "proposals-content" in resp.text
    assert "hx-push-url" in resp.headers

    # Test filtering by status=rejected
    resp_rej = client.get("/ui/proposals/list?status=rejected")
    assert resp_rej.status_code == 200
    assert "Primary 2 Basic Science" in resp_rej.text
    assert "Primary 4 Mathematics" not in resp_rej.text

