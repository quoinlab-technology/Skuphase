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


def test_admin_control_centre_renders_for_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_admin_call(req, method, path, **kwargs):
        if path == "/users/":
            return FakeResp(200, {"users": [
                {"id": "u1", "full_name": "Admin Grace", "role": "school_admin", "is_active": True, "is_verified": True},
                {"id": "u2", "full_name": "Invited Teacher", "role": "teacher", "is_active": True, "is_verified": False},
            ]})
        if path == "/schools/s1":
            return FakeResp(200, {
                "name": "Greenfield Academy",
                "contact_email": "admin@greenfield.edu.ng",
                "contact_phone": "+234 801 000 0000",
            })
        if path == "/schools/s1/settings":
            return FakeResp(200, {"active_term": "First Term", "academic_year": "2025/2026"})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.admin.call_api", fake_admin_call)
    resp = client.get("/app/admin")
    assert resp.status_code == 200
    assert "School administration" in resp.text
    assert "Greenfield Academy" in resp.text
    assert "+234 801 000 0000" in resp.text
    assert "Active staff" in resp.text
    assert "Pending invites" in resp.text
    assert "Set the defaults once" in resp.text
    assert "Administration" in resp.text
    assert "v2.0.0" in resp.text
    assert "mutationForm" in resp.text
    assert "spinner-border spinner-border-sm" in resp.text


