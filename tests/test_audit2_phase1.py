"""Audit2 Phase 1 regression tests (see AUDIT2_IMPLEMENTATION_PLAN.md §Phase 1).

Drives the real flows the audit2 flagged as HIGH severity: `Flash()` components
previously returned directly from HTMX handlers (exam delete / poll /
submit-final / ops partial role-guard), which rendered orphaned alerts with no
session pop and broke the toast contract. Each test asserts the HTMX response
now carries ModernToast markup (`faststrap-modern-toast`) and the full-page
paths still use the Flash + redirect pattern.
"""

import pytest
from starlette.testclient import TestClient

from app.main import app

TOAST_MARKER = "faststrap-modern-toast"

# ---------------------------------------------------------------------------
# EmptyState kwarg regression (audit2 Phase 2 discovery)
# ---------------------------------------------------------------------------
# faststrap's EmptyState signature is (icon, title, description, action, ...).
# Passing message=/primary_cta= silently became HTML attributes, so empty-state
# text and CTAs never rendered. These tests pin the correct kwargs at the
# source level and verify a real render.


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


@pytest.fixture
def client():
    return TestClient(app)


def _login(client, monkeypatch, role="school_admin"):
    tokens = {
        "access_token": "at", "refresh_token": "rt", "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u1", "full_name": "Amina", "email": "a@b.com",
            "role": role, "account_type": "school_staff",
            "is_active": True, "is_verified": True,
        },
    }
    stub = ApiStub([("POST", "/auth/login", FakeResp(200, tokens))])
    monkeypatch.setattr("app.frontend.routes.auth.call_api", stub)
    r = client.post("/login", data={"email": "a@b.com", "password": "pw"})
    assert r.status_code in (200, 303)
    return stub


# ---------------------------------------------------------------------------
# 1. exam_delete (HTMX DELETE): error -> ModernToast, success -> 303 + flash
# ---------------------------------------------------------------------------


