"""Exam pages + HTMX partials (FRONTEND_SPEC sec 6.4-6.6).

Server-rendered FastHTML routes that talk to the API via ``call_api`` only.
Covers: exams list, exam detail (with polling), the 3-step generation wizard
(curriculum -> sections -> options -> generate), manual exam entry, and all
action handlers (refine, submit-final, approve, export, download, delete).
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from fasthtml.common import (
    A,
    Details,
    Div,
    Form,
    H1,
    H2,
    Input,
    Label,
    Option,
    P,
    Pre,
    Select as HtmlSelect,
    Span,
    Strong,
    Summary,
    Textarea,
    Title,
)
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import (
    Alert,
    Badge,
    Button,
    Card,
    Col,
    EmptyState,
    FormGroup,
    Icon,
    Row,
    Select,
    Spinner,
)

from app.core.workflow import REFINABLE_STATES, SUBMITTABLE_STATES  # noqa: F401  (re-exported for app.core.workflow)
from app.frontend.api import call_api, unwrap
from app.frontend.components.exam import (
    StatusBadge,
    action_buttons,
    exam_header,
    render_questions,
)
from app.frontend.components.feedback import Flash, pop_flash, set_flash, show_toast
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login

QUESTION_TYPES = [
    ("multiple_choice", "Multiple choice"),
    ("short_answer", "Short answer"),
    ("essay", "Essay"),
    ("true_false", "True / False"),
]
INSTRUCTION_TYPES = [
    ("answer_all", "Answer all"),
    ("answer_any_n", "Answer any N"),
    ("compulsory_plus_optional", "Compulsory + optional"),
]
SUB_PART_STYLES = [
    ("none", "None"),
    ("letter", "Letter (a, b, c)"),
    ("roman", "Roman (i, ii, iii)"),
    ("number", "Number (1, 2, 3)"),
]
LANGUAGES = [
    ("English", "English"),
    ("Igbo", "Igbo"),
    ("Yoruba", "Yoruba"),
    ("Hausa", "Hausa"),
]
TERMS = ["First Term", "Second Term", "Third Term"]
GRADE_LEVELS = [
    "Pre-Nursery", "Nursery 1", "Nursery 2", "Kindergarten",
    "Primary 1", "Primary 2", "Primary 3", "Primary 4",
    "Primary 5", "Primary 6",
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _csrf_input(request: Request):
    """Hidden CSRF token input for HTML <form> posts; '' when no token yet."""
    token = request.session.get("csrf")
    if not token:
        return ""
    return Input("csrf_token", value=token, type="hidden")


def _safe_int(value, default: int) -> int:
    """Parse an int from form data without crashing on bad input."""
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


async def _fetch_exam(req: Request, exam_id: str):
    """Fetch single exam. Returns (ok, data_or_error_dict)."""
    resp = await call_api(req, "GET", f"/exams/{exam_id}")
    return unwrap(resp)


def _query(**params) -> str:
    """Build a query string from non-empty kwargs."""
    return urlencode({k: v for k, v in params.items() if v not in (None, "")})


def _state_of(exam: dict) -> str:
    """Resolve the effective workflow state for badge/action logic."""
    if exam.get("status") == "failed":
        return "failed"
    return exam.get("workflow_state") or exam.get("status") or "draft"


def _quality_bar(exam: dict):
    """Quality-score bar (AI-generated exams only; hidden otherwise)."""
    score = exam.get("quality_score")
    if score is None:
        return Span("\u2014", cls="text-muted")
    pct = max(0, min(100, int(score)))
    warn = " warn" if pct < 80 else ""
    return Span(
        Span(Span(cls=f"app-quality-fill{warn}", style=f"width:{pct}%"), cls="app-quality-track"),
        f"{pct}%",
        cls="d-inline-flex align-items-center gap-1 small text-muted",
    )


def _exam_row(exam: dict):
    """One prototype-style exams-list row (UI_design/Exams.png)."""
    exam_id = exam.get("id", "")
    detail_link = f"/app/exams/{exam_id}"
    created = (exam.get("created_at") or "")[:10]
    subject = exam.get("subject", "Untitled exam")
    grade = exam.get("grade_level", "")
    total_marks = exam.get("total_marks", 0)
    questions_count = exam.get("total_questions") or len(exam.get("questions") or []) or "—"
    created_by = exam.get("creator_name") or exam.get("created_by_name") or "Adaeze"
    workflow_state = exam.get("workflow_state") or exam.get("status") or "draft"

    if workflow_state == "generation_requested":
        icon_name, icon_cls = "lightning-charge-fill", "app-row-icon"
    elif exam.get("source_type") == "manual" or exam.get("is_manual"):
        icon_name, icon_cls = "file-earmark-text", "app-row-icon"
    else:
        icon_name, icon_cls = "stars", "app-row-icon ai"

    title_text = f"{grade} {subject} — Term Examination" if "Exam" not in subject else f"{grade} {subject}"

    return Div(
        Div(
            Div(Icon(icon_name, cls="bi"), cls=icon_cls),
            Div(
                A(Strong(title_text, cls="text-dark d-block mb-0 text-truncate"), href=detail_link, cls="text-decoration-none"),
                Span(f"{total_marks} marks · by {created_by}", cls="text-muted small"),
                cls="text-truncate",
            ),
            cls="col-12 col-md-5 d-flex align-items-center mb-2 mb-md-0 pe-2",
        ),
        Div(
            Div(subject, cls="fw-semibold text-dark small"),
            Div(grade, cls="text-muted small"),
            cls="col-6 col-md-2",
        ),
        Div(
            Span(str(questions_count), cls="small fw-semibold text-dark"),
            cls="col-6 col-md-1 text-md-center",
        ),
        Div(
            _quality_bar(exam),
            cls="col-6 col-md-1 text-md-center mt-1 mt-md-0",
        ),
        Div(
            StatusBadge(exam),
            cls="col-6 col-md-2 text-md-center mt-1 mt-md-0",
        ),
        Div(
            Span(created, cls="small text-muted me-2 d-none d-md-inline"),
            A(Icon("chevron-right", cls="bi text-muted"), href=detail_link, cls="text-decoration-none"),
            cls="col-12 col-md-1 text-md-end mt-2 mt-md-0 d-flex justify-content-between justify-content-md-end align-items-center",
        ),
        cls="row app-table-row align-items-center g-0 px-3 py-3 border-bottom",
    )


def _section_card(idx: int) -> Div:
    """One configurable section row for the generation wizard."""
    return Div(
        Div(
            FormGroup(
                "Section title",
                Input(
                    f"section_{idx}_title",
                    value=f"SECTION {chr(64 + idx)}",
                    required=True,
                ),
            ),
            FormGroup(
                "Question type",
                Select(
                    f"section_{idx}_qtype",
                    *QUESTION_TYPES,
                    value="multiple_choice",
                ),
            ),
            FormGroup(
                "Number of questions",
                Input(
                    f"section_{idx}_num",
                    type="number",
                    value="20",
                    min="1",
                    max="50",
                ),
            ),
            FormGroup(
                "Marks per question",
                Input(
                    f"section_{idx}_marks",
                    type="number",
                    value="2",
                    min="1",
                    max="20",
                ),
            ),
            FormGroup(
                "Instruction type",
                Select(
                    f"section_{idx}_instr",
                    *INSTRUCTION_TYPES,
                    value="answer_all",
                ),
            ),
            FormGroup(
                "Sub-part style",
                Select(
                    f"section_{idx}_substyle",
                    *SUB_PART_STYLES,
                    value="none",
                ),
            ),
            cls="row g-2",
        ),
        id=f"section-card-{idx}",
        cls="card p-3 mb-2",
        **{"data-section-index": str(idx)},
    )


def _build_sections_from_form(form) -> list:
    """Read section fields from the wizard form and build SectionConfig dicts."""
    sections: list = []
    idx = 1
    while True:
        title = form.get(f"section_{idx}_title")
        if title is None:
            break
        qtype = form.get(f"section_{idx}_qtype", "multiple_choice")
        num_q = max(1, _safe_int(form.get(f"section_{idx}_num"), 1))
        marks = max(1, _safe_int(form.get(f"section_{idx}_marks"), 1))
        instr = form.get(f"section_{idx}_instr", "answer_all")
        substyle = form.get(f"section_{idx}_substyle", "none")
        sections.append(
            {
                "section_number": idx,
                "section_title": title,
                "question_type": qtype,
                "num_questions": num_q,
                "marks_per_question": marks,
                "instruction_type": instr,
                "sub_part_style": substyle,
            }
        )
        idx += 1
    return sections


def _manual_paste_help() -> Div:
    return Div(
        P(
            "Paste one question per block, separated by a blank line. "
            "For multiple-choice questions, prefix each option with \"A)\", "
            "\"B)\", \"C)\", \"D)\" and mark the correct answer with \"Answer: B\".",
            cls="text-muted small",
        ),
        P("Example:", cls="small mb-1 fw-semibold"),
        Pre(
            "What is 2 + 2?\nA) 3\nB) 4\nC) 5\nD) 6\nAnswer: B\nMarks: 2\n\n"
            "Name the capital of Lagos State.\nMarks: 1"
        ),
    )


def _is_workspace_admin(user: dict) -> bool:
    """Mirror of app.core.permissions.is_workspace_admin for UI gating."""
    return user.get("role") == "school_admin" or user.get("account_type") == "individual_teacher"


# ---------------------------------------------------------------------------
# Page-route registration: /app/exams list + /app/exams/{id} detail
# ---------------------------------------------------------------------------

def register_page_routes(app):
    """Register list and detail routes (full pages)."""

    @app.get("/app/exams")
    async def exams_list(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)

        q = req.query_params.get("q", "").strip()
        subject = req.query_params.get("subject", "").strip()
        grade = req.query_params.get("grade", "").strip()
        status = req.query_params.get("status", "").strip()

        params = {"limit": "50"}
        if subject:
            params["subject"] = subject
        if grade:
            params["grade_level"] = grade
        if status:
            params["status"] = status

        resp = await call_api(req, "GET", "/exams/", params=params)
        ok, data = unwrap(resp)

        if not ok:
            # Full-page flow: inline Alert is correct here (FRONTEND_SPEC §5) —
            # this renders inside AppShell, not as an HTMX swap response.
            body_content = Div(
                Alert(data.get("message", "We couldn't load your exams right now — refresh to try again."), variant="danger"),
                cls="mb-3",
            )
        else:
            exams = data.get("exams", []) or []
            if q:
                q_lower = q.lower()
                exams = [
                    e for e in exams
                    if q_lower in (e.get("subject", "") + " " + e.get("grade_level", "")).lower()
                ]
            if not exams:
                body_content = EmptyState(
                    title="No exams yet",
                    description="Create your first exam with AI or type one yourself.",
                    action=A(
                        Icon("stars", cls="bi me-2"),
                        "Create exam",
                        href="/app/exams/new",
                        cls="btn btn-brand rounded-pill px-4 py-2 text-white fw-semibold text-decoration-none shadow-sm",
                    ),
                )
            else:
                rows = [_exam_row(e) for e in exams]
                table_head = Div(
                    Div("Title", cls="col-md-5 fw-bold"),
                    Div("Subject / Grade", cls="col-md-2 fw-bold"),
                    Div("Questions", cls="col-md-1 text-md-center fw-bold"),
                    Div("Quality", cls="col-md-1 text-md-center fw-bold"),
                    Div("Status", cls="col-md-2 text-md-center fw-bold"),
                    Div("Updated", cls="col-md-1 text-md-end fw-bold"),
                    cls="row app-table-head g-0 d-none d-md-flex px-3 py-2 text-muted small",
                )
                body_content = Div(table_head, *rows, cls="app-table-container app-card shadow-sm border-0 rounded-4 overflow-hidden")

        # Status filter pills (UI_design/Exams2.png) — links preserve search & filters.
        def _pill(label: str, key: str, active_key: str, count: int | None = None):
            href_params = {k: v for k, v in (("q", q), ("subject", subject), ("grade", grade)) if v}
            if key:
                href_params["status"] = key
            href = "/app/exams" + (("?" + urlencode(href_params)) if href_params else "")
            count_str = f" ({count})" if count is not None else ""
            is_active = (active_key == key) or (not active_key and not key)
            if is_active:
                cls = "badge rounded-pill text-white px-3 py-2 fw-semibold text-decoration-none shadow-sm"
                style = "background-color: #00412E !important; font-size: 0.88rem;"
            else:
                cls = "badge rounded-pill bg-white text-muted border px-3 py-2 fw-normal text-decoration-none shadow-sm"
                style = "font-size: 0.88rem;"
            return A(f"{label}{count_str}", href=href, cls=cls, style=style,
                     **({"aria-current": "true"} if is_active else {}))

        all_exams = (data.get("exams", []) or []) if ok else []
        approved_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) == "approved")
        review_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) in {"teacher_review", "final_submitted_by_teacher", "refinement_requested"})
        gen_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) == "generation_requested")
        draft_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) == "draft")
        failed_cnt = sum(1 for e in all_exams if e.get("status") == "failed")

        # Live bell badge (audit: was hardcoded "3"): stash the under-review
        # count in the session so every AppShell page can show a real number.
        req.session["bell_count"] = review_cnt

        pills = Div(
            _pill("All", "", status, len(all_exams)),
            _pill("Approved", "approved", status, approved_cnt),
            _pill("Under Review", "under_review", status, review_cnt),
            _pill("Generating", "generating", status, gen_cnt),
            _pill("Draft", "draft", status, draft_cnt),
            _pill("Failed", "failed", status, failed_cnt),
            cls="d-flex gap-2 flex-wrap mb-3 align-items-center",
        )

        subject_options = [
            ("All subjects", ""),
            ("Mathematics", "Mathematics"),
            ("English Language", "English Language"),
            ("Basic Science", "Basic Science"),
            ("Social Studies", "Social Studies"),
            ("National Values", "National Values"),
            ("Civic Education", "Civic Education"),
            ("Agricultural Science", "Agricultural Science"),
            ("Computer Studies", "Computer Studies"),
            ("Physical & Health Education", "Physical & Health Education"),
            ("Home Economics", "Home Economics"),
            ("Christian Religious Studies", "Christian Religious Studies"),
            ("Islamic Religious Studies", "Islamic Religious Studies"),
            ("Hausa", "Hausa"),
            ("Igbo", "Igbo"),
            ("Yoruba", "Yoruba"),
        ]

        grade_options = [
            ("All grades", ""),
            ("Primary 1", "Primary 1"),
            ("Primary 2", "Primary 2"),
            ("Primary 3", "Primary 3"),
            ("Primary 4", "Primary 4"),
            ("Primary 5", "Primary 5"),
            ("Primary 6", "Primary 6"),
            ("JSS1", "JSS1"),
            ("JSS2", "JSS2"),
            ("JSS3", "JSS3"),
            ("SS1", "SS1"),
            ("SS2", "SS2"),
            ("SS3", "SS3"),
        ]

        search_input_wrap = Div(
            Icon("search", cls="bi text-muted me-2"),
            Input(
                "q",
                value=q,
                placeholder="Search exams...",
                cls="border-0 bg-transparent shadow-none p-0 flex-grow-1",
                style="outline:none; font-size: 0.92rem;",
                **{"aria-label": "Search exams"},
            ),
            cls="d-flex align-items-center bg-white border rounded-pill px-3 py-2 shadow-sm flex-grow-1",
            style="min-width: 240px; max-width: 360px;",
        )

        subject_select = HtmlSelect(
            *[Option(label, value=val, selected=(subject == val if val else not subject)) for label, val in subject_options],
            name="subject",
            cls="form-select rounded-pill bg-white border px-3 py-2 shadow-sm",
            style="min-width: 160px; max-width: 200px; font-size: 0.92rem; cursor: pointer;",
            onchange="this.form.submit()",
        )

        grade_select = HtmlSelect(
            *[Option(label, value=val, selected=(grade == val if val else not grade)) for label, val in grade_options],
            name="grade",
            cls="form-select rounded-pill bg-white border px-3 py-2 shadow-sm",
            style="min-width: 140px; max-width: 180px; font-size: 0.92rem; cursor: pointer;",
            onchange="this.form.submit()",
        )

        filter_form = Form(
            search_input_wrap,
            subject_select,
            grade_select,
            Input("status", type="hidden", value=status) if status else "",
            action="/app/exams",
            method="get",
            cls="d-flex flex-wrap gap-3 align-items-center mb-4",
            id="exams-filter",
        )

        body = Div(
            Div(
                Div(
                    Div(
                        H1("Exams", cls="app-section-title mb-1"),
                        P("Manage, generate, and review examinations.", cls="app-body-copy mb-0"),
                    ),
                    Div(
                        A(
                            Icon("stars", cls="bi me-2"),
                            "Generate with AI",
                            href="/app/exams/new",
                            cls="btn btn-brand rounded-pill px-4 py-2 fw-semibold text-white shadow-sm d-inline-flex align-items-center text-decoration-none",
                        ),
                        Button(
                            Icon("plus-lg", cls="bi me-2"),
                            "New Exam",
                            type="button",
                            cls="btn btn-outline-secondary bg-white text-dark border rounded-pill px-4 py-2 fw-semibold shadow-sm ms-2 d-inline-flex align-items-center",
                            **{"data-bs-toggle": "modal", "data-bs-target": "#createExamModal"},
                        ),
                        cls="d-flex flex-wrap gap-2 align-items-center",
                    ),
                    cls="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4",
                ),
                pills,
                filter_form,
                Div(body_content, id="exams-content"),
                cls="mt-2",
            ),
            _create_modal(),
            id="exams-view",
        )
        return AppShell(
            Title("Exams - SkuPhase"),
            body,
            user=user,
            active="exams",
            flash=flash,
            crumbs=[("Exams", None)],
            bell_count=req.session.get("bell_count"),
        )

    @app.get("/app/exams/new")
    async def exam_new(req: Request, mode: str = "ai", step: str = "1"):
        guard = ensure_login(req)
        if guard:
            return guard
        if mode == "manual":
            return RedirectResponse("/app/exams/new/manual", status_code=303)
        user = current_user(req) or {}
        flash = pop_flash(req)
        body = _render_wizard_full(step=step, request=req)
        return AppShell(
            Title("New AI exam - SkuPhase"),
            body,
            user=user,
            active="exams",
            flash=flash,
            bell_count=req.session.get("bell_count"),
        )
    @app.get("/app/exams/{exam_id}")
    async def exam_detail(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)
        show_answers = req.query_params.get("answers") == "1"

        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            set_flash(req.session, "danger", exam.get("message", "Exam not found."))
            return RedirectResponse("/app/exams", status_code=303)

        state = _state_of(exam)
        is_generating = state in ("generation_requested", "refinement_requested")

        if is_generating:
            inner = Div(
                Div(
                    Spinner(),
                    P(
                        "Generating your exam... This usually takes 30-60 seconds.",
                        cls="text-muted small ms-2",
                    ),
                    cls="d-flex align-items-center gap-2 mb-3",
                ),
                P(
                    A(
                        "Cancel and pick manual entry",
                        href="/app/exams/new/manual",
                        cls="text-muted small",
                    ),
                    cls="mb-3",
                ),
                Div(
                    hx_get=f"/ui/exams/{exam_id}/poll",
                    hx_trigger="every 4s",
                    hx_target="#exam-detail-view",
                    hx_swap="outerHTML",
                ),
                id="exam-detail-view",
            )
        else:
            inner = Div(
                _render_exam_detail(exam, user, show_answers),
                id="exam-detail-view",
            )

        return AppShell(
            Title(f"{exam.get('subject', 'Exam')} - SkuPhase"),
            inner,
            user=user,
            active="exams",
            flash=flash,
            crumbs=[("Exams", "/app/exams"), (exam.get("subject", "Exam"), None)],
            bell_count=req.session.get("bell_count"),
        )

    # ----- Detail tab partials (lazy-loaded into #tab-content) -----

    @app.get("/ui/exams/{exam_id}/tab/questions")
    async def tab_questions(req: Request, exam_id: str, answers: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            # HTMX partial response: ephemeral feedback uses show_toast (FRONTEND_SPEC §5).
            return show_toast(exam.get("message", "We couldn't load the questions right now — refresh to try again."), "danger")
        return _questions_tab(exam, show_answers=answers == "1")

    @app.get("/ui/exams/{exam_id}/tab/preflight")
    async def tab_preflight(req: Request, exam_id: str, run: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        if run != "1":
            # Exams7.png: "Preflight not yet run" + explicit CTA.
            return Div(
                EmptyState(
                    title="Preflight not yet run",
                    description="Run the checks to confirm this exam is ready to export.",
                    action=Button(
                        "Run Preflight Check",
                        hx_get=f"/ui/exams/{exam_id}/tab/preflight?run=1",
                        hx_target="#tab-content",
                        hx_swap="innerHTML",
                        cls="btn-brand",
                    ),
                ),
            )
        resp = await call_api(req, "GET", f"/exams/{exam_id}/preflight")
        ok, data = unwrap(resp)
        if not ok:
            # HTMX partial response: ephemeral feedback uses show_toast (FRONTEND_SPEC §5).
            return show_toast(data.get("message", "Preflight could not run."), "danger")
        if data.get("passed"):
            # Persistent tab content (result summary), not ephemeral feedback —
            # inline Alert is the agreed exception (QUICK_REFERENCE feedback rules).
            return Div(
                Alert(
                    Icon("check-circle", cls="bi me-2"),
                    "All checks passed — exam is ready to export.",
                    variant="success",
                ),
                id="tab-content-inner",
            )
        items = []
        for issue in data.get("issues") or []:
            items.append(
                P(
                    Icon("x-circle", cls="bi text-danger me-2"),
                    issue.get("message", "Issue"),
                    cls="mb-1",
                )
            )
        for warning in data.get("warnings") or []:
            items.append(
                P(
                    Icon("exclamation-triangle", cls="bi text-warning me-2"),
                    warning.get("message", "Warning"),
                    cls="mb-1",
                )
            )
        return Div(
            # Persistent tab content (preflight result summary) — inline Alert is the
            # agreed exception (QUICK_REFERENCE feedback rules).
            Alert(
                f"Preflight found {data.get('issue_count', len(data.get('issues') or []))} issue(s)"
                f" and {data.get('warning_count', len(data.get('warnings') or []))} warning(s)."
                " Resolve issues before export.",
                variant="warning",
            ),
            Card(Div(*items, cls="p-3"), cls="mb-3"),
            id="tab-content-inner",
        )

    @app.get("/ui/exams/{exam_id}/tab/quality")
    async def tab_quality(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "GET", f"/exams/{exam_id}/quality-report")
        ok, data = unwrap(resp)
        if not ok:
            # Exams8.png: quality report unavailable (e.g. no questions yet).
            return EmptyState(
                title="Quality report not available",
                description=data.get("message", "Complete generation to see the quality score."),
            )
        return _quality_tab_content(data)

    @app.get("/ui/exams/{exam_id}/tab/comments")
    async def tab_comments(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "GET", f"/exams/{exam_id}/audit-comments")
        ok, data = unwrap(resp)
        comments = data if (ok and isinstance(data, list)) else []
        return _comments_tab_content(req, exam_id, comments, ok=ok, message=data.get("message") if not ok else None)

    @app.post("/ui/exams/{exam_id}/comments")
    async def add_comment(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        text = (form.get("comment_text") or "").strip()
        if len(text) < 5:
            return show_toast("Comment must be at least 5 characters.", "danger")
        resp = await call_api(req, "POST", f"/exams/{exam_id}/audit-comments",
                              json={"comment_text": text})
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not save comment."), "danger")
        # Re-render the whole comments tab with the fresh list.
        list_resp = await call_api(req, "GET", f"/exams/{exam_id}/audit-comments")
        ok2, comments = unwrap(list_resp)
        return _comments_tab_content(req, exam_id, comments if (ok2 and isinstance(comments, list)) else [])

    @app.post("/ui/exams/{exam_id}/refine-comments")
    async def refine_from_comments(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/exams/{exam_id}/refine-from-comments")
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not trigger refinement from comments."), "danger")
        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.post("/ui/exams/{exam_id}/save-bank")
    async def save_to_bank(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        indexes_raw = form.getlist("question_indexes")
        indexes = [int(i) for i in indexes_raw if i.isdigit()]
        resp = await call_api(req, "POST", f"/exams/{exam_id}/question-bank/save",
                              json={"question_indexes": indexes if indexes else None})
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Failed to save questions to bank."), "danger")
        saved_count = data.get("saved_count", len(indexes) or "all")
        return show_toast(f"Successfully saved {saved_count} question(s) to Question Bank!", "success", title="Saved to Bank")

    @app.get("/ui/exams/{exam_id}/exports-history")
    async def exports_history(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "GET", f"/exams/{exam_id}/exports")
        ok, data = unwrap(resp)
        files = data if (ok and isinstance(data, list)) else []
        if not files:
            return Div(
                Icon("file-earmark-pdf", cls="bi text-muted fs-1 mb-2 d-block text-center"),
                P("No exported files yet for this exam. Use 'Export PDF' to generate printable papers.", cls="text-muted small text-center mb-0"),
                cls="p-4",
            )
        file_items = []
        for f in files:
            file_items.append(
                Div(
                    Div(
                        Icon("file-pdf-fill", cls="bi text-danger fs-4 me-3"),
                        Div(
                            Strong(f, cls="d-block small text-dark"),
                            Span("Print-ready PDF", cls="text-muted small"),
                        ),
                        cls="d-flex align-items-center",
                    ),
                    A(
                        Icon("download", cls="bi me-1"),
                        "Download",
                        href=f"/api/v1/exams/{exam_id}/exports/{f}",
                        target="_blank",
                        cls="btn btn-sm btn-outline-success rounded-pill px-3",
                    ),
                    cls="d-flex align-items-center justify-content-between p-3 border-bottom",
                )
            )
        return Div(*file_items)


# ---------------------------------------------------------------------------
# Detail rendering helper (also used by polling + refine hx-target)
# ---------------------------------------------------------------------------

def _save_bank_modal(exam: dict) -> Div:
    exam_id = str(exam.get("id") or "")
    questions = exam.get("questions") or []
    items = []
    for idx, q in enumerate(questions, start=1):
        qtext = q.get("question_text", "")
        if len(qtext) > 80:
            qtext = qtext[:77] + "..."
        items.append(
            Div(
                Input(
                    type="checkbox",
                    name="question_indexes",
                    value=str(idx - 1),
                    checked=True,
                    cls="form-check-input me-2",
                    id=f"chk-q-{exam_id}-{idx}",
                ),
                Label(f"Q{idx}. {qtext}", cls="form-check-label small", for_=f"chk-q-{exam_id}-{idx}"),
                cls="form-check mb-2",
            )
        )
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Save Questions to Bank", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Select questions to save into the school repository.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Form(
                    Div(
                        Div(id=f"save-bank-result-{exam_id}", cls="mb-2"),
                        P(f"Total questions available: {len(questions)}", cls="small fw-semibold text-dark mb-2"),
                        Div(*items, cls="p-3 bg-light rounded-3 border mb-3", style="max-height: 240px; overflow-y: auto;"),
                        cls="modal-body py-2 px-4",
                    ),
                    Div(
                        Button("Cancel", type="button", variant="light", cls="btn btn-light rounded-pill px-3 me-2", **{"data-bs-dismiss": "modal"}),
                        Button("Save Selected Questions", type="submit", variant="success", cls="btn-brand rounded-pill px-4"),
                        cls="modal-footer border-0 pt-2 pb-4 px-4",
                    ),
                    hx_post=f"/ui/exams/{exam_id}/save-bank",
                    hx_target=f"#save-bank-result-{exam_id}",
                    hx_swap="innerHTML",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"saveBankModal-{exam_id}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _exports_history_modal(exam: dict) -> Div:
    exam_id = str(exam.get("id") or "")
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Export History", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Previously generated PDF exam papers.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Div(
                    Div(
                        Spinner(),
                        Span("Loading past exports...", cls="text-muted small ms-2"),
                        id=f"exports-history-container-{exam_id}",
                        cls="p-4 text-center",
                    ),
                    cls="modal-body py-2 px-4",
                ),
                Div(
                    Button("Close", type="button", variant="secondary", cls="btn btn-secondary rounded-pill px-4", **{"data-bs-dismiss": "modal"}),
                    cls="modal-footer border-0 pt-2 pb-4 px-4",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"exportsHistoryModal-{exam_id}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _teacher_waiting_copy(exam: dict, user: dict):
    """Helper copy for school-staff teachers viewing an exam awaiting admin approval.

    Audit fix-list #7: when a teacher's exam is in final_submitted_by_teacher
    (with the admin), explain why no action buttons are available.
    """
    role = (user.get("role") or "").lower()
    if role != "teacher":
        return Div()
    state = _state_of(exam)
    if state == "final_submitted_by_teacher":
        return P(
            "Your exam is with your school admin for approval. You'll get a notification when it's reviewed.",
            cls="text-muted small mt-2",
        )
    return Div()


def _render_exam_detail(exam: dict, user: dict, show_answers: bool = False) -> Div:
    """Render the full exam detail content (used after polling resolves).

    Layout per UI_design/Exams4.png: badges + title + meta, section summary
    cards, action buttons, then a tab strip (Questions / Preflight / Quality
    Report / Audit Comments) with lazy HTMX tab loading into #tab-content.
    """
    exam_id = exam.get("id", "")
    actions = action_buttons(exam, user)
    state = _state_of(exam)
    origin_chip = "AI-generated" if exam.get("generation_job_id") or exam.get("ai_generated") else "Manual entry"
    return Div(
        # Header: badges + title + meta (Export/actions row below)
        Div(
            Div(StatusBadge(exam), Badge(origin_chip, variant="light", pill=True),
                cls="d-flex gap-2 mb-2"),
            H1(exam.get("subject", "") or "Untitled exam", cls="app-section-title fs-3 mb-1"),
            P(
                f"{exam.get('grade_level', '')}  ·  {exam.get('term', '')}"
                + (f"  ·  {exam.get('total_marks', 0)} marks" if exam.get("total_marks") else "")
                + (f"  ·  {len(exam.get('questions') or [])} questions" if exam.get("questions") else ""),
                cls="text-muted small mb-0",
            ),
            cls="mb-3",
        ),
        _section_cards(exam),
        Div(*actions, id="exam-actions", cls="mb-3 d-flex flex-wrap gap-2"),
        _teacher_waiting_copy(exam, user),
        _refine_panel(exam_id),
        _export_panel(exam_id),
        Div(id="export-result"),
        Div(id="exam-delete-result"),
        _tab_strip(exam_id),
        Div(
            _questions_tab(exam, show_answers),
            id="tab-content",
        ),
        _save_bank_modal(exam),
        _exports_history_modal(exam),
    )


def _section_cards(exam: dict) -> Div:
    """Section summary cards (name + question count + marks), Exams4 style."""
    sections = exam.get("sections") or []
    if not sections:
        return Div(cls="mb-3")
    cards = []
    for s in sections:
        if not isinstance(s, dict):
            continue
        title = s.get("section_title") or f"Section {s.get('section_number', '?')}"
        qtype = (s.get("question_type") or "").replace("_", " ").title()
        meta_bits = []
        if s.get("num_questions"):
            meta_bits.append(f"{s['num_questions']} questions")
        if s.get("marks_per_question") and s.get("num_questions"):
            meta_bits.append(f"{int(s['marks_per_question']) * int(s['num_questions'])} marks")
        if qtype:
            meta_bits.append(qtype)
        cards.append(
            Div(
                Div(
                    Icon("journal-text", cls="bi text-muted me-2"),
                    Span(title, cls="fw-semibold"),
                    cls="d-flex align-items-center mb-1",
                ),
                P(" Â· ".join(meta_bits), cls="mb-0 text-muted small"),
                cls="app-section-card",
            )
        )
    return Div(
        Row(*[Col(c, md=4, cls="mb-2 mb-md-0") for c in cards], cls="g-3 mb-3"),
        cls="mb-1",
    )


def _tab_strip(exam_id: str) -> Div:
    """Tab strip; each tab lazily loads its partial into #tab-content."""
    def _tab(label, key, path):
        return Button(
            label,
            cls="nav-link",
            type="button",
            hx_get=f"/ui/exams/{exam_id}/tab/{path}",
            hx_target="#tab-content",
            hx_swap="innerHTML",
            **{"data-tab": key},
        )

    return Div(
        _tab("Questions", "questions", "questions"),
        _tab("Preflight", "preflight", "preflight"),
        _tab("Quality Report", "quality", "quality"),
        _tab("Audit Comments", "comments", "comments"),
        cls="app-tabs nav border-bottom mb-3",
    )


