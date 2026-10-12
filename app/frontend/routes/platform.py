"""Private company operations console (platform-membership protected)."""

from fasthtml.common import A, Div, Form, H1, Input, Label, Option, P, Span, Strong, Textarea, Title, Select as HtmlSelect
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Badge, Button, Card, Col, EmptyState, Icon, Row, Table, TBody, TCell, THead, TRow

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
        Title("Platform Operations â€” SkuPhase"),
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


def _csrf(req: Request):
    token = req.session.get("csrf")
    return Input(name="csrf_token", value=token or "", type="hidden") if token else None


def _support_status_label(value: str) -> str:
    return value.replace("_", " ").title()


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
                Badge(f"Live Â· {data.get('viewer_role', 'platform staff').replace('_', ' ').title()}", variant="success", pill=True),
                cls="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4",
            ),
            Row(
                Col(_metric("Active schools", str(schools.get("active", 0)), f"of {schools.get('total', 0)} total", "building", "icon-green-light"), span=12, sm=6, lg=3),
                Col(_metric("Active users", str(users.get("active", 0)), f"{users.get('verified', 0)} verified", "people", "icon-blue-light"), span=12, sm=6, lg=3),
                Col(_metric("Exams Â· 24 hours", str(exams.get("created_24h", 0)), f"{exams.get('created_30d', 0)} in 30 days", "file-earmark-text", "icon-purple-light"), span=12, sm=6, lg=3),
                Col(_metric("Failed jobs", str(jobs.get("failed", 0)), f"{jobs.get('pending', 0)} pending Â· {jobs.get('running', 0)} running", "exclamation-triangle", "icon-red-light"), span=12, sm=6, lg=3),
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
                        Strong("AI usage Â· last 30 days", cls="d-block text-dark mb-3"),
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
                        P(
                            f"Use the operational queue to investigate failed or delayed work. {data.get('notifications', {}).get('email_failed', 0)} notification email failure(s) need review.",
                            cls="text-muted small mb-0",
                        ),
                    ),
                    A("Open school directory", href="/internal/platform/schools", cls="btn btn-brand rounded-pill px-3"),
                    cls="d-flex flex-wrap justify-content-between align-items-center gap-3",
                ),
                cls="border-0 shadow-sm rounded-4 p-4 bg-white",
            ),
        )
        return _platform_shell(content, user, "platform-overview", pop_flash(req), [("Platform operations", None)], data.get("viewer_role"))

    @app.get("/internal/platform/notifications")
    async def platform_notifications_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/notifications", params={"limit": 100})
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(
                EmptyState(title="Notifications unavailable", description=data.get("message", "Try again shortly.")),
                user, "platform-notifications", pop_flash(req),
                [("Platform operations", "/internal/platform"), ("Notifications", None)],
            )
        items = data.get("notifications", [])
        cards = []
        for item in items:
            target = item.get("target_url") or "/internal/platform/notifications"
            cards.append(
                Div(
                    Div(
                        Badge(item.get("severity", "info").title(), variant="danger" if item.get("severity") == "critical" else "secondary", pill=True),
                        Strong(item.get("title", "Notification"), cls="d-block text-dark mt-2"),
                        P(item.get("body", ""), cls="text-muted small mb-1"),
                        Span(item.get("created_at", "")[:16].replace("T", " "), cls="text-muted small"),
                        cls="flex-grow-1",
                    ),
                    Div(
                        A("Open", href=target, cls="btn btn-sm btn-outline-secondary rounded-pill me-2") if target else None,
                        Form(
                            _csrf(req),
                            Button("Mark read", type="submit", variant="light", cls="btn btn-sm rounded-pill")
                            if not item.get("is_read") else Span("Read", cls="small text-muted"),
                            action=f"/internal/platform/notifications/{item['notification_id']}/read", method="post",
                        ) if not item.get("is_read") else None,
                        cls="d-flex align-items-center flex-shrink-0",
                    ),
                    cls="d-flex flex-wrap align-items-center gap-3 p-3 border-bottom" + (" bg-light" if not item.get("is_read") else ""),
                )
            )
        content = Div(
            Div(
                Div(H1("Notifications", cls="fw-bold fs-2 mb-1 text-dark"), P(f"{data.get('unread', 0)} unread operational notification(s)", cls="text-muted mb-0")),
                Form(_csrf(req), Button("Mark all as read", type="submit", variant="light", cls="btn btn-outline-secondary rounded-pill", **{"data-loading-label": "Updatingâ€¦"}), action="/internal/platform/notifications/read-all", method="post") if data.get("unread", 0) else None,
                cls="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4",
            ),
            Card(*(cards or [EmptyState(title="You are all caught up", description="Assigned support cases and operational alerts will appear here.")]), cls="border-0 shadow-sm rounded-4 p-0 bg-white overflow-hidden"),
        )
        return _platform_shell(content, user, "platform-notifications", pop_flash(req), [("Platform operations", "/internal/platform"), ("Notifications", None)])

    @app.get("/internal/platform/jobs")
    async def platform_jobs_page(req: Request, status: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/platform/jobs", params={"limit": 100, **({"status": status} if status else {})})
        health_response = await call_api(req, "GET", "/platform/health")
        health_ok, health = unwrap(health_response)
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(EmptyState(title="Job monitor unavailable", description=data.get("message", "Try again shortly.")), user, "platform-jobs", pop_flash(req), [("Platform operations", "/internal/platform"), ("Jobs & health", None)])
        counts = data.get("counts", {})
        rows = [TRow(TCell(item.get("created_at", "")[:16].replace("T", " ")), TCell(item.get("job_id", "")[:8]), TCell(item.get("status", "").title()), TCell(f"{item.get('attempts', 0)}/{item.get('max_attempts', 0)}"), TCell(item.get("last_error") or "—"), TCell(Form(_csrf(req), Button("Retry", type="submit", variant="light", cls="btn btn-sm btn-outline-secondary rounded-pill", **{"data-loading-label": "Retrying…"}), action=f"/internal/platform/jobs/{item['job_id']}/retry", method="post") if item.get("status") == "failed" else Span("—", cls="text-muted"))) for item in data.get("jobs", [])]
        table = Table(THead(TRow(TCell("Created"), TCell("Job"), TCell("Status"), TCell("Attempts"), TCell("Last error"), TCell("Action"))), TBody(*rows), hover=True, cls="app-table mb-0") if rows else EmptyState(title="No jobs found", description="The queue has no jobs matching this filter.")
        health_status = health.get("status", "unavailable") if health_ok else "unavailable"
        content = Div(H1("Jobs & health", cls="fw-bold fs-2 mb-1 text-dark"), P("Monitor generation queue state and provider configuration without exposing prompts or credentials.", cls="text-muted mb-4"), Row(Col(_metric("Service health", health_status.title(), "Database and worker checks", "heart-pulse", "icon-green-light" if health_status == "healthy" else "icon-red-light"), span=12, sm=3), Col(_metric("Pending", str(counts.get("pending", 0)), "Waiting to run", "hourglass", "icon-blue-light"), span=12, sm=3), Col(_metric("Running", str(counts.get("running", 0)), "Currently processing", "activity", "icon-purple-light"), span=12, sm=3), Col(_metric("Failed", str(counts.get("failed", 0)), "Requires investigation", "exclamation-triangle", "icon-red-light"), span=12, sm=3), cls="g-3 mb-4"), Card(table, cls="border-0 shadow-sm rounded-4 p-3 bg-white overflow-auto"))
        return _platform_shell(content, user, "platform-jobs", pop_flash(req), [("Platform operations", "/internal/platform"), ("Jobs & health", None)])

    @app.post("/internal/platform/jobs/{job_id}/retry")
    async def platform_job_retry_action(req: Request, job_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        response = await call_api(req, "POST", f"/platform/jobs/{job_id}/retry")
        ok, data = unwrap(response)
        push_flash(req, data.get("message", "Generation job requeued.") if ok else data.get("message", "Could not retry job."), "success" if ok else "danger")
        return RedirectResponse("/internal/platform/jobs", status_code=303)

    @app.get("/internal/platform/usage")
    async def platform_usage_page(req: Request, days: int = 30):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        days = min(max(days, 1), 90)
        response = await call_api(req, "GET", "/platform/usage", params={"days": days})
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(EmptyState(title="Usage report unavailable", description=data.get("message", "Try again shortly.")), user, "platform-usage", pop_flash(req), [("Platform operations", "/internal/platform"), ("Usage", None)])
        totals = data.get("totals", {})
        bars = []
        for item in data.get("daily", []):
            percent = min(100, max(2, item.get("tokens", 0) / max(1, totals.get("tokens", 1)) * 100))
            bars.append(Div(
                Div(Span(item.get("date"), cls="small text-muted"), Span(f"{item.get('tokens', 0):,} tokens / ${item.get('estimated_cost', 0):,.2f}", cls="small fw-semibold"), cls="d-flex justify-content-between mb-1"),
                Div(Div(style=f"width:{percent}%; height:10px;", cls="bg-success rounded-pill"), cls="bg-light rounded-pill mb-2"),
            ))
        if not bars:
            bars = [P("No usage recorded for this period.", cls="text-muted small mb-0")]
        content = Div(
            H1("Usage", cls="fw-bold fs-2 mb-1 text-dark"),
            P("Bounded AI usage and estimated cost reporting for the selected period.", cls="text-muted mb-4"),
            Row(
                Col(_metric("Tokens", f"{totals.get('tokens', 0):,}", f"Last {days} days", "graph-up", "icon-blue-light"), span=12, sm=4),
                Col(_metric("Estimated cost", f"${totals.get('estimated_cost', 0):,.2f}", "Provider estimate", "currency-dollar", "icon-green-light"), span=12, sm=4),
                Col(_metric("Usage events", f"{totals.get('events', 0):,}", "Recorded operations", "activity", "icon-purple-light"), span=12, sm=4),
                cls="g-3 mb-4",
            ),
            Card(Strong("Daily activity", cls="d-block text-dark mb-3"), Div(*bars), cls="border-0 shadow-sm rounded-4 p-4 bg-white"),
        )
        return _platform_shell(content, user, "platform-usage", pop_flash(req), [("Platform operations", "/internal/platform"), ("Usage", None)])

    @app.post("/internal/platform/notifications/{notification_id}/read")
    async def platform_notification_read_action(req: Request, notification_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        response = await call_api(req, "POST", f"/notifications/{notification_id}/read")
        ok, data = unwrap(response)
        push_flash(req, data.get("message", "Notification marked as read.") if ok else data.get("message", "Could not update notification."), "success" if ok else "danger")
        return RedirectResponse("/internal/platform/notifications", status_code=303)

    @app.get("/internal/platform/audit")
    async def platform_audit_page(req: Request, action: str = "", success: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        audit_params = {"limit": 100}
        if action:
            audit_params["action"] = action
        if success in {"true", "false"}:
            audit_params["success"] = success
        response = await call_api(req, "GET", "/platform/audit-events", params=audit_params)
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(
                EmptyState(title="Audit stream unavailable", description=data.get("message", "Try again shortly.")),
                user, "platform-audit", pop_flash(req),
                [("Platform operations", "/internal/platform"), ("Audit", None)],
            )
        rows = [
            TRow(
                TCell(item.get("created_at", "")[:16].replace("T", " ")),
                TCell(Strong(item.get("action", "").replace("_", " ").title())),
                TCell(item.get("actor_role") or "System"),
                TCell(f"{item.get('target_type') or ''} {item.get('target_id') or ''}".strip() or "â€”"),
                TCell(Badge("Success" if item.get("success") else "Failed", variant="success" if item.get("success") else "danger", pill=True)),
                TCell(item.get("summary") or "â€”"),
            )
            for item in data.get("events", [])
        ]
        table = Table(
            THead(TRow(TCell("Time"), TCell("Action"), TCell("Actor"), TCell("Target"), TCell("Result"), TCell("Summary"))),
            TBody(*rows), hover=True, cls="app-table mb-0",
        ) if rows else EmptyState(title="No audit events yet", description="Sensitive platform actions will appear here.")
        content = Div(
            H1("Audit events", cls="fw-bold fs-2 mb-1 text-dark"),
            P("Read-only history of sensitive company operations. Secrets and private prompts are excluded.", cls="text-muted mb-4"),
            Card(
                Form(
                    Div(
                        Input("action", label="Action", value=action, placeholder="e.g. platform.support_message_added", cls="mb-0"),
                        HtmlSelect(Option("Any result", value="", selected=not success), Option("Successful", value="true", selected=success == "true"), Option("Failed", value="false", selected=success == "false"), name="success", cls="form-select rounded-3"),
                        Button("Filter", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Filteringâ€¦"}),
                        A("Clear", href="/internal/platform/audit", cls="btn btn-outline-secondary rounded-pill px-4"),
                        cls="d-flex flex-wrap align-items-end gap-2",
                    ),
                    action="/internal/platform/audit", method="get",
                ),
                cls="border-0 shadow-sm rounded-4 p-3 bg-white mb-3",
            ),
            Card(table, cls="border-0 shadow-sm rounded-4 p-3 bg-white overflow-auto"),
        )
        return _platform_shell(content, user, "platform-audit", pop_flash(req), [("Platform operations", "/internal/platform"), ("Audit", None)])

    @app.post("/internal/platform/notifications/read-all")
    async def platform_notifications_read_all_action(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        response = await call_api(req, "POST", "/notifications/read-all")
        ok, data = unwrap(response)
        push_flash(req, data.get("message", "Notifications marked as read.") if ok else data.get("message", "Could not update notifications."), "success" if ok else "danger")
        return RedirectResponse("/internal/platform/notifications", status_code=303)

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
                TCell(A(Strong(item["name"]), href=f"/internal/platform/schools/{item['school_id']}", cls="text-decoration-none text-dark")),
                TCell(item.get("contact_email") or "â€”"),
                TCell(str(item.get("staff_count", 0))),
                TCell(str(item.get("exams_30d", 0))),
                TCell(Badge("Active" if item.get("is_active") else "Inactive", variant="success" if item.get("is_active") else "secondary", pill=True)),
            )
            for item in data.get("schools", [])
        ]
        table = Table(
            THead(TRow(TCell("School"), TCell("Contact"), TCell("Staff"), TCell("Exams Â· 30d"), TCell("Status"))),
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

    @app.get("/internal/platform/schools/{school_id}")
    async def platform_school_detail_page(req: Request, school_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", f"/platform/schools/{school_id}")
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(
                EmptyState(title="School profile unavailable", description=data.get("message", "Try again shortly.")),
                user, "platform-schools", pop_flash(req), [("Platform operations", "/internal/platform"), ("Schools", "/internal/platform/schools"), ("School", None)],
            )
        school = data.get("school", {})
        users = data.get("users", {})
        usage = data.get("usage_30d", {})
        content = Div(
            A("Back to schools", href="/internal/platform/schools", cls="text-decoration-none small mb-2 d-inline-block"),
            Div(H1(school.get("name", "School"), cls="fw-bold fs-2 mb-1 text-dark"), P(school.get("contact_email") or "No contact email", cls="text-muted mb-4")),
            Row(
                Col(_metric("Active staff", str(users.get("active", 0)), f"{users.get('verified', 0)} verified", "people", "icon-blue-light"), span=12, sm=6, lg=3),
                Col(_metric("Exams Â· 30d", str(data.get("exams_30d", 0)), "Created by this school", "file-earmark-text", "icon-purple-light"), span=12, sm=6, lg=3),
                Col(_metric("Open support", str(data.get("open_support_cases", 0)), "Cases needing attention", "chat-square-text", "icon-red-light"), span=12, sm=6, lg=3),
                Col(_metric("AI tokens Â· 30d", f"{usage.get('tokens', 0):,}", f"${usage.get('estimated_cost', 0):,.2f} estimated", "graph-up", "icon-green-light"), span=12, sm=6, lg=3),
                cls="g-3 mb-4",
            ),
            Card(
                Strong("Operational profile", cls="d-block text-dark mb-3"),
                P(f"Contact phone: {school.get('contact_phone') or 'Not recorded'}", cls="text-muted mb-1"),
                P(f"Created: {school.get('created_at', '')[:10]}", cls="text-muted mb-1"),
                P(f"Failed generation jobs: {data.get('failed_jobs', 0)}", cls="text-muted mb-0"),
                cls="border-0 shadow-sm rounded-4 p-4 bg-white",
            ),
        )
        return _platform_shell(content, user, "platform-schools", pop_flash(req), [("Platform operations", "/internal/platform"), ("Schools", "/internal/platform/schools"), (school.get("name", "School"), None)])

    @app.get("/internal/platform/users")
    async def platform_users_page(req: Request, q: str = "", active: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        params = {"limit": 100}
        if q:
            params["q"] = q
        if active in {"true", "false"}:
            params["active"] = active
        response = await call_api(req, "GET", "/platform/users", params=params)
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(EmptyState(title="User directory unavailable", description=data.get("message", "Try again shortly.")), user, "platform-users", pop_flash(req), [("Platform operations", "/internal/platform"), ("Users", None)])
        rows = [
            TRow(TCell(Strong(item.get("full_name") or item.get("email"))), TCell(item.get("email")), TCell(item.get("school_name")), TCell(item.get("role", "").replace("_", " ").title()), TCell(Badge("Active" if item.get("is_active") else "Suspended", variant="success" if item.get("is_active") else "danger", pill=True)), TCell(item.get("last_login", "Never")[:10] if item.get("last_login") else "Never"))
            for item in data.get("users", [])
        ]
        table = Table(THead(TRow(TCell("User"), TCell("Email"), TCell("School"), TCell("Role"), TCell("State"), TCell("Last login"))), TBody(*rows), hover=True, cls="app-table mb-0") if rows else EmptyState(title="No users found", description="Try a different name or email.")
        content = Div(H1("Users", cls="fw-bold fs-2 mb-1 text-dark"), P("Cross-school identity and access visibility without credential exposure.", cls="text-muted mb-4"), Card(Form(Input("q", label="Search name or email", value=q, placeholder="Search usersâ€¦"), Button("Search", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Searchingâ€¦"}), action="/internal/platform/users", method="get", cls="d-flex flex-wrap align-items-end gap-2 mb-3"), table, cls="border-0 shadow-sm rounded-4 p-3 bg-white"))
        return _platform_shell(content, user, "platform-users", pop_flash(req), [("Platform operations", "/internal/platform"), ("Users", None)])

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
                TCell(A(Strong(item["subject"]), href=f"/internal/platform/support/{item['ticket_id']}", cls="text-decoration-none text-dark")),
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

    @app.get("/internal/platform/support/{ticket_id}")
    async def platform_support_detail_page(req: Request, ticket_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", f"/platform/feedback/{ticket_id}")
        ok, data = unwrap(response)
        if not ok:
            return _access_denied(req) if response.status_code in (401, 403) else _platform_shell(
                EmptyState(title="Support case unavailable", description=data.get("message", "Try again shortly.")),
                user, "platform-support", pop_flash(req),
                [("Platform operations", "/internal/platform"), ("Support", "/internal/platform/support"), ("Case", None)],
            )
        ticket = data.get("ticket", {})
        messages = data.get("messages", [])
        members_response = await call_api(req, "GET", "/platform/members")
        members_ok, members_data = unwrap(members_response)
        members = members_data.get("members", []) if members_ok else []
        message_cards = [
            Card(
                Div(
                    Badge("Internal note" if item.get("is_internal") else "Reply", variant="warning" if item.get("is_internal") else "success", pill=True),
                    Span(item.get("created_at", "")[:16].replace("T", " "), cls="text-muted small ms-2"),
                    cls="mb-2",
                ),
                P(item.get("body", ""), cls="mb-0 text-dark", style="white-space: pre-wrap;"),
                cls="border rounded-3 p-3 mb-2 bg-light" if item.get("is_internal") else "border rounded-3 p-3 mb-2 bg-white",
            )
            for item in messages
        ]
        status_options = ["new", "acknowledged", "investigating", "waiting_on_school", "resolved", "closed"]
        content = Div(
            Div(
                A("Back to support", href="/internal/platform/support", cls="text-decoration-none small mb-2 d-inline-block"),
                H1(ticket.get("subject") or "Support case", cls="fw-bold fs-2 mb-1 text-dark"),
                P(f"Opened {ticket.get('created_at', '')[:16].replace('T', ' ')}", cls="text-muted mb-0"),
                cls="mb-4",
            ),
            Row(
                Col(
                    Card(
                        Div(
                            Badge(_support_status_label(ticket.get("status", "new")), variant="success" if ticket.get("status") in {"resolved", "closed"} else "warning", pill=True),
                            Badge(ticket.get("severity", "normal").title(), variant="danger" if ticket.get("severity") in {"critical", "high"} else "secondary", pill=True),
                            cls="d-flex flex-wrap gap-2 mb-3",
                        ),
                        P(ticket.get("description") or "No description provided.", cls="text-dark", style="white-space: pre-wrap;"),
                        P(f"Category: {ticket.get('category', 'general').replace('_', ' ').title()}", cls="text-muted small mb-1"),
                        P(f"Page: {ticket.get('page_url') or 'Not recorded'}", cls="text-muted small mb-0"),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white mb-3",
                    ),
                    Card(
                        Strong("Conversation", cls="d-block text-dark mb-3"),
                        Div(*(message_cards or [EmptyState(title="No replies yet", description="Add a reply or internal note below.")]), id="support-message-list"),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white",
                    ),
                    span=12, lg=7,
                ),
                Col(
                    Card(
                        Strong("Update case", cls="d-block text-dark mb-3"),
                        Form(
                            _csrf(req),
                            Label("Status", cls="form-label"),
                            HtmlSelect(*(Option(_support_status_label(value), value=value, selected=value == ticket.get("status")) for value in status_options), name="status", cls="form-select rounded-3 mb-3"),
                            Label("Assigned to", cls="form-label"),
                            HtmlSelect(
                                Option("Leave unassigned", value="", selected=not ticket.get("assigned_to_user_id")),
                                *(Option(f"{member.get('full_name') or member.get('email')} Â· {member.get('role', '').replace('_', ' ').title()}", value=member["user_id"], selected=member["user_id"] == ticket.get("assigned_to_user_id")) for member in members),
                                name="assigned_to_user_id", cls="form-select rounded-3 mb-3",
                            ),
                            Label("Resolution note", cls="form-label"),
                            Textarea(name="resolution_note", placeholder="Optional note about the resolutionâ€¦", rows=4, cls="form-control rounded-3 mb-3", maxlength=5000),
                            Button("Save status", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Savingâ€¦"}),
                            action=f"/internal/platform/support/{ticket_id}/status", method="post",
                        ),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white mb-3",
                    ),
                    Card(
                        Strong("Send a message", cls="d-block text-dark mb-3"),
                        Form(
                            _csrf(req),
                            Label("Message", cls="form-label"),
                            Textarea(name="body", placeholder="Write a reply to the schoolâ€¦", rows=5, required=True, cls="form-control rounded-3 mb-3"),
                            Div(
                                Input(name="is_internal", type="checkbox", value="true", id="internal-note", cls="form-check-input me-2"),
                                Label("Internal note (not visible to school)", for_="internal-note", cls="form-check-label small"),
                                cls="form-check mb-3",
                            ),
                            Button("Send message", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Sendingâ€¦"}),
                            action=f"/internal/platform/support/{ticket_id}/message", method="post",
                        ),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white",
                    ),
                    span=12, lg=5,
                ),
                cls="g-3",
            ),
        )
        return _platform_shell(content, user, "platform-support", pop_flash(req), [("Platform operations", "/internal/platform"), ("Support", "/internal/platform/support"), ("Case", None)])

    @app.post("/internal/platform/support/{ticket_id}/status")
    async def platform_support_status_action(req: Request, ticket_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        response = await call_api(req, "PATCH", f"/platform/feedback/{ticket_id}", json={
            "status": form.get("status", "new"),
            "resolution_note": (form.get("resolution_note") or "").strip() or None,
            "assigned_to_user_id": (form.get("assigned_to_user_id") or "").strip() or None,
        })
        ok, data = unwrap(response)
        push_flash(req, data.get("message", "Support case updated.") if ok else data.get("message", "Could not update support case."), "success" if ok else "danger")
        return RedirectResponse(f"/internal/platform/support/{ticket_id}", status_code=303)

    @app.post("/internal/platform/support/{ticket_id}/message")
    async def platform_support_message_action(req: Request, ticket_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        response = await call_api(req, "POST", f"/platform/feedback/{ticket_id}/messages", json={
            "body": (form.get("body") or "").strip(),
            "is_internal": bool(form.get("is_internal")),
        })
        ok, data = unwrap(response)
        push_flash(req, data.get("message", "Message added.") if ok else data.get("message", "Could not add message."), "success" if ok else "danger")
        return RedirectResponse(f"/internal/platform/support/{ticket_id}", status_code=303)
