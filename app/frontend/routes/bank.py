"""Question Bank browser and editor (Phase 7: P07_question_bank_*.png).

Allows teachers and school admins to browse verified questions, filter by subject,
grade, difficulty, and type, inspect answers and explanations, and update question details.
Supports two-way integration: inserting questions from the bank into specific exam sections.
"""

from urllib.parse import urlencode
from fasthtml.common import (
    A,
    Button as HtmlButton,
    Div,
    Form,
    H1,
    H2,
    Input,
    Label,
    P,
    Script,
    Span,
    Strong,
    Textarea,
    Title,
)
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from faststrap import (
    Alert,
    Badge,
    Button,
    Card,
    Col,
    Container,
    EmptyState,
    FormGroup,
    Icon,
    Row,
    Select,
)

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash, show_toast
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login
from app.frontend.components.bank import BankCard, BankMetricsBar, AddQuestionModal
from app.services.curriculum_taxonomy import ALL_SUBJECTS, CLASS_LEVELS


# Backward-compatibility alias
def _difficulty_pill(difficulty: str) -> Span:
    diff = (difficulty or "medium").lower()
    if diff == "easy":
        return Span("Easy", cls="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2 py-1 small")
    elif diff == "hard":
        return Span("Hard", cls="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-2 py-1 small")
    return Span("Medium", cls="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle rounded-pill px-2 py-1 small")


def _question_bank_card(item: dict, is_editor: bool) -> Div:
    return BankCard(item, is_editor)


def _render_bank_list_content(items: list[dict], is_editor: bool, editable_exams: list[dict]) -> Div:
    """Render the metrics counter row and card list (or empty state)."""
    total = len(items)
    easy = sum(1 for i in items if (i.get("difficulty") or "").lower() == "easy")
    medium = sum(1 for i in items if (i.get("difficulty") or "").lower() == "medium")
    hard = sum(1 for i in items if (i.get("difficulty") or "").lower() == "hard")

    metrics = BankMetricsBar(total=total, easy=easy, medium=medium, hard=hard)

    if items:
        cards = [BankCard(i, is_editor, editable_exams) for i in items]
        card_list = Div(*cards)
    else:
        card_list = EmptyState(
            title="No questions in bank yet",
            description="Questions are automatically saved into your school bank when approved, or can be saved directly from any exam detail.",
            action=Button("View Exams", as_="a", href="/app/exams", cls="btn-brand rounded-pill px-4"),
        )

    return Div(metrics, card_list, id="bank-items-container")


async def _fetch_bank_items_and_exams(req: Request, q: str = "", subject: str = "", grade: str = "", qtype: str = "", difficulty: str = ""):
    """Query bank items and editable exams in parallel or sequence."""
    params = {"limit": "100"}
    if q:
        params["query_text"] = q
    if subject and subject.lower() != "all":
        params["subject"] = subject
    if grade and grade.lower() != "all":
        params["grade_level"] = grade
    if difficulty and difficulty.lower() != "all":
        params["difficulty"] = difficulty

    resp = await call_api(req, "GET", "/exams/question-bank/items", params=params)
    ok, data = unwrap(resp)
    items = data if (ok and isinstance(data, list)) else []

    # Optional local filter for question_type
    if qtype and qtype.lower() != "all":
        items = [
            i for i in items
            if qtype.lower() in (i.get("question_type") or "").lower()
        ]

    # Fetch editable exams
    exam_resp = await call_api(req, "GET", "/exams", params={"limit": "30"})
    e_ok, e_data = unwrap(exam_resp)
    all_exams = e_data.get("items") if (e_ok and isinstance(e_data, dict)) else (e_data if isinstance(e_data, list) else [])
    editable_states = {"draft", "teacher_review", "final_submitted_by_teacher"}
    editable_exams = [
        e for e in (all_exams or [])
        if e.get("workflow_state") in editable_states or e.get("status") in editable_states
    ]

    return items, editable_exams


