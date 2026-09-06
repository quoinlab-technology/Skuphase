"""Question Bank browser and editor (FRONTEND_SPEC sec 6.10 & UI_design/Question-Bank.png).

Allows teachers and school admins to browse verified questions, filter by subject,
grade, and difficulty, inspect answers and explanations, and update question details.
"""

from urllib.parse import urlencode
from fasthtml.common import A, Div, Form, H1, H2, Input, Label, P, Span, Strong, Textarea, Title
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Alert, Badge, Button, Card, Col, Container, EmptyState, FormGroup, Icon, Row, Select

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _difficulty_pill(difficulty: str) -> Span:
    diff = (difficulty or "medium").lower()
    if diff == "easy":
        return Span("Easy", cls="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2 py-1 small")
    elif diff == "hard":
        return Span("Hard", cls="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-2 py-1 small")
    return Span("Medium", cls="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle rounded-pill px-2 py-1 small")


def _question_bank_card(item: dict, is_editor: bool) -> Div:
    item_id = str(item.get("id") or "")
    subject = item.get("subject", "General")
    grade = item.get("grade_level", "Primary")
    topic = item.get("topic") or ""
    difficulty = item.get("difficulty") or "medium"
    text = item.get("question_text", "No question text provided.")
    marks = item.get("marks", 1)
    options = item.get("options") or []
    correct = item.get("correct_answer") or ""
    explanation = item.get("explanation") or ""
    usage_count = item.get("usage_count", 0)

    options_div = Div()
    if options and isinstance(options, list):
        opt_letters = ["A", "B", "C", "D", "E", "F"]
        opt_rows = []
        for i, opt in enumerate(options):
            letter = opt_letters[i] if i < len(opt_letters) else str(i + 1)
            is_correct = correct and (correct.upper() == letter or correct == opt)
            cls_extra = " fw-bold text-success" if is_correct else " text-muted"
            opt_rows.append(
                Div(
                    Span(f"{letter}. ", cls="fw-bold me-1" + (" text-success" if is_correct else "")),
                    Span(str(opt)),
                    (Icon("check-circle-fill", cls="bi text-success ms-2 small") if is_correct else Div()),
                    cls=f"small py-1 px-2 mb-1 rounded {cls_extra}",
                    style="background: #f8fafc" if not is_correct else "background: #ecfdf5",
                )
            )
        options_div = Div(*opt_rows, cls="mb-2 mt-2")

    return Div(
        Div(
            Div(
                Div(Icon("book", cls="bi text-secondary fs-5"), cls="app-row-icon me-3"),
                Div(
                    Div(
                        Span((item.get("question_type") or "MCQ").replace("_", " ").upper(), cls="badge bg-light text-dark border me-2 small"),
                        _difficulty_pill(difficulty),
                        Span(f"{grade} · {subject}" + (f" · {topic}" if topic else ""), cls="text-muted small ms-2"),
                        cls="d-flex align-items-center flex-wrap mb-1",
                    ),
                    P(text, cls="fw-semibold text-dark mb-1"),
                    cls="flex-grow-1",
                ),
                Div(
                    Span(f"Used {usage_count}x", cls="badge bg-light text-secondary border me-2 small"),
                    Button(
                        Icon("pencil", cls="bi"),
                        type="button",
                        variant="outline-secondary",
                        size="sm",
                        cls="btn btn-sm btn-outline-secondary rounded-circle me-1",
                        title="Edit question",
                        **{
                            "data-bs-toggle": "modal",
                            "data-bs-target": f"#editItemModal-{item_id}",
                        },
                    ) if is_editor else Div(),
                    Button(
                        Icon("chevron-down", cls="bi"),
                        type="button",
                        cls="btn btn-sm btn-link text-muted p-1",
                        **{"data-bs-toggle": "collapse", "data-bs-target": f"#bank-detail-{item_id}"},
                    ),
                    cls="d-flex align-items-center ms-3",
                ),
                cls="d-flex align-items-center p-3",
            ),
            # Collapsible details (options, explanation, correct answer)
            Div(
                Div(
                    options_div,
                    (Div(
                        Icon("info-circle", cls="bi me-1 text-primary"),
                        Span(Strong("Explanation: "), explanation, cls="small text-muted"),
                        cls="p-2 mb-2 rounded bg-light border-start border-3 border-primary",
                    ) if explanation else Div()),
                    Div(
                        Span(f"Value: {marks} mark{'s' if marks > 1 else ''}", cls="badge bg-light text-dark border me-2"),
                        Span(f"Saved to school repository", cls="text-muted small"),
                        cls="d-flex align-items-center pt-2 border-top",
                    ),
                    cls="p-3 pt-0",
                ),
                id=f"bank-detail-{item_id}",
                cls="collapse",
            ),
            cls="card shadow-sm border-0 mb-3 rounded-3",
            id=f"bank-item-{item_id}",
        ),
        _edit_modal(item) if is_editor else Div(),
    )