def _questions_tab(exam: dict, show_answers: bool = False):
    """Default tab content: the questions + show-answers toggle."""
    exam_id = exam.get("id", "")
    return Div(
        Div(
            Div(render_questions(exam, show_answers=show_answers)),
            Div(
                Label("Show answers", cls="form-check-label me-2"),
                Input(
                    "answers",
                    type="checkbox",
                    value="1",
                    hx_get=f"/ui/exams/{exam_id}/tab/questions?answers={'0' if show_answers else '1'}",
                    hx_target="#tab-content",
                    hx_swap="innerHTML",
                    checked=show_answers,
                    cls="form-check-input",
                ),
                cls="form-check mt-3",
            ),
        ),
    )


def _quality_tab_content(data: dict) -> Div:
    """Quality Report tab (visual: UI_design/Exams5.png, real dimensions only).

    Renders: overall score / question count / coverage score cards, then
    distribution bars (question types, difficulty, Bloom's) from the report.
    """
    overall = data.get("overall_score")
    overall_txt = f"{int(overall)}%" if isinstance(overall, (int, float)) else str(overall or "—")
    coverage = (data.get("coverage") or {}).get("score")
    coverage_txt = f"{int(coverage)}%" if isinstance(coverage, (int, float)) else "—"
    q_count = data.get("question_count", "—")

    def _score_card(value, label):
        return Col(Div(P(value, cls="app-score-value mb-0"), P(label, cls="app-score-label mb-0"),
                       cls="app-score-card"), md=4, cls="mb-2")

    def _dist_rows(title, dist: dict):
        if not dist:
            return Div()
        total = sum(dist.values()) or 1
        rows = [
            Div(
                Span(label.replace("_", " ").title(), cls="app-dist-label"),
                Span(
                    Span(
                        cls="app-dist-fill",
                        style=f"width:{round(100 * count / total)}%",
                    ),
                    cls="app-dist-track",
                ),
                Span(str(count), cls="text-muted small"),
                cls="app-dist-row",
            )
            for label, count in sorted(dist.items())
        ]
        return Div(P(Strong(title, cls="small"), cls="mb-2 mt-3"), Div(*rows))

    distribution = data.get("distribution") or {}
    flags = data.get("quality_flags") or []
    status = data.get("quality_status") or "unknown"

    return Div(
        Row(
            _score_card(overall_txt, "Overall Score"),
            _score_card(str(q_count), "Questions"),
            _score_card(coverage_txt, "Curriculum Coverage"),
            cls="g-3 mb-3",
        ),
        # Persistent tab content (quality report summary) — inline Alert is the
        # agreed exception (QUICK_REFERENCE feedback rules).
        Alert(
            f"Quality status: {str(status).replace('_', ' ').title()}",
            variant="success" if status in ("good", "excellent") else "warning",
        ),
        _dist_rows("Question types", distribution.get("question_types")),
        _dist_rows("Difficulty", distribution.get("difficulty")),
        _dist_rows("Bloom's levels", distribution.get("bloom_levels")),
        *[
            # Persistent quality flags, not ephemeral feedback — inline Alert exception.
            Alert(Icon("exclamation-triangle", cls="bi me-2"), str(flag), variant="warning")
            for flag in flags
        ],
    )


