"""Audit remediation regression tests (see IMPLEMENTATION_PLAN.md §Validation).

Unlike the mocked unit tests, these drive the REAL multi-request flows the
audit flagged (audit_report.md:181-182): wizard step submissions, proposal
reject vs accept, and the staff/bank/profile endpoints — via TestClient with a
stubbed API backend, asserting the exact payloads the frontend handlers build.
"""

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


def _tokens(role="school_admin"):
    return {
        "access_token": "at", "refresh_token": "rt", "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u1", "full_name": "Amina", "email": "a@b.com",
            "role": role, "account_type": "school_staff",
            "is_active": True, "is_verified": True,
        },
    }


GEN_OK = FakeResp(200, {"exam_id": "e9", "warnings": []})


class ApiStub:
    """Records every (method, path, json) the frontend sends to the backend."""

    def __init__(self, routes):
        self.routes = routes  # [(method, path_prefix, FakeResp)]
        self.calls = []

    async def __call__(self, req, method, path, json=None, params=None):
        self.calls.append({"method": method, "path": path, "json": json, "params": params})
        for m, prefix, resp in self.routes:
            if m == method and path.startswith(prefix):
                return resp
        return FakeResp(200, {})


@pytest.fixture
def client():
    return TestClient(app)


def _login(client, monkeypatch, role="school_admin"):
    stub = ApiStub([("POST", "/auth/login", FakeResp(200, _tokens(role)))])
    monkeypatch.setattr("app.frontend.routes.auth.call_api", stub)
    r = client.post("/login", data={"email": "a@b.com", "password": "pw"})
    assert r.status_code in (200, 303)
    return stub


# ---------------------------------------------------------------------------
# 1. Wizard E2E: step1 -> step2 -> generate keeps ALL state (audit #1/#2)
# ---------------------------------------------------------------------------


def test_wizard_full_flow_preserves_state(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("POST", "/exams/generate", GEN_OK)])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    # Step 1: curriculum (what the browser posts from wizard-step-1)
    r = client.post("/ui/exams/wizard/step1", data={
        "grade_level": "Primary 3", "subject": "Basic Science",
        "term": "Second Term", "weeks": "1,2,3",
        "difficulty_preset": "exam_prep", "bloom_levels": ["Apply", "Analyze"],
    })
    assert r.status_code == 200

    # Step 2: sections (posted by the real form now on the Next button)
    r = client.post("/ui/exams/wizard/step2", data={
        "section_1_title": "SECTION A", "section_1_qtype": "multiple_choice",
        "section_1_num": "20", "section_1_marks": "2",
        "section_1_instr": "answer_all", "section_1_substyle": "none",
        "section_2_title": "SECTION B", "section_2_qtype": "essay",
        "section_2_num": "5", "section_2_marks": "10",
        "section_2_instr": "answer_any_n", "section_2_substyle": "letter",
    })
    assert r.status_code == 200

    # Step 3: only duration/language travel over the wire — the rest must come
    # from session (before the fix the generate call received nothing).
    r = client.post("/ui/exams/generate", data={"duration_minutes": "90", "language": "English"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/app/exams/e9")

    gen = [c for c in stub.calls if c["path"] == "/exams/generate"]
    assert len(gen) == 1
    p = gen[0]["json"]
    assert p["subject"] == "Basic Science"
    assert p["grade_level"] == "Primary 3"
    assert p["term"] == "Second Term"
    assert p["selected_weeks"] == [1, 2, 3]
    assert p["duration_minutes"] == 90
    assert [s["section_number"] for s in p["sections"]] == [1, 2]
    assert p["sections"][1]["question_type"] == "essay"
    assert p["difficulty_distribution"] == {"easy": 0.2, "medium": 0.4, "hard": 0.4}
    assert "Bloom's taxonomy levels: Apply, Analyze" in p["custom_instructions"]


def test_wizard_generate_without_steps_fails_gracefully(client, monkeypatch):
    """Generating with an empty session must show the friendly error, not 500."""
    _login(client, monkeypatch)
    monkeypatch.setattr("app.frontend.routes.exams.call_api", ApiStub([]))
    r = client.post("/ui/exams/generate", data={"duration_minutes": "60"})
    assert r.status_code == 200
    assert "section" in r.text.lower()


# ---------------------------------------------------------------------------
# 2. Proposal reject must NOT generate; accept must send sections (#3/#4)
# ---------------------------------------------------------------------------


def test_proposal_reject_calls_reject_endpoint_and_never_generates(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([
        ("POST", "/exams/generation-proposals/p1/reject",
         FakeResp(200, {"id": "p1", "status": "rejected"})),
    ])
    monkeypatch.setattr("app.frontend.routes.proposals.call_api", stub)

    r = client.post("/app/proposals/p1/reject",
                    data={"admin_note": "Out of scope"}, follow_redirects=False)
    assert r.status_code == 303

    paths = [c["path"] for c in stub.calls]
    assert "/exams/generation-proposals/p1/reject" in paths
    assert not any("/generate" in p for p in paths), "reject must not trigger generation"


def test_proposal_generate_sends_sections_payload(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([
        ("POST", "/exams/generate", FakeResp(200, {"exam_id": "e2"})),
    ])
    monkeypatch.setattr("app.frontend.routes.proposals.call_api", stub)

    r = client.post("/app/proposals/p1/generate", data={
        "term": "First Term", "selected_weeks": "1,2", "desired_outcomes": "word problems",
    }, follow_redirects=False)
    assert r.status_code == 303

    gen = [c for c in stub.calls if "generate" in c["path"] and c["method"] == "POST"]
    assert gen, "expected a generate call"
    sent = gen[0]["json"] or {}
    # audit #4: the backend schema requires non-empty sections -> 422 otherwise
    assert sent.get("sections"), "sections payload must be present"


# ---------------------------------------------------------------------------
# 3-6. Staff /users/, bank PATCH, exam reject, auth routes
# ---------------------------------------------------------------------------


def test_staff_page_uses_users_alias(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("GET", "/users/", FakeResp(200, {"users": [], "total": 0}))])
    monkeypatch.setattr("app.frontend.routes.staff.call_api", stub)
    r = client.get("/app/staff")
    assert r.status_code == 200
    assert any(c["path"].rstrip("/") == "/users" for c in stub.calls)


def test_question_bank_edit_uses_patch(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("PATCH", "/question-bank/q1", FakeResp(200, {"id": "q1"}))])
    monkeypatch.setattr("app.frontend.routes.bank.call_api", stub)
    r = client.post("/app/bank/items/q1", data={"question_text": "updated?"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    assert any(c["method"] == "PATCH" for c in stub.calls), "expected a PATCH call"


def test_exam_reject_transitions_back_to_teacher_review(client, monkeypatch):
    _login(client, monkeypatch)
    exam = {"id": "e1", "workflow_state": "teacher_review", "status": "under_review"}
    stub = ApiStub([
        ("POST", "/exams/e1/reject", FakeResp(200, {"workflow_state": "teacher_review"})),
        ("GET", "/exams/e1", FakeResp(200, exam)),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.post("/ui/exams/e1/reject", data={"feedback": "too hard for P3"})
    assert r.status_code == 200
    rejects = [c for c in stub.calls if "/exams/e1/reject" in c["path"] and c["method"] == "POST"]
    assert rejects, "expected the reject API call"


def test_get_logout_and_register_routes(client, monkeypatch):
    _login(client, monkeypatch)
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 303
    for path in ("/register/school", "/register/individual"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 200, f"{path} should render"