def register_routes(app):
    @app.get("/app/bank")
    async def question_bank_page(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        role = user.get("role") or ""
        is_editor = role in {"teacher", "school_admin"} or user.get("account_type") == "individual_teacher"
        flash = pop_flash(req)

        q = req.query_params.get("q", "").strip()
        subject_filter = req.query_params.get("subject", "").strip()
        grade_filter = req.query_params.get("grade", "").strip()
        type_filter = req.query_params.get("type", "").strip()
        diff_filter = req.query_params.get("difficulty", "").strip()

        items, editable_exams = await _fetch_bank_items_and_exams(
            req, q=q, subject=subject_filter, grade=grade_filter, qtype=type_filter, difficulty=diff_filter
        )

        header = Div(
            Div(
                H1("Question Bank", cls="fw-bold fs-2 text-dark mb-1"),
                P("Reusable questions saved from generated exams or added manually.", cls="text-muted small mb-0"),
            ),
            Div(
                HtmlButton(
                    Icon("funnel", cls="bi me-2"),
                    "Filters",
                    type="button",
                    cls="btn btn-outline-secondary bg-white rounded-pill px-4 py-2 fw-medium shadow-sm me-2",
                    **{"data-bs-toggle": "collapse", "data-bs-target": "#bank-filter-tray"},
                ),
                Button(
                    Icon("plus-lg", cls="bi me-2"),
                    "Add Question",
                    type="button",
                    cls="btn btn-brand rounded-pill px-4 py-2 fw-medium shadow-sm",
                    **{"data-bs-toggle": "modal", "data-bs-target": "#addQuestionModal"},
                ) if is_editor else Div(),
                cls="d-flex align-items-center mt-3 mt-md-0",
            ),
            cls="d-flex flex-wrap justify-content-between align-items-center mb-4",
        )

        # Search Bar matching P07
        search_bar = Div(
            Icon("search", cls="bi position-absolute text-muted", style="left: 1rem; top: 50%; transform: translateY(-50%); font-size: 1rem; pointer-events: none; z-index: 5;"),
            Input(
                name="q",
                value=q,
                placeholder="Search questions or topics...",
                cls="form-control bank-search-input w-100",
                hx_get="/ui/bank/list",
                hx_target="#bank-items-container",
                hx_swap="outerHTML",
                hx_trigger="input changed delay:300ms, search",
                hx_include="#bank-filter-form",
            ),
            cls="position-relative mb-3",
            id="bank-search-wrapper",
        )

        # Dropdown options matching P07
        subjects = [("All", "All"), *[(label, label) for label in ALL_SUBJECTS]]
        grades = [("All", "All"), *[(label, label) for label in CLASS_LEVELS]]
        types = [
            ("All", "All"),
            ("multiple_choice", "MCQ"),
            ("short_answer", "Short Answer"),
            ("essay", "Essay"),
        ]
        diffs = [
            ("All", "All"),
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard"),
        ]

        # Filter Tray — hidden by default (collapsible) as seen in P07_question_bank_default_desktop.png
        filter_tray = Div(
            Form(
                Row(
                    Col(
                        Div(
                            Label("Subject", cls="form-label small fw-semibold text-secondary mb-1"),
                            Select("subject", *subjects, value=subject_filter or "All", cls="form-select rounded-3"),
                        ),
                        span=12, sm=6, md=3,
                        cls="mb-3",
                    ),
                    Col(
                        Div(
                            Label("Grade", cls="form-label small fw-semibold text-secondary mb-1"),
                            Select("grade", *grades, value=grade_filter or "All", cls="form-select rounded-3"),
                        ),
                        span=12, sm=6, md=3,
                        cls="mb-3",
                    ),
                    Col(
                        Div(
                            Label("Type", cls="form-label small fw-semibold text-secondary mb-1"),
                            Select("type", *types, value=type_filter or "All", cls="form-select rounded-3"),
                        ),
                        span=12, sm=6, md=3,
                        cls="mb-3",
                    ),
                    Col(
                        Div(
                            Label("Difficulty", cls="form-label small fw-semibold text-secondary mb-1"),
                            Select("difficulty", *diffs, value=diff_filter or "All", cls="form-select rounded-3"),
                        ),
                        span=12, sm=6, md=3,
                        cls="mb-3",
                    ),
                    g=3,
                    cls="align-items-end",
                ),
                id="bank-filter-form",
                hx_get="/ui/bank/list",
                hx_target="#bank-items-container",
                hx_swap="outerHTML",
                hx_trigger="change",
                hx_include="#bank-search-wrapper input",
            ),
            id="bank-filter-tray",
            cls="bank-filter-tray collapse mb-4" + (" show" if (subject_filter or grade_filter or type_filter or diff_filter) else ""),
        )

        items_container = _render_bank_list_content(items, is_editor, editable_exams)

        return AppShell(
            Title("Question Bank — SkuPhase"),
            Div(
                header,
                search_bar,
                filter_tray,
                items_container,
                AddQuestionModal() if is_editor else Div(),
            ),
            user=user,
            active="bank",
            flash=flash,
            crumbs=[("Question Bank", None)],
        )

    @app.get("/ui/bank/list")
    async def bank_list_partial(req: Request):
        """HTMX partial endpoint for dynamic search and filter swaps."""
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        role = user.get("role") or ""
        is_editor = role in {"teacher", "school_admin"} or user.get("account_type") == "individual_teacher"

        q = req.query_params.get("q", "").strip()
        subject_filter = req.query_params.get("subject", "").strip()
        grade_filter = req.query_params.get("grade", "").strip()
        type_filter = req.query_params.get("type", "").strip()
        diff_filter = req.query_params.get("difficulty", "").strip()

        items, editable_exams = await _fetch_bank_items_and_exams(
            req, q=q, subject=subject_filter, grade=grade_filter, qtype=type_filter, difficulty=diff_filter
        )

        return _render_bank_list_content(items, is_editor, editable_exams)

    @app.delete("/ui/bank/items/{item_id}")
    async def delete_bank_item_ui(req: Request, item_id: str):
        """HTMX delete bank item endpoint with toast response."""
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "DELETE", f"/exams/question-bank/items/{item_id}")
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(
                data.get("message", "Could not delete question from bank."),
                "danger",
                hx_swap_oob="beforeend:#app-toast-container",
            )
        return Div(
            show_toast("Question removed from school question bank.", "success", title="Deleted", hx_swap_oob="beforeend:#app-toast-container"),
        )

    @app.post("/ui/bank/items/{item_id}/add-to-exam")
    async def add_item_to_exam_ui(req: Request, item_id: str):
        """HTMX action to insert a question bank item into an exam section."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        exam_id = (form.get("exam_id") or "").strip()
        sec_num = int(form.get("section_number") or 1)
        sec_name = f"Section {chr(64 + sec_num)}"

        if not exam_id:
            return show_toast("Please select a target exam.", "warning")

        payload = {
            "bank_item_ids": [item_id],
            "section_number": sec_num,
            "section_name": sec_name,
        }
        resp = await call_api(req, "POST", f"/exams/{exam_id}/questions/import-from-bank", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not add question to exam."), "danger")

        script = Script(f"var m = bootstrap.Modal.getInstance(document.getElementById('addToExamModal-{item_id}')); if(m) m.hide();")
        toast = show_toast(
            f"Question added to {sec_name} of exam successfully!",
            "success",
            title="Added to Exam",
            hx_swap_oob="beforeend:#app-toast-container",
        )
        return Div(toast, script)

    @app.post("/app/bank/new")
    @app.post("/app/bank/add")
    async def create_bank_item(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        text = (form.get("question_text") or "").strip()
        subject = (form.get("subject") or "Mathematics").strip()
        grade = (form.get("grade_level") or "JSS1").strip()
        qtype = (form.get("question_type") or "multiple_choice").strip()
        diff = (form.get("difficulty") or "easy").strip()
        topic = (form.get("topic") or "").strip()
        marks = int(form.get("marks") or 1)
        correct = (form.get("correct_answer") or "").strip()
        explanation = (form.get("explanation") or "").strip()

        # Parse options
        options_raw = form.get("options") or ""
        options = [o.strip() for o in options_raw.splitlines() if o.strip()] if options_raw else None

        if len(text) < 3:
            push_flash(req, "Question text must be at least 3 characters.", "danger")
            return RedirectResponse("/app/bank", status_code=303)

        payload = {
            "subject": subject,
            "grade_level": grade,
            "question_type": qtype,
            "difficulty": diff,
            "topic": topic if topic else None,
            "question_text": text,
            "marks": marks,
            "options": options,
            "correct_answer": correct if correct else None,
            "explanation": explanation if explanation else None,
        }
        resp = await call_api(req, "POST", "/exams/question-bank/items", json=payload)
        ok, data = unwrap(resp)
        if ok:
            push_flash(req, "Question added to bank successfully!", "success")
        else:
            push_flash(req, data.get("message", "Failed to add question."), "danger")
        return RedirectResponse("/app/bank", status_code=303)

    @app.post("/app/bank/items/{item_id}")
    async def update_bank_item(req: Request, item_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        options_raw = form.get("options") or ""
        options = [o.strip() for o in options_raw.splitlines() if o.strip()] if options_raw else None

        payload = {
            "question_text": form.get("question_text", "").strip() or None,
            "difficulty": form.get("difficulty", "medium").strip() or None,
            "marks": int(form.get("marks", 1)) if form.get("marks") else None,
            "correct_answer": form.get("correct_answer", "").strip() or None,
            "options": options,
            "topic": form.get("topic", "").strip() or None,
            "explanation": form.get("explanation", "").strip() or None,
        }
        resp = await call_api(req, "PATCH", f"/exams/question-bank/items/{item_id}", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            push_flash(req, data.get("message", "Failed to update question item."), "danger")
        else:
            push_flash(req, "Question item updated successfully.", "success")
        return RedirectResponse("/app/bank", status_code=303)
