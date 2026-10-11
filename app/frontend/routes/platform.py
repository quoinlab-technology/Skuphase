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
                Form(_csrf(req), Button("Mark all as read", type="submit", variant="light", cls="btn btn-outline-secondary rounded-pill", **{"data-loading-label": "Updating…"}), action="/internal/platform/notifications/read-all", method="post") if data.get("unread", 0) else None,
                cls="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4",
            ),
            Card(*(cards or [EmptyState(title="You are all caught up", description="Assigned support cases and operational alerts will appear here.")]), cls="border-0 shadow-sm rounded-4 p-0 bg-white overflow-hidden"),
        )
        return _platform_shell(content, user, "platform-notifications", pop_flash(req), [("Platform operations", "/internal/platform"), ("Notifications", None)])

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
                TCell(f"{item.get('target_type') or ''} {item.get('target_id') or ''}".strip() or "—"),
                TCell(Badge("Success" if item.get("success") else "Failed", variant="success" if item.get("success") else "danger", pill=True)),
                TCell(item.get("summary") or "—"),
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
                        Button("Filter", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Filtering…"}),
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
                                *(Option(f"{member.get('full_name') or member.get('email')} · {member.get('role', '').replace('_', ' ').title()}", value=member["user_id"], selected=member["user_id"] == ticket.get("assigned_to_user_id")) for member in members),
                                name="assigned_to_user_id", cls="form-select rounded-3 mb-3",
                            ),
                            Label("Resolution note", cls="form-label"),
                            Textarea(name="resolution_note", placeholder="Optional note about the resolution…", rows=4, cls="form-control rounded-3 mb-3", maxlength=5000),
                            Button("Save status", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Saving…"}),
                            action=f"/internal/platform/support/{ticket_id}/status", method="post",
                        ),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white mb-3",
                    ),
                    Card(
                        Strong("Send a message", cls="d-block text-dark mb-3"),
                        Form(
                            _csrf(req),
                            Label("Message", cls="form-label"),
                            Textarea(name="body", placeholder="Write a reply to the school…", rows=5, required=True, cls="form-control rounded-3 mb-3"),
                            Div(
                                Input(name="is_internal", type="checkbox", value="true", id="internal-note", cls="form-check-input me-2"),
                                Label("Internal note (not visible to school)", for_="internal-note", cls="form-check-label small"),
                                cls="form-check mb-3",
                            ),
                            Button("Send message", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Sending…"}),
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
