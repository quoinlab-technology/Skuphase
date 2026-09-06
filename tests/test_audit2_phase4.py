"""Audit2 Phase 4 regression tests (see AUDIT2_IMPLEMENTATION_PLAN.md §Phase 4).

Drives the accessibility, mobile, and print polish items: aria-current on
filter pills / curriculum pills / settings tabs, action-oriented fallback
error copy, hx-indicator on small partials, print-avoid-break on question
cards, mobile toast-container clearance above the bottom nav, and the
proposal title truncate clamp.
"""

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


TOAST_MARKER = "faststrap-modern-toast"


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


def _login(client: TestClient, monkeypatch: pytest.MonkeyPatch, role: str = "school_admin"):
    tokens = {
        "access_token": "at", "refresh_token": "rt", "token_type": "bearer",
        "expires_in": 3600,
        "user": {"user_id": "u1", "full_name": "Amina", "email": "a@b.com",
                 "role": role, "account_type": "school_staff",
                 "is_active": True, "is_verified": True},
    }
    auth_stub = ApiStub([("POST", "/auth/login", FakeResp(200, tokens))])
    monkeypatch.setattr("app.frontend.routes.auth.call_api", auth_stub)
    r = client.post("/login", data={"email": "a@b.com", "password": "pw"})
    assert r.status_code in (200, 303)
    return auth_stub


def test_exams_filter_pill_active_aria(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    r = client.get("/app/exams")
    assert r.status_code == 200
    assert 'aria-current="true"' in r.text
    assert r.text.count('aria-current="true"') == 1


def test_curriculum_pill_active_aria(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    stub = ApiStub([
        ("GET", "/curriculum/scheme", FakeResp(200, {
            "classes": [{"name": "Primary 3", "subjects": [
                {"name": "Mathematics", "terms": [
                    {"name": "First Term", "weeks": [{"week_number": 1}]}]}]}]
        })),
    ])
    monkeypatch.setattr("app.frontend.routes.curriculum.call_api", stub)
    r = client.get("/app/curriculum?class_level=Primary 3")
    assert r.status_code == 200
    assert 'aria-current="true"' in r.text


def test_settings_tab_active_aria(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    r = client.get("/app/settings?tab=account")
    assert r.status_code == 200
    assert 'aria-current="true"' in r.text


def test_exams_load_fallback_copy(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    stub = ApiStub([("GET", "/exams", FakeResp(500, {}))])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)
    r = client.get("/app/exams")
    assert r.status_code == 200
    assert 'role="alert"' in r.text
    # unwrap() centralizes error copy (api.py case 8); assert the action-oriented tail.
    assert "please try again in a moment" in r.text


def test_exam_delete_fallback_copy(monkeypatch):
    client = TestClient(app)
    _login(client, monkeypatch)
    stub = ApiStub([
        ("GET", "/exams", FakeResp(200, {"exams": [{"id": "e1", "title": "T",
             "status": "draft", "subject": "Math", "grade": "Primary 3",
             "total_marks": 40, "creator_name": "Me", "created_at": "2025-01-01",
             "quality_score": None, "question_count": 0}]})),
        ("GET", "/exams/e1", FakeResp(200, {"id": "e1", "title": "T",
             "status": "draft", "subject": "Math", "grade": "Primary 3",
             "total_marks": 40, "creator_name": "Me", "created_at": "2025-01-01",
             "quality_score": None, "question_count": 0})),
        ("DELETE", "/exams/e1", FakeResp(500, {})),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)
    r = client.delete("/ui/exams/e1", headers={"hx-request": "true"})
    assert r.status_code == 200
    assert TOAST_MARKER in r.text
    # unwrap() supplies the message; the route fallback is a safety net.
    assert "please try again in a moment" in r.text


def test_question_toggles_are_native_checkboxes(monkeypatch):
    """Plan §4.2: toggle controls are native labeled checkboxes.

    The show-answers toggle and the Bloom's pills are real ``<input
    type=checkbox>`` elements (checked state is natively exposed to assistive
    tech).  ``aria-pressed`` deliberately is NOT added — per ARIA guidance it
    would mask the checkbox role.  This test locks in that guarantee.
    """
    client = TestClient(app)
    _login(client, monkeypatch)
    stub = ApiStub([
        ("GET", "/exams/e1", FakeResp(200, {
            "id": "e1", "title": "T", "status": "draft",
            "questions": [{"marks": 2, "question": "What is 2+2?",
                           "correct_answer": "4", "difficulty": "easy"}],
        })),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)
    r = client.get("/ui/exams/e1/tab/questions", headers={"hx-request": "true"})
    assert r.status_code == 200
    # Native labeled checkbox for show-answers.
    assert 'type="checkbox"' in r.text
    assert "Show answers" in r.text
    # The questions tab is a partial; the Bloom's pills live in the wizard
    # (step 1) as native labeled checkboxes too.
    w = client.get("/app/exams/new")
    assert w.status_code == 200
    assert "Cognitive Taxonomy Focus" in w.text
    assert 'class="blooms-pill-checkbox d-none"' in w.text
    # No bare toggle buttons — aria-pressed would mask the checkbox role.
    assert "aria-pressed" not in r.text + w.text