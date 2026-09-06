"""Role-aware dashboard (FRONTEND_SPEC sec 6.8 & UI_design/Dashboard.png).

Dashboard matching UI_design/Dashboard.png:
- Greeting header with role pill, date, and "+ Generate Exam" action
- 4 KPI metric cards (Generating, Under Review, Approved, Failed)
- 2-column layout: Recent Exams list (8 cols) + Proposals list (4 cols)
- Quick Actions horizontal cards at the bottom
"""

import asyncio
from datetime import datetime
from fasthtml.common import A, Div, H1, P, Span, Strong, Title
from starlette.requests import Request

from faststrap import Button, Card, Col, Container, EmptyState, Icon, Row

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login
from app.frontend.routes.exams import _create_modal


async def _load_exams(req: Request, status: str | None = None, workflow_state: str | None = None):
    """Fetch exams list; returns (ok, data)."""
    params = {"limit": "50"}
    if status:
        params["status"] = status
    if workflow_state:
        params["workflow_state"] = workflow_state
    resp = await call_api(req, "GET", "/exams", params=params)
    return unwrap(resp)


def _metric_card(label: str, value: int, icon: str, icon_class: str, href: str = "/app/exams"):
    """Single metric card matching UI_design/Dashboard.png."""
    return A(
        Div(
            Div(
                Icon(icon, cls="bi"),
                cls=f"app-metric-icon-wrap {icon_class}",
            ),
            Div(
                Div(str(value), cls="app-metric-value"),
                Div(label, cls="app-metric-label"),
            ),
            cls="app-metric-card",
        ),
        href=href,
        cls="text-decoration-none d-block h-100",
    )


def _status_badge_pill(status_text: str, badge_type: str = "review"):
    """Pill badge with exact colors from UI_design/Dashboard.png & Exams.png."""
    badge_cls = {
        "approved": "badge-status-approved",
        "under review": "badge-status-review",
        "teacher_review": "badge-status-review",
        "generating": "badge-status-generating",
        "draft": "badge-status-draft",
        "failed": "badge-status-failed",
        "accepted": "badge-status-accepted",
        "open": "badge-status-open",
        "generated": "badge-status-generating",
    }.get(badge_type.lower(), "badge-status-draft")
    return Span(status_text, cls=f"badge-status {badge_cls}")


def _recent_exam_item(exam: dict):
    """Item row in Recent Exams card matching UI_design/Dashboard.png."""
    eid = str(exam.get("id") or "")
    subject = exam.get("subject", "Untitled Exam")
    grade = exam.get("grade_level", "")
    total_marks = exam.get("total_marks", 0)
    workflow_state = exam.get("workflow_state") or exam.get("status") or "draft"

    if workflow_state == "approved":
        st_text, st_type = "Approved", "approved"
    elif workflow_state in {"teacher_review", "final_submitted_by_teacher", "refinement_requested"}:
        st_text, st_type = "Under Review", "under review"
    elif workflow_state == "generation_requested":
        st_text, st_type = "Generating", "generating"
    elif exam.get("status") == "failed":
        st_text, st_type = "Failed", "failed"
    else:
        st_text, st_type = "Draft", "draft"

    title_text = f"{grade} {subject} — Term Examination" if "Exam" not in subject else f"{grade} {subject}"

    return Div(
        Div(
            A(
                Strong(title_text, cls="text-dark d-block mb-1"),
                href=f"/app/exams/{eid}",
                cls="text-decoration-none",
            ),
            Div(f"{grade} · {total_marks} marks", cls="text-muted small"),
            cls="flex-grow-1",
        ),
        _status_badge_pill(st_text, st_type),
        cls="d-flex align-items-center justify-content-between py-3 border-bottom",
    )


def _proposal_item(prop: dict):
    """Item row in Proposals card matching UI_design/Dashboard.png."""
    pid = str(prop.get("id") or "")
    title = prop.get("title") or f"{prop.get('grade_level', '')} {prop.get('subject', '')} — Proposal"
    creator = prop.get("creator_name") or prop.get("requested_by") or "Teacher"
    status = prop.get("status") or "open"

    st_map = {
        "open": ("Open", "open"),
        "accepted": ("Accepted", "accepted"),
        "used": ("Generated", "generated"),
        "generated": ("Generated", "generated"),
        "rejected": ("Rejected", "failed"),
    }
    st_text, st_type = st_map.get(status.lower(), (status.title(), "draft"))

    return Div(
        Div(
            A(
                Strong(title, cls="text-dark d-block mb-1"),
                href=f"/app/proposals#{pid}",
                cls="text-decoration-none",
            ),
            Div(creator, cls="text-muted small"),
            cls="flex-grow-1",
        ),
        _status_badge_pill(st_text, st_type),
        cls="d-flex align-items-center justify-content-between py-3 border-bottom",
    )


