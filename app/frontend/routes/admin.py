"""School-admin control centre.

This is intentionally a control surface, not an approval queue.  It gives an
administrator a clear view of school-wide configuration while keeping routine
lesson, question, exam, and export work self-service for teachers.
"""

import asyncio

from fasthtml.common import A, Div, H1, P, Span, Strong
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Button, Card, Col, Icon, Row

from app.frontend.api import call_api, unwrap
from app.frontend.components.layout import AppShell
from app.frontend.components.feedback import pop_flash
from app.frontend.deps import current_user, ensure_login


def _metric(label: str, value: str, icon: str, tone: str, href: str) -> A:
    return A(
        Div(
            Div(Icon(icon, cls="bi"), cls=f"app-metric-icon-wrap {tone}"),
            Div(Div(value, cls="app-metric-value"), Div(label, cls="app-metric-label")),
            cls="app-metric-card",
        ),
        href=href,
        cls="text-decoration-none d-block h-100",
    )


def _control_card(title: str, description: str, href: str, icon: str, action: str) -> Card:
    return Card(
        Div(
            Div(Icon(icon, cls="bi fs-5"), cls="guided-task-icon mb-3"),
            Strong(title, cls="d-block text-dark mb-1"),
            P(description, cls="text-muted small mb-3"),
            A(action, href=href, cls="btn btn-sm btn-outline-success rounded-pill px-3"),
        ),
        cls="h-100 border-0 shadow-sm rounded-4 p-3",
    )


def register_routes(app):
    @app.get("/app/admin")
    async def admin_home(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        if user.get("role") != "school_admin":
            return RedirectResponse("/app", status_code=303)

        school_id = user.get("school_id")
        users_call = call_api(req, "GET", "/users/")
        school_call = call_api(req, "GET", f"/schools/{school_id}") if school_id else None
        settings_call = call_api(req, "GET", f"/schools/{school_id}/settings") if school_id else None
        results = await asyncio.gather(users_call, school_call, settings_call)

        users_ok, users_data = unwrap(results[0])
        school_ok, school_data = unwrap(results[1]) if school_id else (False, {})
        settings_ok, settings_data = unwrap(results[2]) if school_id else (False, {})
        users = users_data.get("users", []) if users_ok and isinstance(users_data, dict) else []
        school = school_data if school_ok and isinstance(school_data, dict) else {}
        school_settings = settings_data if settings_ok and isinstance(settings_data, dict) else {}
        active_users = sum(1 for item in users if item.get("is_active", True) and item.get("is_verified", True))
        pending_invites = sum(1 for item in users if not item.get("is_verified", True))
        school_name = school.get("name") or user.get("school_name") or "Your school"
        academic_year = school_settings.get("academic_year") or "Not set"
        active_term = school_settings.get("active_term") or "Not set"
        flash = pop_flash(req)

        header = Div(
            Div(
                H1("School administration", cls="fw-bold fs-2 mb-1 text-dark"),
                P(
                    f"Keep {school_name} ready for independent, confident teaching.",
                    cls="text-muted mb-0",
                ),
            ),
            Button("Open school settings", as_="a", href="/app/settings", variant="success", cls="btn-brand px-4 py-2 fw-semibold"),
            cls="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4",
        )

        metrics = Row(
            Col(_metric("Active staff", str(active_users), "people-fill", "icon-green-light", "/app/staff?status=active"), span=12, sm=4),
            Col(_metric("Pending invites", str(pending_invites), "envelope-open", "icon-blue-light", "/app/staff?status=invited"), span=12, sm=4),
            Col(_metric("Current term", str(active_term), "calendar3", "icon-purple-light", "/app/settings?tab=policy"), span=12, sm=4),
            cls="g-3 mb-4",
        )

        guidance = Card(
            Div(
                Div(Icon("stars", cls="bi fs-4 text-success"), cls="app-row-icon brand me-3"),
                Div(
                    Strong("Set the defaults once; let teachers get on with teaching", cls="d-block text-dark"),
                    P(
                        "School defaults flow into new papers and documents automatically. Teachers can still create drafts, edit questions, and export work without waiting for approval.",
                        cls="text-muted small mb-0",
                    ),
                ),
                cls="d-flex align-items-start gap-2 p-3",
            ),
            cls="border-0 shadow-sm rounded-4 mb-4 bg-white",
        )

        controls = Row(
            Col(_control_card("School profile & documents", "Branding, address, logo, margins, typography, and paper defaults.", "/app/settings?tab=profile", "building", "Manage defaults"), span=12, md=6, lg=4),
            Col(_control_card("Academic policy", "Set the active session, term, and pass mark used across school workflows.", "/app/settings?tab=policy", "journal-bookmark", "Review policy"), span=12, md=6, lg=4),
            Col(_control_card("Staff access", "Invite teachers, resend invitations, and manage access without supervising daily work.", "/app/staff", "people", "Manage staff"), span=12, md=6, lg=4),
            Col(_control_card("School operations", "Review activity, jobs, and system health when something needs attention.", "/app/ops", "activity", "Open operations"), span=12, md=6, lg=4),
            Col(_control_card("Shared curriculum", "Maintain school-level curriculum choices while teachers keep personal drafts private.", "/app/curriculum", "book", "Open curriculum"), span=12, md=6, lg=4),
            Col(_control_card("Account & security", "Change your password, notification preferences, and account details.", "/app/settings?tab=account", "person-gear", "Manage account"), span=12, md=6, lg=4),
            cls="g-3",
        )

        return AppShell(
            header,
            metrics,
            guidance,
            Div(Strong("Control centre", cls="fs-5 text-dark d-block mb-3"), controls),
            user=user,
            active="admin",
            flash=flash,
            crumbs=[("Administration", None)],
        )