def _edit_modal(item: dict) -> Div:
    item_id = str(item.get("id") or "")
    text = item.get("question_text", "")
    difficulty = (item.get("difficulty") or "medium").lower()
    marks = str(item.get("marks") or 1)
    topic = item.get("topic") or ""
    explanation = item.get("explanation") or ""
    correct = item.get("correct_answer") or ""

    return Div(
        Div(
            Div(
                Div(
                    Strong("Edit Question Bank Item", cls="fs-5 text-dark"),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header pb-2",
                ),
                Form(
                    Div(
                        FormGroup("Question Text", Textarea(text, name="question_text", rows=3, cls="form-control", required=True), cls="mb-3"),
                        Row(
                            Col(
                                FormGroup("Difficulty", Select("difficulty", ("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), value=difficulty, cls="form-select")),
                                md=4,
                            ),
                            Col(
                                FormGroup("Marks", Input("marks", type="number", value=marks, min="1", max="100", cls="form-control")),
                                md=4,
                            ),
                            Col(
                                FormGroup("Correct Option", Input("correct_answer", value=correct, placeholder="e.g. A", cls="form-control")),
                                md=4,
                            ),
                            cls="mb-3",
                        ),
                        FormGroup("Topic", Input("topic", value=topic, placeholder="Curriculum topic...", cls="form-control"), cls="mb-3"),
                        FormGroup("Explanation", Textarea(explanation, name="explanation", rows=2, cls="form-control"), cls="mb-3"),
                        cls="modal-body py-2",
                    ),
                    Div(
                        Button("Cancel", type="button", variant="outline-secondary", **{"data-bs-dismiss": "modal"}),
                        Button("Save Changes", type="submit", variant="success", cls="btn-brand ms-2"),
                        cls="modal-footer pt-2",
                    ),
                    action=f"/app/bank/items/{item_id}",
                    method="post",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"editItemModal-{item_id}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _add_question_modal() -> Div:
    """Modal to add reusable question to bank matching UI_design/Question-Bank3.png."""
    grades = [
        ("Primary 1", "Primary 1"),
        ("Primary 2", "Primary 2"),
        ("Primary 3", "Primary 3"),
        ("Primary 4", "Primary 4"),
        ("Primary 5", "Primary 5"),
        ("Primary 6", "Primary 6"),
    ]
    subjects = [
        ("Mathematics", "Mathematics"),
        ("English Language", "English Language"),
        ("Basic Science", "Basic Science"),
        ("Social Studies", "Social Studies"),
        ("National Values", "National Values"),
        ("Prevocational Studies", "Prevocational Studies"),
    ]
    types = [
        ("multiple_choice", "MCQ (Multiple Choice)"),
        ("short_answer", "Short Answer"),
        ("essay", "Essay / Theory"),
    ]
    diffs = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Add Question to Bank", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Manually add a reusable question.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Form(
                    Div(
                        FormGroup("Question Text", Textarea(name="question_text", rows=3, placeholder="Enter the question...", required=True, cls="form-control mb-3")),
                        Row(
                            Col(FormGroup("Subject", Select("subject", *subjects, cls="form-select")), md=6),
                            Col(FormGroup("Grade", Select("grade_level", *grades, cls="form-select")), md=6),
                            cls="mb-3",
                        ),
                        Row(
                            Col(FormGroup("Type", Select("question_type", *types, cls="form-select")), md=6),
                            Col(FormGroup("Difficulty", Select("difficulty", *diffs, value="easy", cls="form-select")), md=6),
                            cls="mb-3",
                        ),
                        FormGroup("Topic", Input("topic", placeholder="e.g. Quadratic Equations, Fractions...", cls="form-control mb-3")),
                        FormGroup("Marks", Input("marks", type="number", value="1", min="1", max="100", cls="form-control mb-3")),
                        FormGroup("Explanation (optional)", Textarea(name="explanation", rows=2, placeholder="Explanation or marking guide...", cls="form-control mb-3")),
                        cls="modal-body py-2 px-4",
                    ),
                    Div(
                        Button("Cancel", type="button", variant="light", cls="btn btn-light rounded-pill px-3 me-2", **{"data-bs-dismiss": "modal"}),
                        Button("Add Question", type="submit", variant="success", cls="btn-brand rounded-pill px-4"),
                        cls="modal-footer border-0 pt-2 pb-4 px-4",
                    ),
                    action="/app/bank/new",
                    method="post",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id="addQuestionModal",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


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
        diff_filter = req.query_params.get("difficulty", "").strip()

        params = {"limit": "50"}
        if q:
            params["query_text"] = q
        if subject_filter:
            params["subject"] = subject_filter
        if grade_filter:
            params["grade_level"] = grade_filter

        resp = await call_api(req, "GET", "/exams/question-bank/items", params=params)
        ok, data = unwrap(resp)
        all_items = data if (ok and isinstance(data, list)) else []

        if diff_filter:
            all_items = [i for i in all_items if (i.get("difficulty") or "").lower() == diff_filter.lower()]

        # Compute metric totals
        total_items = len(all_items)
        easy_cnt = sum(1 for i in all_items if (i.get("difficulty") or "").lower() == "easy")
        med_cnt = sum(1 for i in all_items if (i.get("difficulty") or "").lower() == "medium")
        hard_cnt = sum(1 for i in all_items if (i.get("difficulty") or "").lower() == "hard")

        # Metric cards
        metrics = Row(
            Col(
                Div(
                    Div(Icon("collection", cls="bi"), cls="app-metric-icon-wrap icon-blue-light"),
                    Div(Div(str(total_items), cls="app-metric-value"), Div("Total Questions", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=12, sm=4,
            ),
            Col(
                Div(
                    Div(Icon("mortarboard", cls="bi"), cls="app-metric-icon-wrap icon-green-light"),
                    Div(Div("Primary 1-6", cls="app-metric-value"), Div("Active Curriculum", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=12, sm=4,
            ),
            Col(
                Div(
                    Div(Icon("bar-chart", cls="bi"), cls="app-metric-icon-wrap icon-amber-light"),
                    Div(Div(f"{easy_cnt}E · {med_cnt}M · {hard_cnt}H", cls="app-metric-value fs-4"), Div("Difficulty Spread", cls="app-metric-label")),
                    cls="app-metric-card",
                ),
                span=12, sm=4,
            ),
            g=3,
            cls="mb-4",
        )

        header = Div(
            Div(
                H1("Question Bank", cls="fw-bold fs-2 text-dark mb-1"),
                P("Reusable questions saved from generated exams or added manually.", cls="text-muted small mb-0"),
            ),
            Div(
                Button(
                    Icon("plus-lg", cls="bi me-1"),
                    "Add Question",
                    type="button",
                    cls="btn btn-dark rounded-pill px-3 fw-semibold shadow-sm",
                    **{"data-bs-toggle": "modal", "data-bs-target": "#addQuestionModal"},
                ) if is_editor else Div(),
            ),
            cls="d-flex flex-wrap justify-content-between align-items-center mb-4",
        )

        grades = [
            ("", "All Grades"),
            ("Primary 1", "Primary 1"),
            ("Primary 2", "Primary 2"),
            ("Primary 3", "Primary 3"),
            ("Primary 4", "Primary 4"),
            ("Primary 5", "Primary 5"),
            ("Primary 6", "Primary 6"),
        ]

        subjects = [
            ("", "All Subjects"),
            ("Mathematics", "Mathematics"),
            ("English Language", "English Language"),
            ("Basic Science and Technology", "Basic Science"),
            ("National Values Education", "National Values"),
            ("Pre-Vocational Studies", "Pre-Vocational"),
        ]

        diffs = [
            ("", "All Difficulties"),
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard"),
        ]

        search_bar = Form(
            Row(
                Col(
                    Input("q", value=q, placeholder="Search questions by keyword...", cls="app-search-input"),
                    span=12, md=4,
                ),
                Col(
                    Select("subject", *subjects, value=subject_filter, cls="form-select rounded-pill"),
                    span=6, md=3,
                ),
                Col(
                    Select("grade", *grades, value=grade_filter, cls="form-select rounded-pill"),
                    span=6, md=2,
                ),
                Col(
                    Select("difficulty", *diffs, value=diff_filter, cls="form-select rounded-pill"),
                    span=6, md=2,
                ),
                Col(
                    Button("Filter", type="submit", size="sm", cls="btn-brand w-100 rounded-pill py-2"),
                    span=6, md=1,
                ),
                g=2,
                cls="align-items-center",
            ),
            method="get",
            action="/app/bank",
            cls="app-card p-3 mb-4",
        )

        if all_items:
            cards = [_question_bank_card(i, is_editor) for i in all_items]
            list_content = Div(*cards)
        else:
            list_content = EmptyState(
                title="No questions in bank yet",
                description="Questions are automatically saved into your school bank when approved, or can be saved directly from any exam detail.",
                action=Button("View Exams", as_="a", href="/app/exams", cls="btn-brand"),
            )

        return AppShell(
            Title("Question Bank — SkuPhase"),
            Div(
                header,
                metrics,
                search_bar,
                list_content,
                _add_question_modal() if is_editor else Div(),
            ),
            user=user,
            active="bank",
            flash=flash,
            crumbs=[("Question Bank", None)],
        )

    @app.post("/app/bank/new")
    async def create_bank_item(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        text = (form.get("question_text") or "").strip()
        subject = (form.get("subject") or "Mathematics").strip()
        grade = (form.get("grade_level") or "Primary 1").strip()
        qtype = (form.get("question_type") or "multiple_choice").strip()
        diff = (form.get("difficulty") or "medium").strip()
        topic = (form.get("topic") or "").strip()
        marks = int(form.get("marks") or 1)
        explanation = (form.get("explanation") or "").strip()

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
        payload = {
            "question_text": form.get("question_text", "").strip() or None,
            "difficulty": form.get("difficulty", "medium").strip() or None,
            "marks": int(form.get("marks", 1)) if form.get("marks") else None,
            "correct_answer": form.get("correct_answer", "").strip() or None,
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