def register_routes(app):
    @app.get("/app")
    async def dashboard(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)
        role = user.get("role") or ("Teacher" if user.get("account_type") == "individual_teacher" else "Staff")
        is_school_staff = user.get("account_type") == "school_staff" or role in {"school_admin", "teacher", "auditor"}

        # Parallel fetches with shared client
        (
            (ok_total, data_total),
            (ok_gen, data_gen),
            (ok_review, data_review),
            (ok_approved, data_approved),
            (ok_failed, data_failed),
        ) = await asyncio.gather(
            _load_exams(req),
            _load_exams(req, workflow_state="generation_requested"),
            _load_exams(req, workflow_state="teacher_review"),
            _load_exams(req, status="approved"),
            _load_exams(req, status="failed"),
        )

        exams_all = (data_total.get("exams") or []) if ok_total else []
        generating_count = len(data_gen.get("exams") or []) if ok_gen else 0
        review_count = len(data_review.get("exams") or []) if ok_review else 0
        approved_count = len(data_approved.get("exams") or []) if ok_approved else 0
        failed_count = len(data_failed.get("exams") or []) if ok_failed else 0

        # Load proposals if school staff
        proposals_list = []
        if is_school_staff:
            try:
                resp_prop = await call_api(req, "GET", "/exams/generation-proposals")
                ok_p, p_data = unwrap(resp_prop)
                if ok_p and isinstance(p_data, list):
                    proposals_list = p_data
            except Exception:
                pass

        # Greeting matching Dashboard.png
        user_first = (user.get("full_name") or user.get("email") or "there").split()[0]
        greeting = f"Good morning, {user_first}"
        date_str = datetime.now().strftime("%A, %d %B")

        header = Div(
            Div(
                H1(greeting, cls="fw-bold fs-2 mb-1 text-dark"),
                Div(
                    Span(date_str, cls="text-muted small me-2"),
                    Span(
                        role.replace("_", " ").title(),
                        cls="badge bg-light text-dark border",
                        style="font-size:0.75rem; vertical-align:middle",
                    ),
                    cls="d-flex align-items-center",
                ),
            ),
            Div(
                Button(
                    Icon("plus-lg", cls="bi me-1"),
                    "Generate Exam",
                    as_="a",
                    href="/app/exams/new",
                    variant="success",
                    cls="btn-brand px-4 py-2 fw-semibold",
                ),
                Button(
                    Icon("file-earmark-plus", cls="bi me-1"),
                    "New Exam",
                    type="button",
                    variant="outline-secondary",
                    cls="ms-2 px-3 py-2",
                    **{"data-bs-toggle": "modal", "data-bs-target": "#createExamModal"},
                ),
                cls="d-flex align-items-center gap-2 mt-3 mt-md-0",
            ),
            cls="d-flex flex-wrap justify-content-between align-items-center mb-4",
        )

        # 4 KPI cards row
        metrics_row = Row(
            Col(_metric_card("Exams Generating", generating_count, "lightning-charge-fill", "icon-blue-light", "/app/exams?status=generating"), span=12, sm=6, lg=3),
            Col(_metric_card("Under Review", review_count, "eye-fill", "icon-purple-light", "/app/exams?status=teacher_review"), span=12, sm=6, lg=3),
            Col(_metric_card("Approved", approved_count, "check-circle-fill", "icon-green-light", "/app/exams?status=approved"), span=12, sm=6, lg=3),
            Col(_metric_card("Failed (24h)", failed_count, "exclamation-triangle-fill", "icon-red-light", "/app/exams?status=failed"), span=12, sm=6, lg=3),
            g=3,
            cls="mb-4",
        )

        # Recent exams card
        if exams_all:
            recent_exams_body = Div(
                *[_recent_exam_item(e) for e in exams_all[:5]],
            )
        else:
            recent_exams_body = Div(
                P("No exams yet. Start by generating from the curriculum or creating a blank exam.", cls="text-muted small py-4 text-center"),
                A(
                    Icon("plus-circle", cls="bi me-1"),
                    "Generate with AI",
                    href="/app/exams/new",
                    cls="btn btn-sm btn-brand d-block mx-auto mb-2",
                    style="max-width: 180px",
                ),
            )

        recent_exams_card = Card(
            Div(
                Strong("Recent Exams", cls="fs-6 text-dark"),
                A("View all", href="/app/exams", cls="small text-brand text-decoration-none fw-semibold"),
                cls="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom",
            ),
            recent_exams_body,
            cls="p-3 h-100 shadow-sm border-0",
        )

        # Proposals widget or Overview widget for right column
        if is_school_staff and proposals_list:
            proposals_body = Div(
                *[_proposal_item(p) for p in proposals_list[:4]],
            )
        elif is_school_staff:
            proposals_body = Div(
                P("No open proposals yet. Teachers can submit proposals for exam generation.", cls="text-muted small py-4 text-center"),
                A(
                    Icon("lightbulb", cls="bi me-1"),
                    "New Proposal",
                    href="/app/proposals/new",
                    cls="btn btn-sm btn-outline-success d-block mx-auto mb-2",
                    style="max-width: 160px",
                ),
            )
        else:
            # Individual teacher curriculum coverage card
            proposals_body = Div(
                P("Official NERDC Curriculum & Scheme of Work", cls="fw-bold small text-dark mb-1"),
                P("Pre-Nursery to Primary 6 active and seeded with standard national learning objectives.", cls="text-muted small mb-3"),
                Div(
                    Div(Span("Mathematics, English, Basic Science", cls="small fw-semibold"), cls="mb-1"),
                    Div(Span("Social Studies, National Values, Languages", cls="small text-muted"), cls="mb-3"),
                    A(
                        Icon("book", cls="bi me-1"),
                        "Question Bank",
                        href="/app/bank",
                        cls="btn btn-sm btn-outline-secondary d-inline-block",
                    ),
                ),
                cls="py-2",
            )

        right_widget_card = Card(
            Div(
                Strong("Proposals" if is_school_staff else "Curriculum Coverage", cls="fs-6 text-dark"),
                A("View all", href="/app/proposals" if is_school_staff else "/app/bank", cls="small text-brand text-decoration-none fw-semibold"),
                cls="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom",
            ),
            proposals_body,
            cls="p-3 h-100 shadow-sm border-0",
        )

        # Quick Actions Row
        quick_actions_section = Div(
            H1("Quick Actions", cls="fs-6 fw-bold text-dark mt-4 mb-3"),
            Row(
                Col(
                    A(
                        Div(Icon("lightning-charge-fill", cls="bi"), cls="app-quick-action-icon"),
                        Div(
                            Strong("Generate Exam", cls="d-block text-dark small"),
                            Span("Start AI exam generation from curriculum", cls="text-muted", style="font-size:0.75rem"),
                        ),
                        href="/app/exams/new",
                        cls="app-quick-action",
                    ),
                    span=12,
                    md=4,
                ),
                Col(
                    A(
                        Div(Icon("file-earmark-plus", cls="bi"), cls="app-quick-action-icon"),
                        Div(
                            Strong("New Exam (Manual)", cls="d-block text-dark small"),
                            Span("Build questions manually without AI", cls="text-muted", style="font-size:0.75rem"),
                        ),
                        href="/app/exams/new/manual",
                        cls="app-quick-action",
                    ),
                    span=12,
                    md=4,
                ),
                Col(
                    A(
                        Div(Icon("book", cls="bi"), cls="app-quick-action-icon"),
                        Div(
                            Strong("Question Bank", cls="d-block text-dark small"),
                            Span("Explore and reuse verified questions", cls="text-muted", style="font-size:0.75rem"),
                        ),
                        href="/app/bank",
                        cls="app-quick-action",
                    ),
                    span=12,
                    md=4,
                ),
                g=3,
            ),
            cls="mb-4",
        )

        # Curriculum-first CTA: guides new teachers to the NERDC scheme deep-link
        # entry point (audit fix-list #5). Shown always; most prominent when empty.
        curriculum_cta = Card(
            Div(
                Div(Icon("journal-text", cls="bi fs-4"), cls="app-row-icon brand me-3"),
                Div(
                    Strong("Start from the curriculum", cls="d-block"),
                    P("Pick a class, subject and week from the NERDC scheme — we pre-fill the exam for you.", cls="text-muted small mb-0"),
                ),
                A(Icon("arrow-right-circle", cls="bi me-1"), "Open Curriculum Explorer",
                  href="/app/curriculum", cls="btn btn-brand rounded-pill px-4 flex-shrink-0"),
                cls="d-flex flex-wrap align-items-center gap-3 p-3",
            ),
            cls="border-0 shadow-sm rounded-4 mb-4 bg-white",
        )

        return AppShell(
            Title("Dashboard — SkuPhase"),
            Div(
                header,
                curriculum_cta,
                metrics_row,
                Row(
                    Col(recent_exams_card, span=12, lg=8),
                    Col(right_widget_card, span=12, lg=4),
                    g=4,
                    cls="mb-4",
                ),
                quick_actions_section,
                _create_modal(),
                id="dashboard-page",
            ),
            user=user,
            active="dashboard",
            flash=flash,
        )