def test_admin_control_centre_redirects_non_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, _teacher_tokens())
    resp = client.get("/app/admin", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/app"


def test_staff_list_forbidden_for_teacher(monkeypatch):
    client = _logged_in_client(monkeypatch, _teacher_tokens())
    resp = client.get("/app/staff", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/app"


def test_settings_page_renders_for_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def fake_school_call(req, method, path, **kwargs):
        if "/schools/s1/settings" in path:
            return FakeResp(200, {
                "active_term": "First Term",
                "academic_year": "2025/2026",
                "min_pass_mark": 50,
                "logo_url": "https://example.supabase.co/storage/v1/object/public/school-assets/schools/s1/logo/current.png",
                "logo_storage_path": "schools/s1/logo/current.png",
            })
        if "/schools/s1" in path:
            return FakeResp(200, {"name": "Greenfield Academy", "contact_email": "admin@greenfield.edu.ng"})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.settings.call_api", fake_school_call)
    resp = client.get("/app/settings")
    assert resp.status_code == 200
    assert "School Settings" in resp.text
    assert "Greenfield Academy" in resp.text
    assert "Reset school logo" in resp.text
    assert "current.png" in resp.text
    assert 'name="csrf_token"' in resp.text


def test_platform_console_is_not_available_to_school_admin(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def denied_platform_call(req, method, path, **kwargs):
        return FakeResp(403, {"detail": "Platform access is not enabled for this account"})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", denied_platform_call)
    resp = client.get("/internal/platform", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/app"


def test_platform_overview_renders_for_platform_membership(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        return FakeResp(200, {
            "viewer_role": "platform_admin",
            "schools": {"total": 4, "active": 3},
            "users": {"active": 18, "verified": 16},
            "exams": {"created_24h": 7, "created_30d": 42, "failed_24h": 1},
            "jobs": {"pending": 2, "running": 1, "failed": 1},
            "usage_30d": {"tokens": 12000, "estimated_cost": 1.25, "events": 40},
            "exam_volume_7d": [{"date": "2026-10-11", "count": 3}],
        })

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    resp = client.get("/internal/platform")
    assert resp.status_code == 200
    assert "Platform operations" in resp.text
    assert "Active schools" in resp.text
    assert "platform_admin" in resp.text or "Platform Admin" in resp.text
    assert "12,000" in resp.text


def test_feedback_and_notification_pages_render(monkeypatch):
    client = _logged_in_client(monkeypatch, _teacher_tokens())

    async def support_call(req, method, path, **kwargs):
        if path == "/feedback/mine":
            return FakeResp(200, {"tickets": []})
        if path == "/notifications":
            return FakeResp(200, {"unread": 1, "notifications": [{
                "notification_id": "n1",
                "title": "Feedback received",
                "body": "Your report was recorded.",
                "kind": "feedback_received",
                "severity": "info",
                "target_url": "/app/feedback",
                "is_read": False,
                "created_at": "2026-10-11T10:00:00+00:00",
            }]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.support.call_api", support_call)
    feedback = client.get("/app/feedback")
    notifications = client.get("/app/notifications")
    assert feedback.status_code == 200
    assert "Report a problem" in feedback.text
    assert notifications.status_code == 200
    assert "Feedback received" in notifications.text


def test_school_feedback_detail_shows_public_replies(monkeypatch):
    client = _logged_in_client(monkeypatch, _teacher_tokens())

    async def support_call(req, method, path, **kwargs):
        if path == "/feedback/mine":
            return FakeResp(200, {"tickets": [{"ticket_id": "ticket-1", "subject": "Export is slow", "category": "export", "status": "investigating", "created_at": "2026-10-11T10:00:00+00:00"}]})
        if path == "/feedback/ticket-1":
            return FakeResp(200, {"ticket": {"ticket_id": "ticket-1", "subject": "Export is slow", "description": "The PDF takes too long.", "category": "export", "severity": "high", "status": "investigating", "created_at": "2026-10-11T10:00:00+00:00"}, "messages": [{"body": "We are checking the export worker.", "created_at": "2026-10-11T10:30:00+00:00"}]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.support.call_api", support_call)
    listing = client.get("/app/feedback")
    detail = client.get("/app/feedback/ticket-1")
    assert listing.status_code == 200
    assert "/app/feedback/ticket-1" in listing.text
    assert detail.status_code == 200
    assert "We are checking the export worker." in detail.text
    assert "What happens next" in detail.text


def test_platform_support_detail_renders_case_controls(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/platform/feedback/ticket-1":
            return FakeResp(200, {"ticket": {
                "ticket_id": "ticket-1", "subject": "Exam export is slow", "description": "The PDF takes several minutes.",
                "category": "export", "severity": "high", "status": "investigating",
                "created_at": "2026-10-11T10:00:00+00:00", "page_url": "/app/exams",
            }, "messages": [{"body": "We are checking the export worker.", "is_internal": True, "created_at": "2026-10-11T10:30:00+00:00"}]})
        if path == "/platform/members":
            return FakeResp(200, {"members": [{"user_id": "operator-1", "full_name": "Support Ada", "email": "ada@skuphase.com", "role": "support_agent"}]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    resp = client.get("/internal/platform/support/ticket-1")
    assert resp.status_code == 200
    assert "Exam export is slow" in resp.text
    assert "Update case" in resp.text
    assert "Internal note" in resp.text
    assert "Support Ada" in resp.text


def test_platform_notifications_render_and_link_to_private_inbox(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/notifications":
            return FakeResp(200, {"unread": 1, "notifications": [{
                "notification_id": "n-1", "title": "Support case assigned", "body": "A ticket needs your attention.",
                "severity": "info", "target_url": "/internal/platform/support/ticket-1", "is_read": False,
                "created_at": "2026-10-11T10:00:00+00:00",
            }]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    resp = client.get("/internal/platform/notifications")
    assert resp.status_code == 200
    assert "Support case assigned" in resp.text
    assert "/internal/platform/support/ticket-1" in resp.text
    assert "Mark all as read" in resp.text


def test_platform_notification_delivery_monitor_renders_retry(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/platform/notifications/delivery":
            return FakeResp(200, {"counts": {"pending": 1, "sent": 2, "failed": 1}, "deliveries": [{
                "notification_id": "n-failed", "recipient_email": "teacher@greenfield.edu.ng",
                "title": "Support replied", "status": "failed", "attempts": 3,
                "last_error": "SMTP unavailable", "created_at": "2026-10-12T10:00:00+00:00",
            }]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    resp = client.get("/internal/platform/notifications/delivery")
    assert resp.status_code == 200
    assert "Email delivery" in resp.text
    assert "SMTP unavailable" in resp.text
    assert "Retry" in resp.text


def test_platform_audit_page_renders_read_only_events(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/platform/audit-events":
            return FakeResp(200, {"events": [{
                "event_id": "event-1", "action": "platform.support_message_added", "actor_role": "support_agent",
                "target_type": "feedback_ticket", "target_id": "ticket-1", "success": True,
                "summary": "Sent a support reply.", "created_at": "2026-10-11T10:00:00+00:00",
            }]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    resp = client.get("/internal/platform/audit")
    assert resp.status_code == 200
    assert "Audit events" in resp.text
    assert "Support Message Added" in resp.text
    assert "Sent a support reply." in resp.text
    assert "Filter" in resp.text


def test_platform_directory_and_school_detail_render(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/platform/users":
            return FakeResp(200, {"users": [{"full_name": "Support Ada", "email": "ada@skuphase.com", "school_name": "Greenfield Academy", "role": "teacher", "is_active": True, "last_login": None}]})
        if path == "/platform/schools/s1":
            return FakeResp(200, {"school": {"name": "Greenfield Academy", "contact_email": "admin@greenfield.edu.ng", "contact_phone": "+234 801 000 0000", "created_at": "2026-10-01T00:00:00+00:00"}, "users": {"active": 4, "verified": 3}, "exams_30d": 12, "open_support_cases": 1, "failed_jobs": 2, "usage_30d": {"tokens": 1200, "estimated_cost": 0.12}})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    users = client.get("/internal/platform/users")
    school = client.get("/internal/platform/schools/s1")
    assert users.status_code == 200
    assert "Support Ada" in users.text
    assert school.status_code == 200
    assert "Greenfield Academy" in school.text
    assert "Open support" in school.text


def test_platform_jobs_and_usage_pages_render(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/platform/jobs":
            return FakeResp(200, {"counts": {"pending": 2, "running": 1, "failed": 3}, "jobs": [{"job_id": "job-12345678", "status": "failed", "attempts": 2, "max_attempts": 3, "created_at": "2026-10-11T10:00:00+00:00", "last_error": "provider timeout"}]})
        if path == "/platform/health":
            return FakeResp(200, {"status": "healthy", "checks": {"database": "healthy"}})
        if path == "/platform/usage":
            return FakeResp(200, {"totals": {"tokens": 1200, "estimated_cost": 0.12, "events": 4}, "daily": [{"date": "2026-10-11", "tokens": 1200, "estimated_cost": 0.12, "events": 4}]})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    jobs = client.get("/internal/platform/jobs")
    usage = client.get("/internal/platform/usage")
    assert jobs.status_code == 200
    assert "Service health" in jobs.text
    assert "provider timeout" in jobs.text
    assert "Retry" in jobs.text
    assert usage.status_code == 200
    assert "Daily activity" in usage.text
    assert "$0.12" in usage.text


def test_platform_insights_page_renders_aggregate_metrics(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/platform/insights":
            return FakeResp(200, {
                "days": 30,
                "usage_by_action": [{"action": "exam_generation", "provider": "gemini", "events": 3, "tokens": 900, "cost": 0.09}],
                "adoption": {"manual_events": 2, "ai_events": 3, "total_exam_events": 5},
                "failures_by_subject": [{"subject": "Physics", "failed": 2}],
                "quality": [{"status": "passed", "snapshots": 4, "average_score": 87.5}],
                "generation_latency": {"completed_jobs": 4, "average_seconds": 8.2, "p95_seconds": 15.4},
                "onboarding": [{"school": "Greenfield Academy", "staff": 4, "exams": 0, "active": False}],
            })
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    response = client.get("/internal/platform/insights")
    assert response.status_code == 200
    assert "Product insights" in response.text
    assert "Exam Generation" in response.text
    assert "$0.09" in response.text
    assert "Physics" in response.text
    assert "Greenfield Academy" in response.text
    assert "No recent activity" in response.text


def test_platform_phase_four_governance_pages_render(monkeypatch):
    client = _logged_in_client(monkeypatch, _admin_tokens())

    async def platform_call(req, method, path, **kwargs):
        if path == "/platform/incidents":
            return FakeResp(200, {"incidents": [{"incident_id": "i1", "title": "Provider timeout", "service": "generation", "severity": "major", "status": "investigating", "created_at": "2026-10-12T08:00:00+00:00"}]})
        if path == "/platform/curriculum/versions":
            return FakeResp(200, {"versions": [{"version_id": "v1", "version": "NERDC-2025.1", "board": "NERDC", "status": "validated", "manifest": {"curriculum_count": 10}, "created_at": "2026-10-12T08:00:00+00:00"}]})
        if path == "/platform/support-access":
            return FakeResp(200, {"grants": [{"school": "Greenfield Academy", "operator_email": "ops@skuphase.com", "reason": "Investigate reported generation failure", "active": True, "expires_at": "2026-10-12T12:00:00+00:00"}]})
        if path == "/platform/retention":
            return FakeResp(200, {"eligible_audit_events": 3})
        return FakeResp(404, {})

    monkeypatch.setattr("app.frontend.routes.platform.call_api", platform_call)
    incidents = client.get("/internal/platform/incidents")
    curriculum = client.get("/internal/platform/curriculum")
    security = client.get("/internal/platform/security")
    assert incidents.status_code == 200 and "Provider timeout" in incidents.text
    assert curriculum.status_code == 200 and "NERDC-2025.1" in curriculum.text and "Publish" in curriculum.text
    assert security.status_code == 200 and "Greenfield Academy" in security.text and "365 days" in security.text


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
    assert "Generating drafts" in resp.text


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
