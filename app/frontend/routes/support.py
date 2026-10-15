"""School-facing feedback and durable notification inbox pages."""

from fasthtml.common import A, Div, Form, H1, H2, Input, Label, Option, P, Select as HtmlSelect, Span, Strong, Textarea, Title
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Badge, Button, Card, Col, EmptyState, Icon, Row

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _csrf(req: Request):
    token = req.session.get("csrf")
    return Input(name="csrf_token", value=token or "", type="hidden") if token else None


def _shell(content, user, active, flash, crumbs):
    return AppShell(Title("Support — SkuPhase"), content, user=user, active=active, flash=flash, crumbs=crumbs)


def register_routes(app):
    @app.get("/ui/notifications/badge")
    async def notification_badge(req: Request):
        """Render the navbar count from durable unread notifications only."""
        guard = ensure_login(req)
        if guard:
            return guard
        response = await call_api(req, "GET", "/notifications", params={"unread_only": True, "limit": 1})
        ok, data = unwrap(response)
        unread = int(data.get("unread", 0) or 0) if ok else 0
        return Span(
            str(unread) if unread else "",
            id="app-notification-badge",
            cls="app-bell-badge" if unread else "app-bell-badge d-none",
            aria_label=f"{unread} unread notifications" if unread else None,
            aria_hidden="true" if not unread else None,
        )

    @app.get("/app/feedback")
    async def feedback_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/feedback/mine")
        ok, data = unwrap(response)
        tickets = data.get("tickets", []) if ok else []
        report_cards = [
            A(
                Div(
                    Div(
                        Div(
                            Strong(item.get("subject") or "Feedback report", cls="support-report-subject"),
                            Badge(
                                (item.get("status") or "new").replace("_", " ").title(),
                                variant=("success" if item.get("status") in {"resolved", "closed"} else "warning" if item.get("status") in {"new", "investigating", "in_progress"} else "secondary"),
                                pill=True,
                                cls="support-status-badge",
                            ),
                            cls="support-report-title-row",
                        ),
                        Div(
                            Span((item.get("category") or "general").replace("_", " ").title(), cls="support-report-category"),
                            Span("·", aria_hidden="true", cls="text-muted"),
                            Span((item.get("created_at") or "")[:10] or "Date unavailable", cls="support-report-date"),
                            cls="d-flex align-items-center flex-wrap gap-2 mt-2",
                        ),
                        cls="support-report-content",
                    ),
                    Icon("arrow-up-right", cls="support-report-arrow"),
                    cls="support-report-row",
                ),
                href=f"/app/feedback/{item.get('ticket_id', '')}",
                cls="support-report-link",
                aria_label=f"Open report: {item.get('subject') or 'Feedback report'}",
            )
            for item in tickets
        ]
        history = (
            Div(*report_cards, cls="support-report-list")
            if report_cards
            else Div(
                Div(Icon("chat-square-text", cls="support-empty-icon"), cls="support-empty-icon-wrap"),
                Strong("No reports yet", cls="d-block text-dark mb-2"),
                P("When you send a report, you can follow its status and any reply here.", cls="text-muted small mb-3"),
                A("Report a problem", href="#report-problem", cls="btn btn-outline-success btn-sm rounded-pill px-3"),
                cls="support-empty-state",
            )
        )
        content = Div(
            Div(H1("Help & feedback", cls="fw-bold fs-2 mb-1 text-dark"), P("Tell us what happened so the SkuPhase team can improve or assist you.", cls="text-muted mb-0"), cls="support-page-heading mb-4"),
            Row(
                Col(
                    Card(
                        Div(Div(Icon("chat-square-dots", cls="support-panel-icon"), cls="support-panel-icon-wrap"), Div(H2("Report a problem", cls="h5 fw-semibold text-dark mb-1"), P("A few details will help us understand and reproduce the issue.", cls="text-muted small mb-0")), cls="support-panel-heading mb-4", id="report-problem"),
                        Form(
                            _csrf(req),
                            Label("Category", for_="feedback-category", cls="form-label fw-medium"),
                            HtmlSelect(
                                Option("Something is not working", value="bug"),
                                Option("Exam generation quality", value="exam_generation_quality"),
                                Option("Curriculum issue", value="curriculum"),
                                Option("PDF or export problem", value="export"),
                                Option("Account or access issue", value="account"),
                                Option("Feature request", value="feature_request"),
                                Option("General complaint", value="general"),
                                name="category", id="feedback-category", cls="form-select rounded-3",
                            ),
                            Div(Label("Short subject", for_="feedback-subject", cls="form-label fw-medium"), Input(type="text", name="subject", id="feedback-subject", required=True, maxlength="180", placeholder="e.g. Exam PDF downloads without a logo", cls="form-control rounded-3"), Span("Keep it brief; you can explain the details below.", cls="form-text"), cls="support-form-field"),
                            Label("What happened?", cls="form-label fw-medium"),
                            Textarea(name="description", placeholder="Describe the problem in your own words…", required=True, rows=5, cls="form-control rounded-3 mb-3"),
                            Label("How urgent is it?", cls="form-label fw-medium"),
                            HtmlSelect(Option("Normal", value="normal"), Option("High — core work is blocked", value="high"), Option("Critical — system unavailable", value="critical"), Option("Low — suggestion or cosmetic issue", value="low"), name="severity", cls="form-select rounded-3 mb-3"),
                            Input(type="hidden", name="page_url", value=str(req.url.path)),
                            Button("Submit feedback", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Sending…"}),
                            action="/app/feedback", method="post", cls="support-feedback-form",
                        ),
                        cls="border-0 shadow-sm rounded-4 p-4 p-lg-5 bg-white h-100 support-panel support-compose-panel",
                    ), span=12, lg=6,
                ),
                Col(Card(Div(Div(Icon("inbox", cls="support-panel-icon"), cls="support-panel-icon-wrap"), Div(H2("Your recent reports", cls="h5 fw-semibold text-dark mb-1"), P("Check the latest status or open a report to read our reply.", cls="text-muted small mb-0")), cls="support-panel-heading mb-4"), history, cls="border-0 shadow-sm rounded-4 p-4 p-lg-5 bg-white h-100 support-panel support-history-panel"), span=12, lg=6),
                cls="g-4 align-items-stretch",
            ),
            cls="support-page",
        )
        return _shell(content, user, "support", pop_flash(req), [("Help & feedback", None)])

    @app.get("/app/feedback/{ticket_id}")
    async def feedback_detail_page(req: Request, ticket_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", f"/feedback/{ticket_id}")
        ok, data = unwrap(response)
        if not ok:
            push_flash(req, data.get("message", "This feedback report is no longer available."), "danger")
            return RedirectResponse("/app/feedback", status_code=303)
        ticket = data.get("ticket", {})
        messages = data.get("messages", [])
        message_cards = [
            Card(
                Div(Strong("SkuPhase support", cls="text-dark"), Span(item.get("created_at", "")[:16].replace("T", " "), cls="text-muted small ms-2"), cls="mb-2"),
                P(item.get("body", ""), cls="mb-0 text-dark", style="white-space: pre-wrap;"),
                cls="border rounded-3 p-3 mb-2 bg-white",
            )
            for item in messages
        ]
        status = (ticket.get("status") or "new").replace("_", " ").title()
        content = Div(
            A("← Back to help & feedback", href="/app/feedback", cls="text-decoration-none small mb-3 d-inline-block"),
            H1(ticket.get("subject") or "Feedback report", cls="fw-bold fs-2 mb-1 text-dark"),
            P(f"Submitted {ticket.get('created_at', '')[:16].replace('T', ' ')}", cls="text-muted mb-4"),
            Row(
                Col(
                    Card(
                        Div(Badge(status, variant="success" if ticket.get("status") in {"resolved", "closed"} else "warning", pill=True), Badge((ticket.get("severity") or "normal").title(), variant="secondary", pill=True), cls="d-flex flex-wrap gap-2 mb-3"),
                        P(ticket.get("description") or "No description provided.", cls="text-dark", style="white-space: pre-wrap;"),
                        P(f"Category: {(ticket.get('category') or 'general').replace('_', ' ').title()}", cls="text-muted small mb-1"),
                        P(f"Status: {status}", cls="text-muted small mb-0"),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white mb-3",
                    ),
                    Card(
                        Strong("Conversation", cls="d-block text-dark mb-3"),
                        Div(*(message_cards or [EmptyState(title="No reply yet", description="The SkuPhase team will post updates here.")]), id="feedback-message-list"),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white",
                    ),
                    span=12, lg=8,
                ),
                Col(
                    Card(
                        Strong("What happens next", cls="d-block text-dark mb-2"),
                        P("We review every report and will post any response or resolution here. You can safely return to your work while we investigate.", cls="text-muted small mb-0"),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white",
                    ), span=12, lg=4,
                ),
                cls="g-3",
            ),
        )
        return _shell(content, user, "support", pop_flash(req), [("Help & feedback", "/app/feedback"), ("Report", None)])

    @app.post("/app/feedback")
    async def submit_feedback(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        response = await call_api(req, "POST", "/feedback", json={
            "category": form.get("category", "general"),
            "severity": form.get("severity", "normal"),
            "subject": form.get("subject", "").strip(),
            "description": form.get("description", "").strip(),
            "page_url": form.get("page_url"),
        })
        ok, data = unwrap(response)
        push_flash(req, data.get("message", "Feedback submitted.") if ok else data.get("message", "Could not submit feedback."), "success" if ok else "danger")
        return RedirectResponse("/app/feedback", status_code=303)

    @app.get("/app/notifications")
    async def notifications_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/notifications", params={"limit": 50})
        ok, data = unwrap(response)
        items = data.get("notifications", []) if ok else []
        cards = [
            A(
                Div(Strong(item["title"], cls="d-block text-dark"), P(item["body"], cls="text-muted small mb-1"), Span(item["created_at"][:16].replace("T", " "), cls="text-muted small"), cls="p-3"),
                href=item.get("target_url") or "/app/notifications",
                cls="text-decoration-none border-bottom d-block" + (" bg-light" if not item.get("is_read") else ""),
            )
            for item in items
        ]
        content = Div(
            Div(H1("Notifications", cls="fw-bold fs-2 mb-1 text-dark"), P(f"{data.get('unread', 0)} unread notification(s)", cls="text-muted mb-4")),
            Card(*(cards or [EmptyState(title="You are all caught up", description="Important SkuPhase events will appear here.")]), cls="border-0 shadow-sm rounded-4 p-0 bg-white overflow-hidden"),
        )
        return _shell(content, user, "support", pop_flash(req), [("Notifications", None)])
