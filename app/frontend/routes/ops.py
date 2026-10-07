"""Operations monitoring module (FRONTEND_SPEC sec 6.13 & UI_design/Operations.png).

Allows school administrators to monitor exam generation workers, system health,
queue latency, and operational throughput.
"""

from fasthtml.common import A, Div, H1, H2, P, Span, Strong, Title
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Alert, Badge, Button, Card, Col, Container, Icon, Row, Spinner

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import Flash, pop_flash, show_toast
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login
from app.config.settings import get_settings


async def _ops_content(req: Request, htmx: bool = False):
    """Build the ops page content (shared by full page and HTMX partial).

    ``htmx=True`` switches the role-guard failure from an inline Flash to a
    ModernToast, per the feedback rules (HTMX partials use toasts, full-page
    responses use Flash).
    """
    user = current_user(req) or {}
    role = user.get("role") or ""
    account_type = user.get("account_type") or ""
    if role != "school_admin":
        if htmx:
            return show_toast("Access restricted to school administrators.", "danger")
        return Flash("Access restricted to school administrators.", "danger")

    resp_health = await call_api(req, "GET", "/ops/health")
    ok_h, health_data = unwrap(resp_health)
    health = health_data if ok_h else {"status": "degraded", "version": "—"}

    resp_stats = await call_api(req, "GET", "/ops/stats")
    ok_s, stats_data = unwrap(resp_stats)
    stats = stats_data if ok_s else {}
    resp_classes = await call_api(req, "GET", "/curriculum/classes", params={"board": "NERDC"})
    ok_c, classes_data = unwrap(resp_classes)

    status_str = health.get("status", "ok").upper()
    exam_stats = stats.get("exams") if isinstance(stats.get("exams"), dict) else {}
    generating = exam_stats.get("generating_draft", "—")
    under_review = exam_stats.get("under_review", "—")
    approved = exam_stats.get("approved", "—")
    failed = exam_stats.get("failed_last_24h", "—")
    settings = get_settings()
    db_label = (health.get("dependencies") or {}).get("database", "unavailable") if isinstance(health, dict) else "unavailable"
    curriculum_label = f"Loaded ({len(classes_data.get('classes', []))} levels)" if ok_c and isinstance(classes_data, dict) else "Unavailable"
    ai_label = "Configured" if settings.groq_api_key or settings.openrouter_api_key else "Not configured"

    header = Div(
        Div(
            H1("System Operations", cls="fw-bold fs-2 text-dark mb-1"),
            P("Real-time monitoring of AI generation workers, queue throughput, and service health.", cls="text-muted small mb-0"),
        ),
        Div(
            Button(
                Icon("arrow-clockwise", cls="bi me-1"),
                "Refresh",
                type="button",
                hx_get="/ui/ops/panel",
                hx_target="#ops-panel",
                hx_swap="outerHTML",
                hx_indicator="#ops-refresh-spinner",
                variant="outline-secondary",
                size="sm",
                cls="rounded-pill px-3 py-2",
            ),
            Div(
                Spinner(variant="success", size="sm", cls="me-2"),
                Span("Updating...", cls="small text-muted"),
                id="ops-refresh-spinner",
                cls="htmx-indicator ms-2 d-inline-flex align-items-center",
            ),
            cls="d-flex align-items-center mt-2 mt-sm-0",
        ),
        cls="d-flex flex-wrap justify-content-between align-items-center mb-4",
    )

    metrics = Row(
        Col(
            Div(
                Div(Icon("check-circle-fill", cls="bi"), cls="app-metric-icon-wrap icon-green-light"),
                Div(Div(status_str, cls="app-metric-value fs-4 text-success"), Div("System Status", cls="app-metric-label")),
                cls="app-metric-card",
            ),
            span=6, lg=3,
        ),
        Col(
            Div(
                Div(Icon("cpu-fill", cls="bi"), cls="app-metric-icon-wrap icon-blue-light"),
                Div(Div(str(generating), cls="app-metric-value"), Div("Generating drafts", cls="app-metric-label")),
                cls="app-metric-card",
            ),
            span=6, lg=3,
        ),
        Col(
            Div(
                Div(Icon("hourglass-split", cls="bi"), cls="app-metric-icon-wrap icon-purple-light"),
                Div(Div(str(under_review), cls="app-metric-value"), Div("Under review", cls="app-metric-label")),
                cls="app-metric-card",
            ),
            span=6, lg=3,
        ),
        Col(
            Div(
                Div(Icon("graph-up-arrow", cls="bi"), cls="app-metric-icon-wrap icon-amber-light"),
                Div(Div(str(approved), cls="app-metric-value"), Div("Approved exams", cls="app-metric-label")),
                cls="app-metric-card",
            ),
            span=6, lg=3,
        ),
        Col(
            Div(
                Div(Icon("exclamation-triangle", cls="bi"), cls="app-metric-icon-wrap icon-red-light"),
                Div(Div(str(failed), cls="app-metric-value"), Div("Failed (24h)", cls="app-metric-label")),
                cls="app-metric-card",
            ),
            span=6, lg=3,
        ),
        cls="g-3 mb-4",
    )

    service_card = Card(
        Strong("Service Components", cls="fs-6 text-dark d-block mb-3"),
        Div(
            Div(
                Span("FastAPI Core Service", cls="small fw-semibold"),
                Span("Healthy" if ok_h else "Unavailable", cls=f"badge {'bg-success-subtle text-success' if ok_h else 'bg-danger-subtle text-danger'} rounded-pill px-2 py-1 small"),
                cls="d-flex justify-content-between align-items-center py-2 border-bottom",
            ),
            Div(
                Span("PostgreSQL Database", cls="small fw-semibold"),
                Span(db_label.title(), cls=f"badge {'bg-success-subtle text-success' if db_label == 'healthy' else 'bg-danger-subtle text-danger'} rounded-pill px-2 py-1 small"),
                cls="d-flex justify-content-between align-items-center py-2 border-bottom",
            ),
            Div(
                Span("Curriculum & Scheme Seed Engine", cls="small fw-semibold"),
                Span(curriculum_label, cls=f"badge {'bg-success-subtle text-success' if ok_c else 'bg-warning-subtle text-warning-emphasis'} rounded-pill px-2 py-1 small"),
                cls="d-flex justify-content-between align-items-center py-2 border-bottom",
            ),
            Div(
                Span("AI Providers (Groq/OpenRouter)", cls="small fw-semibold"),
                Span(ai_label, cls=f"badge {'bg-success-subtle text-success' if ai_label == 'Configured' else 'bg-warning-subtle text-warning-emphasis'} rounded-pill px-2 py-1 small"),
                cls="d-flex justify-content-between align-items-center py-2 border-bottom",
            ),
            Div(
                Span("PDF Export Engine (ReportLab)", cls="small fw-semibold"),
                Span("Ready", cls="badge bg-success-subtle text-success rounded-pill px-2 py-1 small"),
                cls="d-flex justify-content-between align-items-center py-2",
            ),
        ),
        cls="p-4 border-0 shadow-sm rounded-4 h-100",
    )

    architecture_card = Card(
        Strong("Architecture & Curriculum Notice", cls="fs-6 text-dark d-block mb-3"),
        Div(
            P(
                "SkuPhase operates on a seeded Nigerian National Curriculum (NERDC) and Scheme of Work foundation. "
                "All exam generations query structured curriculum learning outcomes rather than ungrounded document embeddings.",
                cls="text-muted small mb-3",
            ),
            Div(
                Div(Span("Curriculum Scope: ", cls="fw-bold small"), Span("Pre-Nursery through SSS 3", cls="small text-muted")),
                Div(Span("Question Generator: ", cls="fw-bold small"), Span("Curriculum-seeded prompt engine", cls="small text-muted")),
                Div(Span("Quality Gate: ", cls="fw-bold small"), Span("Multi-dimensional automated preflight", cls="small text-muted")),
                cls="p-3 rounded-3 bg-light border-start border-3 border-success",
            ),
        ),
        cls="p-4 border-0 shadow-sm rounded-4 h-100",
    )

    return Div(
        header,
        metrics,
        Row(
            Col(service_card, span=12, lg=6),
            Col(architecture_card, span=12, lg=6),
            g=4,
        ),
        id="ops-panel",
        cls="pb-5 mb-5",
        hx_get="/ui/ops/panel",
        hx_trigger="every 30s",
        hx_swap="outerHTML",
    )


def register_routes(app):
    @app.get("/ui/ops/panel")
    async def ops_panel_partial(req: Request):
        """HTMX partial: refresh just the ops metrics/content."""
        guard = ensure_login(req)
        if guard:
            return guard
        return await _ops_content(req, htmx=True)

    @app.get("/app/ops")
    async def operations_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)
        content = await _ops_content(req)
        return AppShell(
            Title("Operations — SkuPhase"),
            content,
            user=user,
            active="ops",
            flash=flash,
            crumbs=[("Administration", "/app/admin"), ("Operations", None)],
        )
