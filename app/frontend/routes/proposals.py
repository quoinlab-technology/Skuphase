"""Generation Proposals governance module (FRONTEND_SPEC sec 6.9 & UI_design/Proposals.png).

Allows school staff to submit exam generation proposals and school admins to review
and trigger automated exam generation.
"""

from urllib.parse import urlencode
from fasthtml.common import (
    A,
    Div,
    Form,
    H1,
    H2,
    Input,
    Label,
    Option,
    P,
    Script,
    Span,
    Strong,
    Textarea,
    Title,
    to_xml,
)
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from faststrap import Alert, Badge, Button, Card, Col, Container, EmptyState, FormGroup, Icon, Row, Select, Spinner

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash, set_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login
from app.services.curriculum_taxonomy import ALL_SUBJECTS, CLASS_LEVELS


def _status_pill(status: str) -> Span:
    status_lower = (status or "open").lower()
    cls_map = {
        "open": "badge-status-open",
        "in_review": "badge-status-review",
        "accepted": "badge-status-accepted",
        "generated": "badge-status-generating",
        "used": "badge-status-generating",
        "rejected": "badge-status-rejected",
    }
    badge_cls = cls_map.get(status_lower, "badge-status-draft")
    return Span(status.replace("_", " ").title(), cls=f"badge-status {badge_cls}")