def _comments_tab_content(req: Request, exam_id: str, comments: list, ok: bool = True, message: str | None = None):
    """Audit Comments tab: list + add-comment form (posts, then re-renders)."""
    csrf = _csrf_input(req)
    items = []
    if not ok and message:
        # Persistent tab context (error shown next to the comment form) —
        # inline Alert is the agreed exception (QUICK_REFERENCE feedback rules).
        items.append(Alert(message, variant="danger"))
    elif not comments:
        items.append(
            P("No review comments yet. Use the box below to note corrections or feedback.",
              cls="text-muted small")
        )
    for c in comments:
        if not isinstance(c, dict):
            continue
        created = (c.get("created_at") or "")[:10]
        items.append(
            Div(
                P(c.get("comment_text", ""), cls="mb-1"),
                P(f"{created} Â· {str(c.get('status', '')).replace('_', ' ')}",
                  cls="mb-0 text-muted small"),
                cls="pb-2 mb-2 border-bottom",
            )
        )
    refine_action = Div()
    if comments:
        refine_action = Div(
            Button(
                Icon("stars", cls="bi me-1"),
                "Refine Exam with AI from Comments",
                type="button",
                cls="btn btn-sm btn-outline-success rounded-pill px-3",
                hx_post=f"/ui/exams/{exam_id}/refine-comments",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                hx_confirm="Use all reviewer audit comments to trigger AI refinement of this exam?",
            ),
            cls="d-flex justify-content-end mb-3",
        )

    return Div(
        Card(Div(*items, cls="p-3"), cls="mb-3"),
        refine_action,
        Form(
            csrf,
            Div(
                Label("Add a review comment", cls="form-label"),
                Textarea(
                    "comment_text",
                    rows="2",
                    minlength="5",
                    maxlength="2000",
                    required=True,
                    placeholder="e.g. Question 4 answer should be B, not C.",
                    cls="form-control",
                ),
                cls="mb-2",
            ),
            Div(
                Button("Save comment", type="submit", size="sm", variant="primary", cls="btn-brand"),
                Span("Saving…", id="comments-spinner", cls="htmx-indicator text-muted small ms-2"),
                cls="d-flex justify-content-end align-items-center",
            ),
            hx_post=f"/ui/exams/{exam_id}/comments",
            hx_target="#tab-content",
            hx_swap="innerHTML",
            hx_indicator="#comments-spinner",
        ),
    )


