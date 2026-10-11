"""Private company operations console (platform-membership protected)."""

from fasthtml.common import A, Div, H1, P, Span, Strong, Title
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Badge, Card, Col, EmptyState, Icon, Row, Table, TBody, TCell, THead, TRow

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _metric(label: str, value: str, hint: str, icon: str, tone: str = "icon-green-light") -> Card:
    return Card(
        Div(
            Div(Icon(icon, cls="bi"), cls=f"app-metric-icon-wrap {tone}"),
            Div(
                Div(value, cls="app-metric-value"),
                Div(label, cls="app-metric-label"),
                Div(hint, cls="text-muted small mt-1"),
            ),
            cls="d-flex align-items-start gap-3",
        ),
        cls="border-0 shadow-sm rounded-4 p-3 h-100 bg-white",
    )


def _platform_shell(content, user: dict, active: str, flash=None, crumbs=None, role: str | None = None):
    shell_user = dict(user)
    if role:
        shell_user["role"] = role
    return AppShell(
        Title("Platform Operations — SkuPhase"),
        content,
        user=shell_user,
        active=active,
        flash=flash,
        crumbs=crumbs,
        platform=True,
    )


def _access_denied(req: Request):
    push_flash(req, "This internal console is restricted to assigned SkuPhase platform staff.", "danger")
    return RedirectResponse("/app", status_code=303)