def _proposal_card(prop: dict, is_admin: bool) -> Div:
    pid = str(prop.get("id") or "")
    subject = prop.get("subject", "General Subject")
    grade = prop.get("grade_level", "Primary 1")
    term = prop.get("term") or "Term"
    weeks = prop.get("selected_weeks") or []
    weeks_str = f"Weeks {', '.join(str(w) for w in weeks)}" if weeks else "All scheme weeks"
    outcomes = prop.get("desired_outcomes") or "Generate end-of-term examination questions covering national curriculum standards."
    instructions = prop.get("custom_instructions") or "Focus on core learning objectives and performance activities."
    status = prop.get("status") or "open"
    created = (prop.get("created_at") or "")[:10]
    author_name = prop.get("teacher_name") or prop.get("created_by_name") or "Teacher"
    author_role = prop.get("teacher_role") or "Teacher"

    # Action buttons per status
    action_btns = []
    if is_admin and status in {"open", "accepted"}:
        action_btns.append(
            Form(
                # Audit #4: the backend GenerateFromProposalRequest requires
                # sections; carry the proposal context through so the handler
                # can build a valid payload (422 fix).
                Input(type="hidden", name="term", value=term or ""),
                Input(type="hidden", name="selected_weeks", value=",".join(str(w) for w in weeks)),
                Input(type="hidden", name="desired_outcomes", value=outcomes),
                Button(
                    Icon("stars", cls="bi me-1"),
                    "Generate Exam",
                    type="submit",
                    variant="success",
                    size="sm",
                    cls="rounded-pill px-3 me-2",
                ),
                action=f"/app/proposals/{pid}/generate",
                method="post",
                cls="d-inline",
            )
        )
        action_btns.append(
            Button(
                "Review",
                type="button",
                cls="btn btn-sm btn-outline-dark rounded-pill px-3",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#reviewModal-{pid}"},
            )
        )
    elif status in {"generated", "used"}:
        action_btns.append(
            A(
                Icon("eye", cls="bi me-1"),
                "View Exam",
                href="/app/exams",
                cls="btn btn-sm btn-outline-secondary rounded-pill px-3",
            )
        )

    # Review modal matching Proposals3.png
    review_modal = Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Review Proposal", cls="fs-5 fw-bold text-dark d-block"),
                        Span(f"{grade} {subject}", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Div(
                    P("Request Description", cls="small fw-bold text-dark mb-1"),
                    Div(
                        P(outcomes, cls="small text-muted mb-0"),
                        cls="p-3 bg-light rounded-3 mb-3 border",
                    ),
                    Form(
                        Div(
                            Label("Admin Note (optional)", cls="form-label small fw-bold"),
                            Textarea(
                                "admin_note",
                                rows="3",
                                placeholder="e.g. Approved. Will use official curriculum scheme...",
                                cls="form-control mb-3",
                            ),
                            cls="mb-3",
                        ),
                        Div(
                            Button("Cancel", type="button", variant="light", cls="btn btn-light rounded-pill px-3 me-2", **{"data-bs-dismiss": "modal"}),
                            Button(
                                Icon("x-circle", cls="bi me-1 text-danger"),
                                "Reject",
                                type="submit",
                                variant="outline-danger",
                                cls="rounded-pill px-3 me-2",
                            ),
                            cls="d-flex justify-content-end",
                        ),
                        # Audit #5: Reject previously posted to the generate
                        # route (which ignored `action`), so rejecting actually
                        # generated an exam. Post to the dedicated reject route.
                        action=f"/app/proposals/{pid}/reject",
                        method="post",
                    ),
                    Form(
                        # Accept & Generate needs the proposal context so the
                        # backend sections payload can be built (audit #4).
                        Input(type="hidden", name="term", value=term or ""),
                        Input(type="hidden", name="selected_weeks", value=",".join(str(w) for w in weeks)),
                        Input(type="hidden", name="desired_outcomes", value=outcomes),
                        Div(
                            Button(
                                Icon("check-circle-fill", cls="bi me-1"),
                                "Accept & Generate",
                                type="submit",
                                variant="success",
                                cls="rounded-pill px-3",
                            ),
                            cls="d-flex justify-content-end mt-2",
                        ),
                        action=f"/app/proposals/{pid}/generate",
                        method="post",
                    ),
                    cls="modal-body pt-1 pb-4 px-4",
                ),
                cls="modal-content shadow-lg border-0 rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"reviewModal-{pid}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )

    return Div(
        Div(
            # Top card row: icon, metadata, actions, collapse chevron
            Div(
                Div(Icon("stars", cls="bi fs-5"), cls="app-row-icon ai me-3"),
                Div(
                    Div(
                        Strong(f"{grade} {subject}", cls="fs-6 text-dark me-2 text-truncate", style="max-width: 22rem;"),
                        _status_pill(status),
                        cls="d-flex align-items-center mb-1",
                    ),
                    Div(
                        Span(f"{subject} · {grade}", cls="text-muted small me-2"),
                        Span(f"Requested by {author_name}", cls="text-muted small me-1"),
                        Span(author_role, cls="badge bg-light text-secondary border me-2", style="font-size:0.7rem;"),
                        Span(created, cls="text-muted small"),
                        cls="d-flex flex-wrap align-items-center",
                    ),
                    cls="flex-grow-1",
                ),
                Div(
                    *action_btns,
                    Button(
                        Icon("chevron-down", cls="bi"),
                        type="button",
                        cls="btn btn-link text-muted p-1 ms-2",
                        **{"data-bs-toggle": "collapse", "data-bs-target": f"#prop-body-{pid}", "aria-label": "Toggle details"},
                    ),
                    cls="d-flex align-items-center ms-3",
                ),
                cls="d-flex align-items-center p-3",
            ),
            # Collapsible body matching Proposals2.png
            Div(
                Div(
                    Div(
                        P("Request Description", cls="small fw-bold text-secondary mb-1"),
                        Div(
                            P(outcomes, cls="small text-dark mb-0"),
                            cls="p-3 bg-light rounded-3 mb-3 border",
                        ),
                        P("Admin Note", cls="small fw-bold text-secondary mb-1"),
                        Div(
                            P(instructions or "Approved and aligned with current term scheme of work.", cls="small text-muted mb-0"),
                            cls="p-3 bg-light rounded-3 border",
                        ),
                        cls="p-3 pt-0",
                    ),
                    id=f"prop-body-{pid}",
                    cls="collapse",
                ),
            ),
            cls="card shadow-sm border-0 mb-3 rounded-3",
            id=f"proposal-{pid}",
        ),
        review_modal,
    )


def _sort_proposals(props: list, sort_by: str) -> list:
    if sort_by == "oldest":
        return sorted(props, key=lambda p: p.get("created_at") or "")
    elif sort_by == "subject_asc":
        return sorted(props, key=lambda p: (p.get("subject") or "").lower())
    elif sort_by == "grade":
        return sorted(props, key=lambda p: (p.get("grade_level") or "").lower())
    else:  # newest default
        return sorted(props, key=lambda p: p.get("created_at") or "", reverse=True)


