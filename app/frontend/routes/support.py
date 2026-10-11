"""School-facing feedback and durable notification inbox pages."""

from fasthtml.common import A, Div, Form, H1, Input, Label, Option, P, Select as HtmlSelect, Span, Strong, Textarea, Title
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Badge, Button, Card, Col, EmptyState, Icon, Row, Spinner, Table, TBody, TCell, THead, TRow

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
    @app.get("/app/feedback")
    async def feedback_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        response = await call_api(req, "GET", "/feedback/mine")
        ok, data = unwrap(response)
        tickets = data.get("tickets", []) if ok else []
        rows = [
            TRow(TCell(item["subject"]), TCell(item["category"].replace("_", " ").title()), TCell(Badge(item["status"].replace("_", " ").title(), variant="secondary", pill=True)), TCell(item["created_at"][:10]))
            for item in tickets
        ]
        history = Table(
            THead(TRow(TCell("Subject"), TCell("Category"), TCell("Status"), TCell("Date"))),
            TBody(*rows), hover=True, cls="app-table mb-0",
        ) if rows else EmptyState(title="No feedback submitted", description="When you report a problem, its status will appear here.")
        content = Div(
            H1("Help & feedback", cls="fw-bold fs-2 mb-1 text-dark"),
            P("Tell us what happened so the SkuPhase team can improve or assist you.", cls="text-muted mb-4"),
            Row(
                Col(
                    Card(
                        Strong("Report a problem", cls="d-block text-dark mb-3"),
                        Form(
                            _csrf(req),
                            Label("Category", cls="form-label"),
                            HtmlSelect(
                                Option("Something is not working", value="bug"),
                                Option("Exam generation quality", value="exam_generation_quality"),
                                Option("Curriculum issue", value="curriculum"),
                                Option("PDF or export problem", value="export"),
                                Option("Account or access issue", value="account"),
                                Option("Feature request", value="feature_request"),
                                Option("General complaint", value="general"),
                                name="category", cls="form-select rounded-3 mb-3",
                            ),
                            Input("subject", label="Short subject", required=True, maxlength=180, placeholder="What do you need help with?"),
                            Label("What happened?", cls="form-label"),
                            Textarea(name="description", placeholder="Describe the problem in your own words…", required=True, rows=5, cls="form-control rounded-3 mb-3"),
                            Label("Severity", cls="form-label"),
                            HtmlSelect(Option("Normal", value="normal"), Option("High — core work is blocked", value="high"), Option("Critical — system unavailable", value="critical"), Option("Low — suggestion or cosmetic issue", value="low"), name="severity", cls="form-select rounded-3 mb-3"),
                            Input("page_url", input_type="hidden", value=str(req.url.path)),
                            Button("Submit feedback", type="submit", variant="success", cls="btn-brand rounded-pill px-4", **{"data-loading-label": "Sending…"}),
                            action="/app/feedback", method="post",
                        ),
                        cls="border-0 shadow-sm rounded-4 p-4 bg-white",
                    ), span=12, lg=6,
                ),
                Col(Card(Strong("Your recent reports", cls="d-block text-dark mb-3"), history, cls="border-0 shadow-sm rounded-4 p-4 bg-white"), span=12, lg=6),
                cls="g-3",
            ),
        )
        return _shell(content, user, "support", pop_flash(req), [("Help & feedback", None)])

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