def _refine_panel(exam_id: str) -> Div:
    """Always-on refine feedback form so action button has a target to hx-include."""
    return Div(
        Details(
            Summary("Refine this exam with AI", cls="fw-semibold"),
            Form(
                Div(
                    Label("What should change?", cls="form-label"),
                    Textarea(
                        "feedback",
                        id="refine-feedback",
                        rows="3",
                        placeholder="e.g. Make Q3 simpler, add an Igbo-language question, remove Q5.",
                        required=True,
                        minlength="5",
                        cls="form-control",
                    ),
                    cls="mb-2",
                ),
                Div(
                    Button(
                        "Send for refinement",
                        type="submit",
                        variant="outline-secondary",
                        size="sm",
                    ),
                    cls="d-flex justify-content-end",
                ),
                hx_post=f"/ui/exams/{exam_id}/refine",
                hx_include="#refine-feedback",
                hx_target="#exam-actions",
                hx_swap="outerHTML",
                hx_indicator="#refine-spinner",
            ),
            Div(
                Spinner(),
                P("Refining...", cls="text-muted small ms-2"),
                id="refine-spinner",
                cls="htmx-indicator d-flex align-items-center gap-2 mt-2",
            ),
        ),
        cls="mb-3",
    )


def _export_panel(exam_id: str) -> Div:
    """Always-on export options so action button has hx-include targets."""
    return Div(
        Details(
            Summary("Export to PDF", cls="fw-semibold"),
            Form(
                Div(
                    Label(
                        Input(
                            "include_answers",
                            type="checkbox",
                            value="1",
                            id="export-answers",
                            cls="form-check-input me-2",
                        ),
                        "Include answer key",
                        cls="form-check-label",
                    ),
                    cls="form-check mb-2",
                ),
                Div(
                    Button(
                        "Generate PDF",
                        type="submit",
                        variant="success",
                        size="sm",
                        cls="btn-brand",
                    ),
                    cls="d-flex justify-content-end",
                ),
                hx_post=f"/ui/exams/{exam_id}/export",
                hx_include="#export-answers",
                hx_target="#export-result",
                hx_swap="innerHTML",
                hx_indicator="#export-spinner",
            ),
            Div(
                Spinner(),
                P("Exporting...", cls="text-muted small ms-2"),
                id="export-spinner",
                cls="htmx-indicator d-flex align-items-center gap-2 mt-2",
            ),
        ),
        cls="mb-3",
    )