def _render_proposals_view(all_props: list, is_admin: bool, status_filter: str = "", q: str = "", sort_by: str = "newest"):
    # Counts
    counts = {
        "all": len(all_props),
        "open": sum(1 for p in all_props if (p.get("status") or "").lower() == "open"),
        "accepted": sum(1 for p in all_props if (p.get("status") or "").lower() == "accepted"),
        "generated": sum(1 for p in all_props if (p.get("status") or "").lower() in {"generated", "used"}),
        "rejected": sum(1 for p in all_props if (p.get("status") or "").lower() == "rejected"),
    }

    # Filter
    filtered = all_props
    if status_filter:
        filtered = [p for p in filtered if (p.get("status") or "").lower() == status_filter.lower()]
    if q:
        filtered = [
            p for p in filtered
            if q in (p.get("subject", "") + " " + p.get("grade_level", "") + " " + p.get("desired_outcomes", "")).lower()
        ]
    filtered = _sort_proposals(filtered, sort_by)

    def _pill(label: str, key: str):
        active_cls = " active" if status_filter == key else ""
        cnt = counts.get(key or "all", 0)
        href_query = f"/app/proposals?status={key}" if key else "/app/proposals"
        return A(
            f"{label} ({cnt})",
            href=href_query,
            cls=f"app-filter-pill{active_cls}",
            hx_get=f"/ui/proposals/list?status={key}",
            hx_target="#proposals-content",
            hx_swap="outerHTML",
            hx_include="#proposals-filter-wrapper input, #proposal-sort-select",
            hx_indicator="#proposals-spinner",
            onclick=f"const el=document.getElementById('proposal-active-status'); if(el) el.value='{key}';",
        )

    pills = Div(
        _pill("All", ""),
        _pill("Open", "open"),
        _pill("Accepted", "accepted"),
        _pill("Generated", "generated"),
        _pill("Rejected", "rejected"),
        cls="d-flex gap-2 flex-wrap mb-3",
    )

    search_and_sort = Div(
        # Search input with live HTMX search
        Div(
            Icon("search", cls="bi text-muted position-absolute", style="top:0.75rem; left:1rem; font-size:1rem;"),
            Input(
                name="q",
                value=q,
                placeholder="Search proposals by subject, grade, or outcome...",
                cls="form-control rounded-pill ps-5 py-2 border shadow-sm",
                style="background:#fff;",
                id="proposal-search-input",
                hx_get="/ui/proposals/list",
                hx_target="#proposals-content",
                hx_swap="outerHTML",
                hx_trigger="input changed delay:300ms, search",
                hx_include="#proposals-filter-wrapper input, #proposal-sort-select",
                hx_indicator="#proposals-spinner",
            ),
            cls="position-relative flex-grow-1",
            style="max-width: 580px;",
        ),
        # Sort dropdown
        Div(
            Label("Sort:", cls="small text-muted fw-semibold me-2 mb-0 d-none d-sm-inline"),
            Select(
                "sort",
                ("newest", "Newest First", sort_by == "newest" or not sort_by),
                ("oldest", "Oldest First", sort_by == "oldest"),
                ("subject_asc", "Subject (A-Z)", sort_by == "subject_asc"),
                ("grade", "Grade Level", sort_by == "grade"),
                id="proposal-sort-select",
                cls="form-select rounded-pill border py-2 px-3 fw-medium small shadow-sm",
                style="background-color: #fff; min-width: 155px; font-size: 0.85rem;",
                hx_get="/ui/proposals/list",
                hx_target="#proposals-content",
                hx_swap="outerHTML",
                hx_trigger="change",
                hx_include="#proposals-filter-wrapper input",
                hx_indicator="#proposals-spinner",
            ),
            cls="d-flex align-items-center ms-sm-3 mt-2 mt-sm-0",
        ),
        # Faststrap Spinner for visual loading feedback
        Div(
            Spinner(variant="success", size="sm", cls="me-2"),
            Span("Updating...", cls="small text-muted"),
            id="proposals-spinner",
            cls="htmx-indicator ms-3 d-inline-flex align-items-center",
        ),
        id="proposals-filter-wrapper",
        cls="d-flex flex-wrap align-items-center justify-content-between mb-4",
    )

    if filtered:
        cards = [_proposal_card(p, is_admin) for p in filtered]
        list_content = Div(*cards, id="proposals-items-list")
    elif not all_props:
        list_content = EmptyState(
            title="How proposals work",
            description="Teachers describe the exam they need. A school admin reviews the request and generates the exam. Everyone can then refine, preflight and export it.",
            action=Button("Submit Proposal", as_="a", href="/app/proposals/new", cls="btn-brand"),
        )
    else:
        list_content = EmptyState(
            title="No proposals found",
            description="No proposals match the current filter. Try selecting a different status or clearing search.",
            action=Button("Submit Proposal", as_="a", href="/app/proposals/new", cls="btn-brand"),
        )

    return Div(
        Input(type="hidden", name="status", value=status_filter, id="proposal-active-status"),
        pills,
        search_and_sort,
        list_content,
        id="proposals-content",
    )