def register_routes(app):
    @app.get("/internal/platform")
    async def platform_overview_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/platform/overview")
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(
                EmptyState(title="Operations data unavailable", description=data.get("message", "Try again shortly.")),
                user,
                "platform-overview",
                pop_flash(req),
                [("Platform operations", None)],
            )

        schools = data.get("schools", {})
        users = data.get("users", {})
        exams = data.get("exams", {})
        jobs = data.get("jobs", {})
        usage = data.get("usage_30d", {})
        content = Div(
            Div(
                Div(
                    H1("Platform operations", cls="fw-bold fs-2 mb-1 text-dark"),
                    P("A private view of SkuPhase health, adoption, and operating cost.", cls="text-muted mb-0"),
                ),
                Badge(f"Live · {data.get('viewer_role', 'platform staff').replace('_', ' ').title()}", variant="success", pill=True),
                cls="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4",
            ),
            Row(
                Col(_metric("Active schools", str(schools.get("active", 0)), f"of {schools.get('total', 0)} total", "building", "icon-green-light"), span=12, sm=6, lg=3),
                Col(_metric("Active users", str(users.get("active", 0)), f"{users.get('verified', 0)} verified", "people", "icon-blue-light"), span=12, sm=6, lg=3),
                Col(_metric("Exams · 24 hours", str(exams.get("created_24h", 0)), f"{exams.get('created_30d', 0)} in 30 days", "file-earmark-text", "icon-purple-light"), span=12, sm=6, lg=3),
                Col(_metric("Failed jobs", str(jobs.get("failed", 0)), f"{jobs.get('pending', 0)} pending · {jobs.get('running', 0)} running", "exclamation-triangle", "icon-red-light"), span=12, sm=6, lg=3),
                cls="g-3 mb-4",
            ),
            Row(
                Col(
                    Card(
                        Strong("Seven-day exam volume", cls="d-block text-dark mb-3"),
                        Div(
                            *[
                                Div(
                                    Div(Span(item["date"], cls="small text-muted"), cls="me-2", style="width:5.5rem;"),
                                    Div(style=f"width:{min(100, max(4, item['count'] * 8))}%; height:10px;", cls="bg-success rounded-pill"),
                                    Span(str(item["count"]), cls="small fw-semibold ms-2"),
                                    cls="d-flex align-items-center mb-2",
                                )
                                for item in data.get("exam_volume_7d", [])
                            ] or [P("No exam activity recorded in the last seven days.", cls="text-muted small mb-0")],
                        ),
                        cls="border-0 shadow-sm rounded-4 p-4 h-100 bg-white",
                    ),
                    span=12,
                    lg=7,
                ),
                Col(
                    Card(
                        Strong("AI usage · last 30 days", cls="d-block text-dark mb-3"),
                        Div(Span(f"{usage.get('tokens', 0):,}", cls="fs-3 fw-bold text-dark"), " tokens", cls="mb-2"),
                        P(f"{usage.get('events', 0):,} recorded usage events", cls="text-muted small mb-1"),
                        P(f"Estimated provider cost: ${usage.get('estimated_cost', 0):,.2f}", cls="text-muted small mb-0"),
                        cls="border-0 shadow-sm rounded-4 p-4 h-100 bg-white",
                    ),
                    span=12,
                    lg=5,
                ),
                cls="g-3 mb-4",
            ),
            Card(
                Div(
                    Div(
                        Strong("Immediate attention", cls="d-block text-dark"),
                        P("Use the operational queue to investigate failed or delayed work.", cls="text-muted small mb-0"),
                    ),
                    A("Open school directory", href="/internal/platform/schools", cls="btn btn-brand rounded-pill px-3"),
                    cls="d-flex flex-wrap justify-content-between align-items-center gap-3",
                ),
                cls="border-0 shadow-sm rounded-4 p-4 bg-white",
            ),
        )
        return _platform_shell(content, user, "platform-overview", pop_flash(req), [("Platform operations", None)], data.get("viewer_role"))

    @app.get("/internal/platform/schools")
    async def platform_schools_page(req: Request, q: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/platform/schools", params={"q": q} if q else None)
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(
                EmptyState(title="School directory unavailable", description=data.get("message", "Try again shortly.")),
                user,
                "platform-schools",
                pop_flash(req),
                [("Platform operations", "/internal/platform"), ("Schools", None)],
            )
        rows = [
            TRow(
                TCell(Strong(item["name"])),
                TCell(item.get("contact_email") or "—"),
                TCell(str(item.get("staff_count", 0))),
                TCell(str(item.get("exams_30d", 0))),
                TCell(Badge("Active" if item.get("is_active") else "Inactive", variant="success" if item.get("is_active") else "secondary", pill=True)),
            )
            for item in data.get("schools", [])
        ]
        table = Table(
            THead(TRow(TCell("School"), TCell("Contact"), TCell("Staff"), TCell("Exams · 30d"), TCell("Status"))),
            TBody(*rows),
            hover=True,
            cls="app-table mb-0",
        ) if rows else EmptyState(title="No schools found", description="Try a different school name.")
        content = Div(
            H1("Schools", cls="fw-bold fs-2 mb-1 text-dark"),
            P("Cross-school visibility for support and platform operations.", cls="text-muted mb-4"),
            Card(table, cls="border-0 shadow-sm rounded-4 p-3 bg-white"),
        )
        return _platform_shell(content, user, "platform-schools", pop_flash(req), [("Platform operations", "/internal/platform"), ("Schools", None)])

    @app.get("/internal/platform/support")
    async def platform_support_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/platform/feedback", params={"limit": 50})
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(
                EmptyState(title="Support queue unavailable", description=data.get("message", "Try again shortly.")),
                user, "platform-support", pop_flash(req), [("Platform operations", "/internal/platform"), ("Support", None)],
            )
        rows = [
            TRow(
                TCell(Strong(item["subject"])),
                TCell(item["category"].replace("_", " ").title()),
                TCell(Badge(item["severity"].title(), variant="danger" if item["severity"] in {"critical", "high"} else "secondary", pill=True)),
                TCell(Badge(item["status"].replace("_", " ").title(), variant="warning" if item["status"] not in {"resolved", "closed"} else "success", pill=True)),
                TCell(item["created_at"][:10]),
            )
            for item in data.get("tickets", [])
        ]
        table = Table(
            THead(TRow(TCell("Subject"), TCell("Category"), TCell("Severity"), TCell("Status"), TCell("Date"))),
            TBody(*rows), hover=True, cls="app-table mb-0",
        ) if rows else EmptyState(title="No support cases", description="New school feedback will appear here.")
        content = Div(
            H1("Support queue", cls="fw-bold fs-2 mb-1 text-dark"),
            P("Review feedback from pilot schools and identify recurring platform issues.", cls="text-muted mb-4"),
            Card(table, cls="border-0 shadow-sm rounded-4 p-3 bg-white"),
        )
        return _platform_shell(content, user, "platform-support", pop_flash(req), [("Platform operations", "/internal/platform"), ("Support", None)], data.get("viewer_role"))