# ---------------------------------------------------------------------------
# Wizard (curriculum / sections / options) Ã¢â‚¬â€ full pages
# ---------------------------------------------------------------------------

def register_wizard_routes(app):


    @app.get("/ui/exams/wizard")
    async def wizard_partial(req: Request, step: str = "1"):
        """HTMX partial for the wizard steps (no full shell)."""
        guard = ensure_login(req)
        if guard:
            return guard
        return _wizard_panel(step=step, request=req)

    @app.get("/ui/exams/wizard/sections")
    async def wizard_sections(req: Request, num_sections: str = "2"):
        guard = ensure_login(req)
        if guard:
            return guard
        n = _safe_int(num_sections, 2)
        n = max(1, min(5, n))
        return Div(*[_section_card(i) for i in range(1, n + 1)], id="section-cards")

    @app.post("/ui/exams/wizard/step1")
    async def wizard_step1(req: Request):
        """Persist Step 1 (curriculum) fields to the session, then show Step 2."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        wiz = _wizard_state(req)
        wiz["grade_level"] = (form.get("grade_level") or "").strip()
        wiz["subject"] = (form.get("subject") or "").strip()
        wiz["term"] = (form.get("term") or "").strip()
        wiz["weeks"] = (form.get("weeks") or "").strip()
        wiz["difficulty_preset"] = (form.get("difficulty_preset") or "balanced").strip()
        wiz["bloom_levels"] = [b for b in form.getlist("bloom_levels") if b]
        _wizard_save(req, wiz)
        if not wiz["subject"] or not wiz["grade_level"]:
            return _wizard_error("Subject and class are required.")
        return _wizard_panel("2", req)

    @app.post("/ui/exams/wizard/step2")
    async def wizard_step2(req: Request):
        """Persist Step 2 (sections) to the session, then show Step 3."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        sections = _build_sections_from_form(form)
        if not sections:
            return _wizard_error("You need at least one section. Add a section before continuing.")
        wiz = _wizard_state(req)
        wiz["sections"] = sections
        _wizard_save(req, wiz)
        return _wizard_panel("3", req)


def _render_wizard_full(step: str, request: Request) -> Div:
    return Div(
        Div(
            Div(
                H1("Create exam with AI", cls="app-section-title fs-3 mb-1"),
                P(
                    "Set the curriculum, sections, then options. All steps are required.",
                    cls="text-muted small mb-0",
                ),
                cls="mb-3",
            ),
            _wizard_steps_nav(step),
        ),
        Div(
            Card(_wizard_panel(step=step, request=request), cls="p-4 mt-2"),
            id="wizard-panel",
        ),
        cls="mt-3",
    )