def test_exam_delete_error_returns_toast_not_flash(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([
        ("DELETE", "/exams/e1", FakeResp(403, {"message": "Only draft exams can be deleted."})),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.delete("/ui/exams/e1")
    assert r.status_code == 200
    body = r.text
    assert TOAST_MARKER in body, "HTMX delete failure must render ModernToast markup"
    assert "Only draft exams can be deleted." in body
    # Flash prefix ("Error: ...") proves a Flash component leaked into the swap
    assert "Error: Only draft" not in body


def test_exam_delete_success_redirects(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("DELETE", "/exams/e1", FakeResp(200, {}))])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.delete("/ui/exams/e1", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/app/exams")


# ---------------------------------------------------------------------------
# 2. exam_poll (HTMX GET partial): fetch failure -> ModernToast
# ---------------------------------------------------------------------------


def test_exam_poll_error_returns_toast(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("GET", "/exams/e1", FakeResp(404, {"message": "Exam not found."}))])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.get("/ui/exams/e1/poll")
    assert r.status_code == 200
    assert TOAST_MARKER in r.text
    assert "Exam not found." in r.text


# ---------------------------------------------------------------------------
# 3. submit-final: error -> ModernToast; success -> 303 redirect + set_flash
# ---------------------------------------------------------------------------


def test_submit_final_error_returns_toast(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([
        ("POST", "/exams/e1/submit-final", FakeResp(400, {"message": "Not in a submittable state."})),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.post("/ui/exams/e1/submit-final")
    assert r.status_code == 200
    assert TOAST_MARKER in r.text
    assert "Not in a submittable state." in r.text


def test_submit_final_success_redirects(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([("POST", "/exams/e1/submit-final", FakeResp(200, {}))])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.post("/ui/exams/e1/submit-final", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/app/exams/e1")


# ---------------------------------------------------------------------------
# 4. Ops role guard split: HTMX partial -> toast; full page -> Flash
# ---------------------------------------------------------------------------


def test_ops_panel_teacher_gets_toast_not_flash(client, monkeypatch):
    _login(client, monkeypatch, role="teacher")
    r = client.get("/ui/ops/panel")
    assert r.status_code == 200
    body = r.text
    assert "Access restricted to school administrators." in body
    assert TOAST_MARKER in body, "HTMX partial guard must use ModernToast"
    assert "Error: Access restricted" not in body


def test_ops_page_teacher_gets_flash_not_toast(client, monkeypatch):
    _login(client, monkeypatch, role="teacher")
    r = client.get("/app/ops")
    assert r.status_code == 200
    body = r.text
    assert "Access restricted to school administrators." in body
    assert TOAST_MARKER not in body, "Full-page guard must use Flash, not a toast"


def test_ops_panel_admin_renders_metrics(client, monkeypatch):
    _login(client, monkeypatch, role="school_admin")
    stub = ApiStub([
        ("GET", "/ops/health", FakeResp(200, {"status": "ok", "version": "1.0.0"})),
        ("GET", "/ops/stats", FakeResp(200, {"active_workers": 3, "queue_depth": 2})),
    ])
    monkeypatch.setattr("app.frontend.routes.ops.call_api", stub)

    r = client.get("/ui/ops/panel")
    assert r.status_code == 200
    assert "System Operations" in r.text
    assert "Access restricted" not in r.text


# ---------------------------------------------------------------------------
# 5. Export: failure -> ModernToast; success -> download link + toast
# ---------------------------------------------------------------------------


def test_export_error_returns_toast(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([
        ("POST", "/exams/e1/export", FakeResp(502, {"message": "Printer service unavailable."})),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.post("/ui/exams/e1/export", data={"include_answers": "1"})
    assert r.status_code == 200
    body = r.text
    assert TOAST_MARKER in body
    assert "Printer service unavailable." in body
    assert "Export ready." not in body


def test_export_success_renders_download_link_and_toast(client, monkeypatch):
    _login(client, monkeypatch)
    stub = ApiStub([
        ("POST", "/exams/e1/export", FakeResp(200, {
            "download_url": "https://cdn.example/exam.pdf", "file_name": "exam.pdf",
        })),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)

    r = client.post("/ui/exams/e1/export", data={})
    assert r.status_code == 200
    body = r.text
    assert TOAST_MARKER in body
    assert "Download exam.pdf" in body
    assert 'href="https://cdn.example/exam.pdf"' in body


# ---------------------------------------------------------------------------
# EmptyState kwarg regression (audit2 Phase 2 discovery)
# ---------------------------------------------------------------------------

ALLOWED_MESSAGE_SITES = {
    "feedback.py",  # set_flash(message=...) — legitimate kwarg of our helper
}


def test_emptystate_calls_use_description_and_action_kwargs():
    """No route may pass message=/primary_cta= to EmptyState — faststrap's
    signature is description=/action= and wrong kwargs silently vanish."""
    from pathlib import Path

    routes_dir = Path(__file__).resolve().parents[1] / "app" / "frontend" / "routes"
    offenders = []
    for py in sorted(routes_dir.glob("*.py")):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if "primary_cta=" in line:
                offenders.append(f"{py.name}:{i}: primary_cta=")
            # message= is allowed only in feedback helper internals
            if "message=" in line and py.name not in ALLOWED_MESSAGE_SITES:
                # exams.py:719 passes message= to _comments_tab_content (ours) — allowed
                if not (py.name == "exams.py" and "_comments_tab_content" in line):
                    offenders.append(f"{py.name}:{i}: message=")
    assert offenders == [], "EmptyState kwarg drift detected:\n" + "\n".join(offenders)


def test_emptystate_renders_description_and_action():
    from faststrap import Button, EmptyState

    html = str(
        EmptyState(
            title="No exams yet",
            description="Create your first exam with AI.",
            action=Button("Create exam", as_="a", href="/app/exams/new", cls="btn-brand"),
        )
    )
    assert "No exams yet" in html
    assert "Create your first exam with AI." in html
    assert 'href="/app/exams/new"' in html


# --- Phase 3: Onboarding & Rural Usability ---


def test_dashboard_renders_curriculum_cta(client, monkeypatch):
    """Dashboard always shows the curriculum-first CTA card (audit fix-list #5)."""
    _login(client, monkeypatch)

    async def fake_load_exams(req, **kw):
        return (True, {"exams": [], "total": 0})

    async def fake_call_api(req, method, path, **kw):
        return FakeResp(200, [])

    monkeypatch.setattr(
        "app.frontend.routes.dashboard._load_exams",
        fake_load_exams,
    )
    monkeypatch.setattr(
        "app.frontend.routes.dashboard.call_api",
        fake_call_api,
    )
    r = client.get("/app")
    assert r.status_code == 200
    assert "Start from the curriculum" in r.text
    assert "Open Curriculum Explorer" in r.text
    assert "/app/curriculum" in r.text


def test_poll_fragment_has_time_expectation_and_aria_live(client, monkeypatch):
    """Polling partial shows time expectation + aria-live (audit fix-list #18 + #12)."""
    _login(client, monkeypatch)
    stub = ApiStub([
        ("GET", "/exams/exam-004", FakeResp(200, {
            "id": "exam-004", "title": "JSS1 Basic Science",
            "workflow_state": "generation_requested", "school_id": "s1",
        })),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)
    r = client.get("/ui/exams/exam-004/poll")
    assert r.status_code == 200
    assert "usually takes under 2 minutes" in r.text
    assert 'aria-live="polite"' in r.text


def test_proposals_empty_state_explains_workflow(client, monkeypatch):
    """Zero-proposal schools see a workflow explainer (audit fix-list #4)."""
    _login(client, monkeypatch)
    stub = ApiStub([
        ("GET", "/exams/generation-proposals", FakeResp(200, {"proposals": [], "total": 0})),
    ])
    monkeypatch.setattr("app.frontend.routes.proposals.call_api", stub)
    r = client.get("/app/proposals")
    assert r.status_code == 200
    assert "How proposals work" in r.text
    assert "Teachers describe the exam they need" in r.text


def test_teacher_under_review_helper_copy(client, monkeypatch):
    """Teachers see waiting-for-admin copy on final_submitted_by_teacher exams (audit fix-list #7)."""
    _login(client, monkeypatch, role="teacher")
    stub = ApiStub([
        ("GET", "/exams/exam-002", FakeResp(200, {
            "id": "exam-002", "title": "SS3 English Language",
            "status": "final_submitted_by_teacher", "school_id": "s1",
            "subject": "English Language", "grade_level": "SS3",
        })),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)
    r = client.get("/app/exams/exam-002")
    assert r.status_code == 200
    assert "with your school admin for approval" in r.text


def test_non_teacher_no_waiting_copy(client, monkeypatch):
    """Admins do NOT see the teacher waiting copy."""
    _login(client, monkeypatch, role="school_admin")
    stub = ApiStub([
        ("GET", "/exams/exam-002", FakeResp(200, {
            "id": "exam-002", "title": "SS3 English Language",
            "status": "final_submitted_by_teacher", "school_id": "s1",
            "subject": "English Language", "grade_level": "SS3",
        })),
    ])
    monkeypatch.setattr("app.frontend.routes.exams.call_api", stub)
    r = client.get("/app/exams/exam-002")
    assert r.status_code == 200
    assert "with your school admin for approval" not in r.text

