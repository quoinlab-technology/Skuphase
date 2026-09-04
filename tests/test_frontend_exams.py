"""M3 frontend exams tests (FRONTEND_SPEC sec 6.4-6.6).

The frontend calls the API in-process via ``app.frontend.routes.exams.call_api``;
tests stub that function so no database is required. Login is performed for real
(via the auth router with a stubbed ``call_api``) to obtain a session cookie.
"""

import pytest
from starlette.testclient import TestClient

from app.main import app


class FakeResp:
    def __init__(self, status: int, payload: dict | None = None, content: bytes = b""):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.content = content

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


def _tokens():
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u1", "full_name": "Amina", "email": "amina@example.com",
            "role": "school_admin", "account_type": "school_staff",
            "is_active": True, "is_verified": True,
        },
    }


def _tokens_teacher():
    t = _tokens()
    t["user"] = {**t["user"], "user_id": "t1", "role": "teacher"}
    return t


def _gen_ok(**extra):
    payload = {"exam_id": "e1", "warnings": []}
    payload.update(extra)
    return FakeResp(200, payload)



EXAM = {
    "id": "e1", "title": "Primary 5 Mathematics First Term",
    "subject": "Mathematics", "grade_level": "Primary 5",
    "term": "First Term", "workflow_state": "teacher_review",
    "status": "completed", "total_questions": 5, "total_marks": 10,
    "questions": [
        {"question_number": i, "question_text": f"Q{i}?",
         "question_type": "multiple_choice", "marks": 2, "options": ["a", "b"],
         "correct_answer": "A"}
        for i in range(1, 6)
    ],
}

EXAM_LIST = {"exams": [EXAM], "total": 1}


@pytest.fixture
def client():
    return TestClient(app)


def _stub(responses):
    calls = {"n": 0}

    async def fake(req, method, path, json=None, params=None):
        calls["n"] += 1
        resp = responses if isinstance(responses, FakeResp) else (
            responses[min(calls["n"] - 1, len(responses) - 1)])
        return resp() if callable(resp) else resp

    return fake


@pytest.fixture
def logged_in(client, monkeypatch):
    """Log in for real (stubbed auth API) then patch exams.call_api."""
    monkeypatch.setattr(
        "app.frontend.routes.auth.call_api", _stub(FakeResp(200, _tokens()))
    )
    client.post("/login", data={"email": "a@b.com", "password": "password123"})
    calls = {"n": 0, "last": None}

    def _make(responses):
        calls["n"] = 0

        async def fake(req, method, path, json=None, params=None):
            calls["n"] += 1
            calls["last"] = (method, path, json)
            resp = responses if isinstance(responses, FakeResp) else (
                responses[min(calls["n"] - 1, len(responses) - 1)])
            return resp() if callable(resp) else resp

        monkeypatch.setattr("app.frontend.routes.exams.call_api", fake)
        return calls

    return _make


# ------------------------------------------------------------ guards


def test_exams_list_redirects_anon(client):
    r = client.get("/app/exams", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location", "")


def test_exam_detail_redirects_anon(client):
    r = client.get("/app/exams/e1", follow_redirects=False)
    assert r.status_code == 303


# ------------------------------------------------------------ list page


def test_exams_list_renders(client, logged_in):
    logged_in(FakeResp(200, EXAM_LIST))
    r = client.get("/app/exams")
    assert r.status_code == 200
    assert "Mathematics" in r.text
    assert "/app/exams/e1" in r.text


def test_exams_list_empty_state(client, logged_in):
    logged_in(FakeResp(200, {"exams": [], "total": 0}))
    r = client.get("/app/exams")
    assert r.status_code == 200
    assert "exam" in r.text.lower()


def test_exams_list_api_error(client, logged_in):
    logged_in(FakeResp(500, {"detail": "boom"}))
    r = client.get("/app/exams")
    assert r.status_code == 200  # error rendered in-page, never a 500


# ------------------------------------------------------------ wizard + manual


def test_wizard_page_renders(client, logged_in):
    # Regression: "/app/exams/new" must NOT be shadowed by the param route
    # "/app/exams/{exam_id}" (which would 303-redirect to /app/exams).
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    r = client.get("/app/exams/new", follow_redirects=False)
    assert r.status_code == 200
    assert "app-stepper" in r.text          # the modern step nav renders
    assert "Create exam with AI" in r.text


def test_wizard_all_steps_render(client, logged_in):
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    for step in ("1", "2", "3"):
        r = client.get(f"/app/exams/new?step={step}", follow_redirects=False)
        assert r.status_code == 200
        assert "app-stepper" in r.text


def test_manual_entry_page_renders(client, logged_in):
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    r = client.get("/app/exams/new/manual")
    assert r.status_code == 200
    assert "question" in r.text.lower()


# ------------------------------------------------------------ detail + actions


def test_exam_detail_renders_questions(client, logged_in):
    logged_in(FakeResp(200, EXAM))
    r = client.get("/app/exams/e1")
    assert r.status_code == 200
    assert "Q1?" in r.text
    assert "Q5?" in r.text


def test_exam_detail_404_handled(client, logged_in):
    logged_in(FakeResp(404, {"detail": "not found"}))
    r = client.get("/app/exams/nope")
    assert r.status_code == 200  # error state page, no crash


def test_poll_partial(client, logged_in):
    logged_in(FakeResp(200, EXAM))
    r = client.get("/ui/exams/e1/poll")
    assert r.status_code == 200


def test_refine_action(client, logged_in):
    logged_in(FakeResp(200, {**EXAM, "workflow_state": "refinement_requested"}))
    r = client.post("/ui/exams/e1/refine",
                    data={"instructions": "make it harder"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)


def test_submit_final_action(client, logged_in):
    logged_in(FakeResp(200, {**EXAM, "workflow_state": "final_submitted_by_teacher"}))
    r = client.post("/ui/exams/e1/submit-final", follow_redirects=False)
    assert r.status_code in (200, 303)


def test_approve_action_preflight_block(client, logged_in):
    logged_in(FakeResp(409, {"detail": "Preflight failed",
                             "failed_checks": ["Total marks mismatch (5 != 10)"]}))
    r = client.post("/ui/exams/e1/approve")
    assert r.status_code == 200  # block surfaced in-page, not a 500


def test_export_action(client, logged_in):
    logged_in(FakeResp(200, {"export_id": "x1", "file_name": "abc.pdf"}))
    r = client.post("/ui/exams/e1/export", follow_redirects=False)
    assert r.status_code in (200, 303)


def test_delete_action(client, logged_in):
    logged_in(FakeResp(204, {}))
    r = client.delete("/ui/exams/e1", follow_redirects=False)
    assert r.status_code in (200, 303)