def _wizard_steps_nav(current: str) -> Div:
    items = [("1", "Curriculum"), ("2", "Sections"), ("3", "Options")]
    steps = []
    for num, label in items:
        cls = "app-step"
        if num == current:
            cls += " active"
        elif int(num) < int(current):
            cls += " done"
        dot = Icon("check-lg", cls="bi") if "done" in cls else Span(num)
        steps.append(
            A(dot, Span(label, cls="app-step-label"), href=f"/app/exams/new?step={num}", cls=cls)
        )
    return Div(*steps, cls="app-stepper mb-4")


def _create_modal():
    """Exams3-style two-choice create modal (Generate with AI / Blank exam)."""
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Create New Exam", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Start blank or generate with AI.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Div(
                    Div(
                        A(
                            Div(
                                Div(Icon("stars", cls="bi fs-5"), cls="app-row-icon ai me-3"),
                                Div(
                                    Strong("Generate with AI", cls="d-block text-dark fw-bold"),
                                    Span("Let AI draft from the national curriculum", cls="text-muted small"),
                                ),
                                cls="d-flex align-items-center flex-grow-1",
                            ),
                            Icon("arrow-right", cls="bi text-muted fs-5 ms-3"),
                            href="/app/exams/new?mode=ai",
                            cls="app-quick-action mb-3 p-3 text-decoration-none border rounded-3",
                        ),
                        A(
                            Div(
                                Div(Icon("file-earmark-text", cls="bi text-secondary fs-5"), cls="app-row-icon me-3"),
                                Div(
                                    Strong("Blank exam", cls="d-block text-dark fw-bold"),
                                    Span("Build questions manually", cls="text-muted small"),
                                ),
                                cls="d-flex align-items-center flex-grow-1",
                            ),
                            Icon("arrow-right", cls="bi text-muted fs-5 ms-3"),
                            href="/app/exams/new/manual",
                            cls="app-quick-action p-3 text-decoration-none border rounded-3",
                        ),
                        cls="d-flex flex-column gap-1 py-2",
                    ),
                    cls="modal-body pt-1 pb-3 px-4",
                ),
                cls="modal-content shadow-lg border-0 rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id="createExamModal",
        tabindex="-1",
        **{"aria-hidden": "true", "data-bs-keyboard": "true"},
    )


def _wizard_state(request: Request) -> dict:
    """Session-backed wizard state (audit #1/#2: fields were dropped between
    steps because Step 2 advanced via a bare anchor and Step 3's hx_include
    referenced DOM that no longer existed)."""
    return request.session.setdefault("wizard", {})


def _wizard_save(request: Request, wiz: dict) -> None:
    """Persist wizard state.

    Starlette's SessionMiddleware only re-signs the session cookie when the
    TOP-LEVEL session dict is mutated — mutating the nested ``wizard`` dict
    directly is silently dropped. Re-assigning the key marks it modified.
    """
    request.session["wizard"] = wiz


def _wizard_panel(step: str, request: Request) -> Div:
    if step == "1":
        return _wizard_curriculum(request)
    if step == "2":
        return _wizard_sections(request)
    return _wizard_options(request)


def _wizard_curriculum(request: Request) -> Card:
    qp = request.query_params
    wiz = _wizard_state(request)
    # Session values win over defaults; explicit query params still win over
    # session so deep links like /app/exams/new?grade=Primary 5 behave.
    default_grade = qp.get("grade") or qp.get("grade_level") or qp.get("class_level") or wiz.get("grade_level") or "Primary 4"
    default_subject = qp.get("subject") or wiz.get("subject") or "Mathematics"
    default_term = qp.get("term") or wiz.get("term") or "First Term"
    default_weeks = qp.get("weeks") if qp.get("weeks") is not None else (wiz.get("weeks") or "")

    # Audit (P1): preset cards were static divs. Make them real radio inputs —
    # the CSS (custom.css .preset-card:has(input:checked)) already styles the
    # checked state — and map them to backend difficulty_distribution values.
    presets = Div(
        Label("Difficulty Preset", cls="form-label fw-semibold small"),
        Row(
            Col(
                Label(
                    Input(
                        "difficulty_preset",
                        type="radio",
                        value="balanced",
                        checked=True,
                        cls="d-none",
                    ),
                    Div(Icon("layers", cls="bi text-primary fs-5 mb-1"), cls="mb-1"),
                    Strong("Balanced", cls="d-block small text-dark"),
                    Span("Standard mix of recall and problem solving", cls="text-muted", style="font-size:0.75rem;"),
                    cls="preset-card p-3 border rounded-3 text-center bg-light h-100 d-block",
                ),
                md=4, cls="mb-2",
            ),
            Col(
                Label(
                    Input("difficulty_preset", type="radio", value="exam_prep", cls="d-none"),
                    Div(Icon("trophy", cls="bi text-success fs-5 mb-1"), cls="mb-1"),
                    Strong("Exam Prep", cls="d-block small text-dark"),
                    Span("Emphasis on multi-step reasoning & application", cls="text-muted", style="font-size:0.75rem;"),
                    cls="preset-card p-3 border rounded-3 text-center bg-light h-100 d-block",
                ),
                md=4, cls="mb-2",
            ),
            Col(
                Label(
                    Input("difficulty_preset", type="radio", value="ca_test", cls="d-none"),
                    Div(Icon("journal-check", cls="bi text-warning fs-5 mb-1"), cls="mb-1"),
                    Strong("CA Test", cls="d-block small text-dark"),
                    Span("Quick continuous assessment recall checks", cls="text-muted", style="font-size:0.75rem;"),
                    cls="preset-card p-3 border rounded-3 text-center bg-light h-100 d-block",
                ),
                md=4, cls="mb-2",
            ),
            cls="g-2 mb-3",
        ),
    )

    # Audit (P1): Bloom pills were dead <span>s. Real checkboxes styled by the
    # .blooms-pill-checkbox:checked + .blooms-pill rule in custom.css.
    blooms = Div(
        Label("Cognitive Taxonomy Focus (Bloom's Level)", cls="form-label fw-semibold small"),
        Div(
            *[
                Label(
                    Input(
                        "bloom_levels",
                        type="checkbox",
                        value=level,
                        checked=(level == "Apply"),
                        cls="blooms-pill-checkbox d-none",
                    ),
                    Span(level, cls="blooms-pill me-2 mb-2"),
                    cls="d-inline-flex align-items-center",
                )
                for level in ("Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create")
            ],
            cls="d-flex flex-wrap align-items-center mb-3",
        ),
    )

    return Card(
        _csrf_input(request),
        Strong("Step 1: Curriculum & Cognitive Focus"),
        P("Pick the target class, subject, term, and academic rigor preset.", cls="text-muted small mb-3"),
        Form(
            presets,
            blooms,
            Div(
                FormGroup(
                    "Class",
                    Select(
                        "grade_level",
                        *[(g, g) for g in GRADE_LEVELS],
                        value=default_grade,
                        required=True,
                    ),
                ),
                FormGroup(
                    "Subject",
                    Input(
                        "subject",
                        value=default_subject,
                        placeholder="e.g. Mathematics",
                        required=True,
                    ),
                ),
                FormGroup(
                    "Term",
                    Select("term", *[(t, t) for t in TERMS], value=default_term),
                ),
                FormGroup(
                    "Weeks covered (comma-separated, e.g. 1,2,3)",
                    Input(
                        "weeks",
                        value=default_weeks,
                        placeholder="1,2,3",
                        pattern=r"^\s*\d+\s*(,\s*\d+\s*)*$",
                        **{"aria-describedby": "weeks-help"},
                    ),
                    P(
                        "Leave blank to use the full scheme of work.",
                        cls="form-text",
                        id="weeks-help",
                    ),
                ),
                cls="row g-3",
            ),
            Div(
                Button(
                    "Next: Sections",
                    type="submit",
                    cls="btn-brand",
                ),
                cls="d-flex justify-content-end mt-3",
            ),
            hx_post="/ui/exams/wizard/step1",
            hx_target="#wizard-panel",
            hx_swap="outerHTML",
        ),
        id="wizard-step-1",
        cls="p-4",
    )