def register_routes(app):
    # ------------------------------------------------------------------
    # HTMX partial: returns just #proposals-content (pills + search + list)
    # ------------------------------------------------------------------
    @app.get("/ui/proposals/list")
    async def proposals_list_partial(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        account_type = user.get("account_type") or ""
        role = user.get("role") or ""
        is_admin = role == "school_admin"

        if account_type == "individual_teacher":
            push_flash(req, "Generation proposals are a school feature. As an individual teacher, you can generate exams directly from your dashboard.", "info")
            return RedirectResponse("/app", status_code=303)

        status_filter = req.query_params.get("status", "").strip()
        q = req.query_params.get("q", "").strip().lower()
        sort_by = req.query_params.get("sort", "newest").strip().lower()

        resp = await call_api(req, "GET", "/exams/generation-proposals?include_closed=true")
        ok, data = unwrap(resp)
        all_props = data if (ok and isinstance(data, list)) else []

        content = _render_proposals_view(all_props, is_admin, status_filter, q, sort_by)

        # Build clean push URL
        url_parts = []
        if status_filter:
            url_parts.append(f"status={status_filter}")
        if q:
            url_parts.append(f"q={q}")
        if sort_by and sort_by != "newest":
            url_parts.append(f"sort={sort_by}")
        push_url = "/app/proposals" + (f"?{'&'.join(url_parts)}" if url_parts else "")

        return HTMLResponse(to_xml(content), headers={"HX-Push-Url": push_url})

    # ------------------------------------------------------------------
    # Full page
    # ------------------------------------------------------------------
    @app.get("/app/proposals")
    async def proposals_list(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        account_type = user.get("account_type") or ""
        role = user.get("role") or ""
        is_admin = role == "school_admin"
        flash = pop_flash(req)

        # Individual teachers are not part of a school and cannot access proposals.
        if account_type == "individual_teacher":
            push_flash(req, "Generation proposals are a school feature. As an individual teacher, you can generate exams directly from your dashboard.", "info")
            return RedirectResponse("/app", status_code=303)

        status_filter = req.query_params.get("status", "").strip()
        q = req.query_params.get("q", "").strip().lower()
        sort_by = req.query_params.get("sort", "newest").strip().lower()

        resp = await call_api(req, "GET", "/exams/generation-proposals?include_closed=true")
        ok, data = unwrap(resp)
        all_props = data if (ok and isinstance(data, list)) else []

        # If this is an HTMX request to /app/proposals, return the partial directly
        if req.headers.get("hx-request") or req.headers.get("HX-Request"):
            content = _render_proposals_view(all_props, is_admin, status_filter, q, sort_by)
            url_parts = []
            if status_filter:
                url_parts.append(f"status={status_filter}")
            if q:
                url_parts.append(f"q={q}")
            if sort_by and sort_by != "newest":
                url_parts.append(f"sort={sort_by}")
            push_url = "/app/proposals" + (f"?{'&'.join(url_parts)}" if url_parts else "")
            return HTMLResponse(to_xml(content), headers={"HX-Push-Url": push_url})

        proposals_view = _render_proposals_view(all_props, is_admin, status_filter, q, sort_by)

        header = Div(
            Div(
                H1("Generation Proposals", cls="fw-bold fs-2 text-dark mb-1"),
                P("Staff requests for admin-approved exam generation from curriculum.", cls="text-muted small mb-0"),
            ),
            Button(
                Icon("plus-lg", cls="bi me-1"),
                "New Proposal",
                as_="a",
                href="/app/proposals/new",
                variant="success",
                cls="btn btn-brand rounded-pill px-4 py-2 text-white fw-semibold",
                style="background-color: #00412E !important; border: none;",
            ),
            cls="d-flex flex-wrap justify-content-between align-items-center mb-4",
        )

        return AppShell(
            Title("Generation Proposals — SkuPhase"),
            Div(
                header,
                proposals_view,
            ),
            user=user,
            active="proposals",
            flash=flash,
            crumbs=[("Generation Proposals", None)],
            bell_count=req.session.get("bell_count"),
        )

    @app.get("/app/proposals/new")
    async def proposals_new_form(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)
        qp = req.query_params

        default_grade = qp.get("grade_level") or qp.get("class_level") or "Primary 4"
        default_subject = qp.get("subject") or "Mathematics"
        default_term = qp.get("term") or "First Term"
        default_weeks = qp.get("selected_weeks") or qp.get("weeks") or ""
        default_outcomes = qp.get("desired_outcomes") or ""

        grades = [(label, label) for label in CLASS_LEVELS]
        subjects = [(label, label) for label in ALL_SUBJECTS]

        # Parse pre-selected weeks
        preselected_weeks = set()
        if default_weeks:
            for part in default_weeks.replace(";", ",").split(","):
                part = part.strip()
                if part.isdigit():
                    preselected_weeks.add(int(part))

        week_toggle_buttons = []
        for w in range(1, 13):
            is_active = w in preselected_weeks
            week_toggle_buttons.append(
                Button(
                    f"W{w}",
                    type="button",
                    cls=f"btn btn-sm rounded-pill px-3 py-1 me-1 mb-2 week-toggle-btn {'btn-dark text-white fw-semibold' if is_active else 'btn-light border text-muted'}",
                    **{"data-week": str(w), "onclick": "toggleProposalWeek(this)"},
                )
            )

        weeks_summary_text = (
            f"Selected: Weeks {', '.join(str(w) for w in sorted(preselected_weeks))}"
            if preselected_weeks
            else "No specific weeks selected (covers full term)"
        )

        form = Form(
            Card(
                Row(
                    Col(
                        Label("Grade Level", cls="form-label text-muted small fw-medium mb-1"),
                        Select(
                            "grade_level",
                            *grades,
                            value=default_grade,
                            cls="form-select rounded-3 border-0 py-2 px-3 fw-medium",
                            style="background-color: #F4F6F4; font-size: 0.92rem;",
                        ),
                        md=6,
                        cls="mb-3",
                    ),
                    Col(
                        Label("Subject", cls="form-label text-muted small fw-medium mb-1"),
                        Select(
                            "subject",
                            *subjects,
                            value=default_subject,
                            cls="form-select rounded-3 border-0 py-2 px-3 fw-medium",
                            style="background-color: #F4F6F4; font-size: 0.92rem;",
                        ),
                        md=6,
                        cls="mb-3",
                    ),
                ),
                Row(
                    Col(
                        Label("Term", cls="form-label text-muted small fw-medium mb-1"),
                        Select(
                            "term",
                            ("First Term", "First Term"),
                            ("Second Term", "Second Term"),
                            ("Third Term", "Third Term"),
                            value=default_term,
                            cls="form-select rounded-3 border-0 py-2 px-3 fw-medium",
                            style="background-color: #F4F6F4; font-size: 0.92rem;",
                        ),
                        md=6,
                        cls="mb-3",
                    ),
                    Col(
                        Div(
                            Label("Scheme of Work Weeks", cls="form-label text-muted small fw-medium mb-1 d-block"),
                            Div(
                                Button(
                                    "All W1–12",
                                    type="button",
                                    cls="btn btn-sm btn-link text-decoration-none p-0 text-success fw-medium me-2",
                                    onclick="toggleAllProposalWeeks(true)",
                                    style="font-size:0.8rem;",
                                ),
                                Span("·", cls="text-muted me-2"),
                                Button(
                                    "Clear",
                                    type="button",
                                    cls="btn btn-sm btn-link text-decoration-none p-0 text-muted fw-medium",
                                    onclick="toggleAllProposalWeeks(false)",
                                    style="font-size:0.8rem;",
                                ),
                                cls="d-inline-flex align-items-center mb-1",
                            ),
                            Div(*week_toggle_buttons, cls="d-flex flex-wrap align-items-center"),
                            Input(type="hidden", name="selected_weeks", id="proposal-weeks-input", value=default_weeks),
                            Span(weeks_summary_text, id="proposal-weeks-hint", cls="small text-muted d-block mt-1"),
                        ),
                        md=6,
                        cls="mb-3",
                    ),
                ),
                Div(
                    Label("Desired Learning Outcomes & Key Topics", cls="form-label text-muted small fw-medium mb-1"),
                    Textarea(
                        default_outcomes,
                        name="desired_outcomes",
                        placeholder="Describe key topics and curriculum standards to assess (min 10 characters)...",
                        rows=4,
                        cls="form-control rounded-3 border-0 p-3",
                        style="background-color: #F4F6F4; font-size: 0.92rem;",
                        required=True,
                    ),
                    cls="mb-3",
                ),
                Div(
                    Label("Custom Instructions for Generation (Optional)", cls="form-label text-muted small fw-medium mb-1"),
                    Textarea(
                        name="custom_instructions",
                        placeholder="e.g. Focus on word problems and basic fractions. Include clear explanations and diagrams.",
                        rows=3,
                        cls="form-control rounded-3 border-0 p-3",
                        style="background-color: #F4F6F4; font-size: 0.92rem;",
                    ),
                    cls="mb-4",
                ),
                Div(
                    A("Cancel", href="/app/proposals", cls="btn btn-outline-secondary rounded-pill px-4 py-2 me-2"),
                    Button(
                        "Submit Proposal",
                        type="submit",
                        variant="success",
                        cls="btn btn-brand rounded-pill px-4 py-2 text-white fw-semibold",
                        style="background-color: #00412E !important; border: none;",
                    ),
                    cls="d-flex justify-content-end",
                ),
                cls="bg-white rounded-4 border p-4 p-md-5 shadow-sm mb-4",
            ),
            Script("""
            function toggleProposalWeek(btn) {
                btn.classList.toggle('btn-dark');
                btn.classList.toggle('text-white');
                btn.classList.toggle('fw-semibold');
                btn.classList.toggle('btn-light');
                btn.classList.toggle('border');
                btn.classList.toggle('text-muted');
                syncProposalWeeks();
            }
            function syncProposalWeeks() {
                const active = Array.from(document.querySelectorAll('.week-toggle-btn.btn-dark')).map(b => b.getAttribute('data-week'));
                const input = document.getElementById('proposal-weeks-input');
                if (input) input.value = active.join(', ');
                const hint = document.getElementById('proposal-weeks-hint');
                if (hint) {
                    hint.textContent = active.length > 0 ? 'Selected: Weeks ' + active.join(', ') : 'No specific weeks selected (covers full term)';
                }
            }
            function toggleAllProposalWeeks(select) {
                document.querySelectorAll('.week-toggle-btn').forEach(btn => {
                    if (select) {
                        btn.classList.add('btn-dark', 'text-white', 'fw-semibold');
                        btn.classList.remove('btn-light', 'border', 'text-muted');
                    } else {
                        btn.classList.remove('btn-dark', 'text-white', 'fw-semibold');
                        btn.classList.add('btn-light', 'border', 'text-muted');
                    }
                });
                syncProposalWeeks();
            }
            """),
            action="/app/proposals/new",
            method="post",
            style="max-width: 840px; margin: 0 auto;",
        )

        return AppShell(
            Title("New Proposal — SkuPhase"),
            Container(
                Div(
                    Div(
                        Icon("journal-plus", cls="bi fs-3 text-success"),
                        cls="p-3 bg-success-subtle rounded-circle d-inline-flex align-items-center justify-content-center me-3",
                        style="width: 52px; height: 52px;",
                    ),
                    Div(
                        H1("Submit Generation Proposal", cls="fw-bold fs-2 text-dark mb-1"),
                        P("Propose an exam for your class aligned with the primary curriculum scheme of work.", cls="text-muted small mb-0"),
                    ),
                    cls="d-flex align-items-center mb-4",
                    style="max-width: 840px; margin: 0 auto;",
                ),
                form,
                cls="py-4 pt-lg-5",
            ),
            user=user,
            active="proposals",
            flash=flash,
            crumbs=[("Generation Proposals", "/app/proposals"), ("New", None)],
            bell_count=req.session.get("bell_count"),
        )

    @app.post("/app/proposals/new")
    async def proposals_create_submit(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        subject = form.get("subject", "").strip()
        grade_level = form.get("grade_level", "").strip()
        term = form.get("term", "").strip()
        weeks_raw = form.get("selected_weeks", "").strip()
        desired_outcomes = form.get("desired_outcomes", "").strip()
        custom_instructions = form.get("custom_instructions", "").strip()

        selected_weeks = []
        if weeks_raw:
            for part in weeks_raw.replace(";", ",").split(","):
                part = part.strip()
                if part.isdigit():
                    selected_weeks.append(int(part))

        payload = {
            "subject": subject,
            "grade_level": grade_level,
            "term": term or "First Term",
            "desired_outcomes": desired_outcomes,
            "custom_instructions": custom_instructions or None,
            "selected_weeks": selected_weeks or None,
        }

        resp = await call_api(req, "POST", "/exams/generation-proposals", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            push_flash(req, data.get("message", "Failed to submit proposal."), "danger")
            return RedirectResponse("/app/proposals/new", status_code=303)

        push_flash(req, "Proposal submitted successfully! School administrators can now generate the exam.", "success")
        return RedirectResponse("/app/proposals", status_code=303)

    @app.post("/app/proposals/{proposal_id}/generate")
    async def proposal_generate_submit(req: Request, proposal_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        if user.get("role") != "school_admin":
            push_flash(req, "Only school administrators can trigger exam generation from proposals.", "danger")
            return RedirectResponse("/app/proposals", status_code=303)

        form = await req.form()

        # Audit #4: GenerateFromProposalRequest requires at least one section.
        # Build a standard Nigerian-format default (20 objectives + 5 short
        # answer) since the review modal does not collect section config.
        term = (form.get("term") or "").strip() or None
        raw_weeks = (form.get("selected_weeks") or "").strip()
        selected_weeks = [int(w) for w in raw_weeks.split(",") if w.strip().isdigit()]
        outcomes = (form.get("desired_outcomes") or "").strip()
        payload = {
            "sections": [
                {
                    "section_number": 1,
                    "section_title": "SECTION A: OBJECTIVES",
                    "question_type": "multiple_choice",
                    "num_questions": 20,
                    "marks_per_question": 1,
                },
                {
                    "section_number": 2,
                    "section_title": "SECTION B: SHORT ANSWER",
                    "question_type": "short_answer",
                    "num_questions": 5,
                    "marks_per_question": 4,
                },
            ],
            "duration_minutes": 120,
            "include_diagrams": False,
            "additional_admin_instructions": outcomes[:2000] or None,
        }
        if term:
            payload["term"] = term
        if selected_weeks:
            payload["selected_weeks"] = selected_weeks

        resp = await call_api(req, "POST", f"/exams/generation-proposals/{proposal_id}/generate", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            push_flash(req, data.get("message", "Could not generate exam from proposal."), "danger")
            return RedirectResponse("/app/proposals", status_code=303)

        exam_id = data.get("exam_id") or ""
        push_flash(req, "Exam generation started successfully!", "success")
        if exam_id:
            return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)
        return RedirectResponse("/app/exams", status_code=303)

    @app.post("/app/proposals/{proposal_id}/reject")
    async def proposal_reject_submit(req: Request, proposal_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        if user.get("role") != "school_admin":
            push_flash(req, "Only school administrators can reject proposals.", "danger")
            return RedirectResponse("/app/proposals", status_code=303)

        form = await req.form()
        note = (form.get("admin_note") or "").strip()

        resp = await call_api(req, "POST", f"/exams/generation-proposals/{proposal_id}/reject")
        ok, data = unwrap(resp)
        if not ok:
            push_flash(req, data.get("message", "Could not reject the proposal."), "danger")
            return RedirectResponse("/app/proposals", status_code=303)

        if note:
            set_flash(req.session, "info", f"Proposal rejected. Note: {note[:200]}")
        else:
            push_flash(req, "Proposal rejected. The teacher can submit a revised version.", "success")
        return RedirectResponse("/app/proposals", status_code=303)