def _wizard_sections(request: Request) -> Card:
    return Card(
        _csrf_input(request),
        Strong("Step 2: Sections"),
        P(
            "Define the sections of your exam. Most primary-school exams use 2 sections: "
            "objectives (multiple-choice) and theory (short-answer/essay).",
            cls="text-muted small mb-3",
        ),
        Form(
            Div(
                FormGroup(
                    "How many sections?",
                    Input(
                        "num_sections",
                        type="number",
                        value="2",
                        min="1",
                        max="5",
                    ),
                    P(
                        "Changing this re-renders the section cards below.",
                        cls="form-text",
                    ),
                ),
                cls="row g-3",
            ),
            hx_get="/ui/exams/wizard/sections",
            hx_target="#section-cards",
            hx_swap="innerHTML",
            hx_trigger="change from:input[name='num_sections'] delay:300ms",
            hx_include="#wizard-step-2 [name='num_sections']",
        ),
        Div(
            id="section-cards",
            cls="mb-3",
            hx_get="/ui/exams/wizard/sections?num_sections=2",
            hx_trigger="load once",
            hx_swap="innerHTML",
        ),
        Div(
            A(
                "Back: Curriculum",
                href="/app/exams/new?step=1",
                cls="btn btn-link",
            ),
            # Audit #1: this was a bare <a href> that dropped every section
            # field. Post the section cards explicitly to the step-2 endpoint,
            # which persists them in the session before rendering Step 3.
            Form(
                Button("Next: Options", type="submit", cls="btn-brand"),
                hx_post="/ui/exams/wizard/step2",
                hx_target="#wizard-panel",
                hx_swap="outerHTML",
                hx_include="#wizard-step-2 [name^='section_']",
            ),
            cls="d-flex justify-content-between mt-3",
        ),
        id="wizard-step-2",
        cls="p-3",
    )


def _wizard_options(request: Request) -> Card:
    summary_box = Div(
        Div(
            Icon("stars", cls="bi text-success fs-4 me-3"),
            Div(
                Strong("National Curriculum Grounding Active", cls="d-block text-dark fw-bold"),
                Span("SkuPhase will synthesize questions strictly anchored to the NERDC Scheme of Work. No external hallucinations or out-of-scope material.", cls="text-muted small"),
            ),
            cls="d-flex align-items-center p-3 bg-light rounded-3 border-start border-4 border-success mb-3",
        ),
    )

    return Card(
        _csrf_input(request),
        Strong("Step 3: Options & Review"),
        P(
            "Set duration, language, and submit. You can refine the exam after it is generated.",
            cls="text-muted small mb-3",
        ),
        summary_box,
        Form(
            Div(
                FormGroup(
                    "Duration (minutes)",
                    Input(
                        "duration_minutes",
                        type="number",
                        value="60",
                        min="30",
                        max="300",
                    ),
                ),
                FormGroup(
                    "Language",
                    Select("language", *LANGUAGES, value="English"),
                ),
                cls="row g-3",
            ),
            Div(
                A(
                    "Back: Sections",
                    href="/app/exams/new?step=2",
                    cls="btn btn-link",
                ),
                Button(
                    "Generate exam",
                    type="submit",
                    cls="btn-brand",
                ),
                cls="d-flex justify-content-between mt-3",
            ),
            hx_post="/ui/exams/generate",
            hx_target="#wizard-panel",
            hx_swap="outerHTML",
        ),
        id="wizard-step-3",
        cls="p-3",
    )


# ---------------------------------------------------------------------------
# Wizard action routes (POST / HTMX partials)
# ---------------------------------------------------------------------------

def register_action_routes(app):

    @app.post("/ui/exams/generate")
    async def exam_generate(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        wiz = _wizard_state(req)

        # Session fallback (audit #1/#2): Step 3 only posts duration/language;
        # curriculum + sections come from the persisted wizard state.
        weeks_raw = (form.get("weeks") or wiz.get("weeks") or "").strip()
        weeks_list: list = []
        if weeks_raw:
            try:
                weeks_list = [int(w.strip()) for w in weeks_raw.split(",") if w.strip()]
            except ValueError:
                return _wizard_error("Weeks must be a comma-separated list of numbers, e.g. 1,2,3.")

        sections = _build_sections_from_form(form) or wiz.get("sections") or []
        if not sections:
            return _wizard_error(
                "You need at least one section. Go back to Step 2 and add sections."
            )

        duration = _safe_int(form.get("duration_minutes"), 60)
        if duration < 30 or duration > 300:
            return _wizard_error("Duration must be between 30 and 300 minutes.")

        payload = {
            "subject": (form.get("subject") or wiz.get("subject") or "").strip(),
            "grade_level": (form.get("grade_level") or wiz.get("grade_level") or "").strip(),
            "term": form.get("term") or wiz.get("term") or None,
            "selected_weeks": weeks_list or None,
            "sections": sections,
            "duration_minutes": duration,
            "language": form.get("language") or "English",
        }

        # Difficulty preset -> backend difficulty_distribution (P1: the preset
        # cards previously did nothing).
        preset = (form.get("difficulty_preset") or wiz.get("difficulty_preset") or "balanced").strip()
        distributions = {
            "balanced": {"easy": 0.4, "medium": 0.4, "hard": 0.2},
            "exam_prep": {"easy": 0.2, "medium": 0.4, "hard": 0.4},
            "ca_test": {"easy": 0.6, "medium": 0.4, "hard": 0.0},
        }
        if preset in distributions:
            payload["difficulty_distribution"] = distributions[preset]

        # Bloom focus (P1: pills previously did nothing) rides along as part
        # of the teacher's custom instructions for the generator.
        bloom_levels = form.getlist("bloom_levels") or wiz.get("bloom_levels") or []
        bloom_levels = [b for b in bloom_levels if b]
        if bloom_levels:
            note = f"Emphasize Bloom's taxonomy levels: {', '.join(bloom_levels)}."
            existing = (form.get("custom_instructions") or "").strip()
            payload["custom_instructions"] = f"{existing} {note}".strip()[:1000]
        if not payload["subject"] or not payload["grade_level"]:
            return _wizard_error("Subject and class are required.")

        resp = await call_api(req, "POST", "/exams/generate", payload)
        ok, data = unwrap(resp)
        if not ok:
            return _wizard_error(
                data.get("message", "Generation failed. Please try again.")
            )
        exam_id = data.get("exam_id", "")
        warnings = data.get("warnings") or []
        if warnings:
            for w in warnings:
                set_flash(req.session, "warning", w)
        # Wizard run is complete — clear persisted state so the next exam
        # starts fresh instead of silently reusing old sections.
        req.session.pop("wizard", None)
        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.get("/ui/exams/{exam_id}/poll")
    async def exam_poll(req: Request, exam_id: str):
        """HTMX polling partial: re-render the exam detail when ready."""
        guard = ensure_login(req)
        if guard:
            return guard
        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            # HTMX polling partial: ephemeral feedback uses show_toast (FRONTEND_SPEC §5).
            return show_toast(exam.get("message", "Could not load exam."), "danger")

        state = _state_of(exam)
        if state in ("generation_requested", "refinement_requested"):
            return Div(
                Spinner(),
                P("Still generating — this usually takes under 2 minutes. You can keep this tab open.", cls="text-muted small ms-2"),
                cls="d-flex align-items-center gap-2 mb-3",
                **{"aria-live": "polite"},
            )

        user = current_user(req) or {}
        show_answers = req.query_params.get("answers") == "1"
        return Div(
            _render_exam_detail(exam, user, show_answers),
            id="exam-detail-view",
        )

    @app.post("/ui/exams/{exam_id}/refine")
    async def exam_refine(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        feedback = (form.get("feedback") or "").strip()
        if not feedback or len(feedback) < 5:
            return show_toast("Please describe what to change (at least 5 characters).", "warning")
        payload = {"feedback": feedback}
        resp = await call_api(req, "POST", f"/exams/{exam_id}/refine", payload)
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Refinement failed."), "danger")
        # Re-render the exam detail so the user sees the spinner / updated actions.
        ok2, exam = await _fetch_exam(req, exam_id)
        user = current_user(req) or {}
        if ok2:
            return Div(
                _render_exam_detail(exam, user, show_answers=False),
                show_toast("AI refinement requested. This usually takes 20-60 seconds."),
                id="exam-detail-view",
            )
        return show_toast("Refinement requested, but the exam could not be re-loaded.", "warning")

    @app.post("/ui/exams/{exam_id}/submit-final")
    async def exam_submit_final(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/exams/{exam_id}/submit-final")
        ok, data = unwrap(resp)
        if not ok:
            # HTMX response: ephemeral feedback uses show_toast; success path redirects with set_flash.
            return show_toast(data.get("message", "We couldn't submit your exam — check your connection and try again."), "danger")
        set_flash(req.session, "success", "Exam submitted for approval.")
        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.post("/ui/exams/{exam_id}/reject")
    async def exam_reject(req: Request, exam_id: str):
        """Admin sends a submitted exam back to the teacher (audit: no reject
        endpoint existed — the governed transition is final_submitted ->
        teacher_review)."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        feedback = (form.get("feedback") or "").strip()
        qs = f"?feedback={quote(feedback)}" if feedback else ""
        resp = await call_api(req, "POST", f"/exams/{exam_id}/reject{qs}")
        ok, data = unwrap(resp)
        toast = (
            show_toast(data.get("message", "Could not reject the exam."), "danger")
            if not ok
            else show_toast(data.get("message", "Exam sent back to the teacher."), "success")
        )
        # Re-render the detail view so the actions/status update immediately.
        ok2, exam = await _fetch_exam(req, exam_id)
        if not ok2:
            return toast
        user = current_user(req) or {}
        return Div(
            _render_exam_detail(exam, user, req.query_params.get("answers") == "1"),
            toast,
            id="exam-detail-view",
        )

    @app.post("/ui/exams/{exam_id}/approve")
    async def exam_approve(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/exams/{exam_id}/approve")
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "We couldn't approve this exam — try again in a moment."), "danger")
        set_flash(req.session, "success", "Exam approved.")
        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.post("/ui/exams/{exam_id}/export")
    async def exam_export(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        include_answers = form.get("include_answers") == "1"
        payload = {"format": "pdf", "include_answers": include_answers}
        resp = await call_api(req, "POST", f"/exams/{exam_id}/export", payload)
        ok, data = unwrap(resp)
        if not ok:
            # HTMX response targeting #export-result: ephemeral feedback uses show_toast.
            return show_toast(data.get("message", "We couldn't prepare the export — try again in a moment."), "danger")
        download_url = data.get("download_url", "")
        file_name = data.get("file_name", "exam.pdf")
        return Div(
            show_toast("Export ready.", "success"),
            A(
                f"Download {file_name}",
                href=download_url,
                cls="btn btn-sm btn-brand",
            ),
            id="export-result",
        )

    @app.delete("/ui/exams/{exam_id}")
    async def exam_delete(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "DELETE", f"/exams/{exam_id}")
        ok, data = unwrap(resp)
        if not ok:
            # HTMX DELETE response: ephemeral feedback uses show_toast (never Flash —
            # Flash is only rendered by the shell in full-page redirect flows).
            return show_toast(data.get("message", "We couldn't delete this exam — check your connection and try again."), "danger")
        set_flash(req.session, "success", "Exam deleted.")
        return RedirectResponse("/app/exams", status_code=303)


def _wizard_error(message: str) -> Div:
    """Return a wizard panel fragment for HTMX swap targets.

    The error itself is ephemeral feedback → show_toast (FRONTEND_SPEC §5);
    the link stays inline so the user always has a recovery path in the panel.
    """
    return Div(
        show_toast(message, "danger"),
        A("Back to Step 1", href="/app/exams/new?step=1", cls="btn btn-link"),
        id="wizard-panel",
    )


# ---------------------------------------------------------------------------
# Manual entry Ã¢â‚¬â€ paste-style form (F04/F24/F57)
# ---------------------------------------------------------------------------

def register_manual_routes(app):

    @app.get("/app/exams/new/manual")
    async def exam_manual(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)
        body = Div(
            Div(
                H1("Create exam manually", cls="app-section-title fs-3 mb-1"),
                P(
                    "Paste your questions below. Faster than typing in Word — SkuPhase "
                    "splits the text into questions and creates the exam.",
                    cls="text-muted small mb-0",
                ),
                cls="mb-3",
            ),
            Card(
                Form(
                    _csrf_input(req),
                    Div(
                        FormGroup(
                            "Subject",
                            Input("subject", required=True, placeholder="Mathematics"),
                        ),
                        FormGroup(
                            "Class",
                            Select(
                                "grade_level",
                                *[(g, g) for g in GRADE_LEVELS],
                                required=True,
                            ),
                        ),
                        FormGroup(
                            "Duration (minutes)",
                            Input(
                                "duration_minutes",
                                type="number",
                                value="60",
                                min="30",
                                max="300",
                            ),
                        ),
                        FormGroup(
                            "Language",
                            Select("language", *LANGUAGES, value="English"),
                        ),
                        FormGroup(
                            "Instructions",
                            Textarea(
                                "instructions",
                                placeholder="Answer all questions.",
                                rows="2",
                            ),
                        ),
                        cls="row g-3",
                    ),
                    _manual_paste_help(),
                    FormGroup(
                        "Questions (one question per blank line)",
                        Textarea(
                            "questions_text",
                            id="questions_text",
                            rows="12",
                            required=True,
                            placeholder=(
                                "What is 2 + 2?\nA) 3\nB) 4\nC) 5\nD) 6\nAnswer: B\nMarks: 2\n\n"
                                "Name the capital of Lagos State.\nMarks: 1"
                            ),
                        ),
                        P(
                            "Use 'Answer: <letter>' for MCQs, 'Marks: <n>' to set marks per question.",
                            cls="form-text",
                        ),
                    ),
                    Div(
                        Button(
                            "Create exam",
                            type="submit",
                            cls="btn-brand",
                        ),
                        cls="d-flex justify-content-end mt-3",
                    ),
                    hx_post="/ui/exams/manual-submit",
                    hx_target="#manual-result",
                    hx_swap="innerHTML",
                    hx_indicator="#manual-spinner",
                ),
                Div(
                    Spinner(),
                    P("Creating exam...", cls="text-muted small ms-2"),
                    id="manual-spinner",
                    cls="htmx-indicator d-flex align-items-center gap-2 mt-2",
                ),
                Div(id="manual-result"),
                cls="p-4",
            ),
            cls="mt-3",
        )
        return AppShell(
            Title("New manual exam - SkuPhase"),
            body,
            user=user,
            active="exams",
            flash=flash,
            bell_count=req.session.get("bell_count"),
        )

    @app.post("/ui/exams/manual-submit")
    async def exam_manual_submit(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        questions_text = (form.get("questions_text") or "").strip()
        if not questions_text:
            return show_toast("Please paste at least one question.", "danger")

        questions = _parse_paste_questions(questions_text)
        if not questions:
            return show_toast(
                "Could not find any questions. Each question must be at least 5 characters long.",
                "danger",
            )

        duration = _safe_int(form.get("duration_minutes"), 60)
        if duration < 30 or duration > 300:
            return show_toast("Duration must be between 30 and 300 minutes.", "danger")

        payload = {
            "subject": (form.get("subject") or "").strip(),
            "grade_level": (form.get("grade_level") or "").strip(),
            "duration_minutes": duration,
            "language": form.get("language") or "English",
            "instructions": (form.get("instructions") or "").strip() or None,
            "questions": questions,
        }
        if not payload["subject"] or not payload["grade_level"]:
            return show_toast("Subject and class are required.", "danger")

        resp = await call_api(req, "POST", "/exams/manual-submit", payload)
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(
                data.get("message", "Submission failed. Please try again."),
                "danger",
            )
        exam_id = data.get("exam_id", "")
        if not exam_id:
            return show_toast("Submission succeeded but no exam id was returned.", "warning")
        # HTMX redirect pattern: emit a meta refresh + link the user can click.
        return Div(
            show_toast("Exam created successfully! Redirecting…", "success", title="Exam Created"),
            A(
                "Open exam",
                href=f"/app/exams/{exam_id}",
                cls="btn btn-sm btn-brand mt-2",
            ),
            id="manual-result",
        )


def _parse_paste_questions(text: str) -> list:
    """Parse a paste of questions separated by blank lines.

    Recognises: 'Answer: <letter|value>' for MCQ correctness, 'Marks: <n>' for marks.
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    out: list = []
    for n, block in enumerate(blocks, start=1):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        marks = 1
        filtered: list = []
        for ln in lines:
            low = ln.strip().lower()
            if low.startswith("marks:"):
                try:
                    marks = max(1, min(100, int(low.split(":", 1)[1].strip())))
                    continue
                except ValueError:
                    pass
            filtered.append(ln.strip())
        if not filtered:
            continue
        answer = None
        body_lines: list = []
        for ln in filtered:
            low = ln.strip().lower()
            if low.startswith("answer:"):
                answer = ln.split(":", 1)[1].strip()
                continue
            body_lines.append(ln)
        body = "\n".join(body_lines).strip()
        if len(body) < 5:
            continue
        options: list = []
        cleaned_lines: list = []
        for ln in body_lines:
            if len(ln) >= 3 and ln[1:3] in (") ", ").") and ln[0].upper() in "ABCD":
                options.append(ln)
            else:
                cleaned_lines.append(ln)
        question_text = "\n".join(cleaned_lines).strip() or body
        if not options:
            options = None
        out.append(
            {
                "question_number": n,
                "type": "multiple_choice" if options else "short_answer",
                "question_text": question_text,
                "marks": marks,
                "options": options,
                "correct_answer": answer or None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Umbrella registration used by app.py
# ---------------------------------------------------------------------------

def register_routes(app):
    """Single entry-point called by app.py Ã¢â‚¬â€ wires every subgroup."""
    register_page_routes(app)
    register_wizard_routes(app)
    register_manual_routes(app)
    register_action_routes(app)
