"""Question Bank UI components (Phase 7: P07_question_bank_*.png)."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from fasthtml.common import (
    A,
    Button as HtmlButton,
    Div,
    Form,
    H4,
    H5,
    Input,
    Label,
    P,
    Span,
    Strong,
    Textarea,
)

from faststrap import (
    Badge,
    Button,
    Col,
    Dropdown,
    DropdownDivider,
    DropdownItem,
    Icon,
    Row,
    Select,
)

from app.frontend.components.exam import render_rich_text


def BankMetricsBar(total: int, easy: int, medium: int, hard: int) -> Div:
    """Summary badge counter row matching P07."""
    return Div(
        Span(f"{total} questions", cls="fw-bold text-dark me-3"),
        Span(f"{easy} easy", cls="bank-pill-easy me-2"),
        Span(f"{medium} medium", cls="bank-pill-medium me-2"),
        Span(f"{hard} hard", cls="bank-pill-hard"),
        cls="d-flex align-items-center mb-4",
        id="bank-metrics-bar",
    )


def BankCard(item: dict, is_editor: bool, editable_exams: list[dict] = None) -> Div:
    """Question Bank Card matching P07_question_bank_default_desktop.png."""
    item_id = str(item.get("id") or "")
    subject = item.get("subject", "General")
    grade = item.get("grade_level", "Primary")
    topic = item.get("topic") or ""
    diff = (item.get("difficulty") or "medium").lower()
    q_type_raw = item.get("question_type") or "multiple_choice"
    
    # Format type label (MCQ, Short Answer, Essay)
    if "choice" in q_type_raw.lower() or "mcq" in q_type_raw.lower():
        type_label = "MCQ"
    elif "short" in q_type_raw.lower():
        type_label = "Short Answer"
    elif "essay" in q_type_raw.lower() or "theory" in q_type_raw.lower():
        type_label = "Essay"
    else:
        type_label = q_type_raw.replace("_", " ").title()

    text = item.get("question_text", "No question text provided.")
    marks = item.get("marks", 1)
    options = item.get("options") or []
    correct = item.get("correct_answer") or ""
    explanation = item.get("explanation") or ""
    usage_count = item.get("usage_count", 0)

    # Collapsible options block
    options_rows = []
    if options and isinstance(options, list):
        opt_letters = ["A", "B", "C", "D", "E", "F"]
        for i, opt in enumerate(options):
            letter = opt_letters[i] if i < len(opt_letters) else str(i + 1)
            is_correct = correct and (correct.upper() == letter or correct == opt)
            cls_bg = "background: #ecfdf5; border-color: #a7f3d0;" if is_correct else "background: #f8fafc; border-color: #f1f5f9;"
            options_rows.append(
                Div(
                    Span(f"{letter}. ", cls="fw-bold me-1 text-success" if is_correct else "fw-bold me-1 text-secondary"),
                    Span(str(opt), cls="text-dark" if not is_correct else "text-success fw-medium"),
                    (Icon("check-circle-fill", cls="bi text-success ms-2 small") if is_correct else Div()),
                    cls="small py-1 px-3 mb-1 rounded-3 border d-flex align-items-center",
                    style=cls_bg,
                )
            )

    collapse_id = f"bank-detail-{item_id}"
    delete_modal_id = f"deleteBankModal-{item_id}"
    edit_modal_id = f"editBankModal-{item_id}"
    add_exam_modal_id = f"addToExamModal-{item_id}"

    # Dropdown menu items for Kebab menu
    kebab_items = []
    if is_editor:
        kebab_items.extend([
            DropdownItem(
                Icon("pencil", cls="me-2 text-primary"),
                "Edit Question",
                href="#",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#{edit_modal_id}"},
            ),
            DropdownItem(
                Icon("journal-plus", cls="me-2 text-success"),
                "Add to Exam Section...",
                href="#",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#{add_exam_modal_id}"},
            ),
            DropdownDivider(),
            DropdownItem(
                Icon("trash", cls="me-2 text-danger"),
                "Delete from Bank",
                href="#",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#{delete_modal_id}"},
            ),
        ])

    kebab_menu = (
        Dropdown(
            *kebab_items,
            label=Icon("three-dots-vertical"),
            variant="light",
            size="sm",
            toggle_cls="btn btn-sm btn-link text-muted p-1 text-decoration-none shadow-none",
            direction="end",
            menu_cls="dropdown-menu-end shadow border rounded-3 py-1",
        )
        if is_editor
        else Div()
    )

    card_header = Div(
        Div(Icon("book", cls="bi fs-5 text-muted"), cls="bank-card-icon me-2 me-sm-3 flex-shrink-0"),
        Div(
            Div(
                Span(type_label, cls="bank-badge-type me-2 flex-shrink-0"),
                Span(diff.capitalize(), cls=f"bank-badge-diff-{diff} me-2 flex-shrink-0"),
                Span(f"{subject} · {grade}" + (f" · {topic}" if topic else ""), cls="text-muted small text-truncate", style="max-width: 180px;"),
                cls="d-flex align-items-center flex-wrap mb-1 min-w-0",
                style="min-width: 0;",
            ),
            P(render_rich_text(text), cls="fw-semibold text-dark mb-0 fs-6 text-break", style="word-break:break-word; overflow-wrap:anywhere; min-width: 0;"),
            cls="flex-grow-1 min-w-0 me-2",
            style="min-width: 0;",
        ),
        Div(
            Span(f"Used {usage_count}x", cls="bank-usage-badge me-2 d-none d-sm-inline-flex flex-shrink-0"),
            kebab_menu,
            HtmlButton(
                Icon("chevron-down", cls="bi text-muted"),
                type="button",
                cls="btn btn-sm btn-link text-muted p-1 text-decoration-none shadow-none ms-1 flex-shrink-0",
                **{"data-bs-toggle": "collapse", "data-bs-target": f"#{collapse_id}"},
            ),
            cls="d-flex align-items-center ms-auto flex-shrink-0",
        ),
        cls="d-flex align-items-start w-100",
        style="min-width: 0;",
    )

    card_collapsible = Div(
        Div(
            Div(*options_rows, cls="mb-2") if options_rows else Div(),
            (
                Div(
                    Icon("check2-circle", cls="bi me-2 text-success"),
                    Strong("Correct Answer: ", cls="text-dark small"),
                    Span(correct, cls="small text-muted"),
                    cls="p-2 mb-2 rounded-3 bg-light border-start border-3 border-success d-flex align-items-center",
                )
                if (correct and not options_rows)
                else Div()
            ),
            (
                Div(
                    Icon("info-circle", cls="bi me-2 text-primary"),
                    Strong("Explanation: ", cls="text-dark small"),
                    Span(render_rich_text(explanation), cls="small text-muted"),
                    cls="p-2 mb-2 rounded-3 bg-light border-start border-3 border-primary d-flex align-items-start",
                )
                if explanation
                else Div()
            ),
            Div(
                Span(f"Value: {marks} mark{'s' if marks > 1 else ''}", cls="badge bg-light text-dark border me-2 small"),
                Span("Stored in school repository", cls="text-muted small"),
                cls="d-flex align-items-center pt-2 border-top mt-2",
            ),
            cls="pt-3 border-top mt-3",
        ),
        id=collapse_id,
        cls="collapse",
        style="min-width: 0;",
    )

    card = Div(
        card_header,
        card_collapsible,
        cls="bank-card",
        id=f"bank-card-{item_id}",
        style="min-width: 0; max-width: 100%; box-sizing: border-box;",
    )

    modals = []
    if is_editor:
        # Edit Modal
        modals.append(_edit_bank_modal(item, edit_modal_id))
        # Add to Exam Modal
        modals.append(_add_to_exam_modal(item, add_exam_modal_id, editable_exams or []))
        # Delete Modal (with hx-on::before-request close)
        modals.append(_delete_bank_modal(item, delete_modal_id))

    return Div(card, *modals)


def _edit_bank_modal(item: dict, modal_id: str) -> Div:
    """Edit Bank Item Modal."""
    item_id = str(item.get("id") or "")
    text = item.get("question_text", "")
    diff = (item.get("difficulty") or "medium").lower()
    marks = str(item.get("marks") or 1)
    topic = item.get("topic") or ""
    explanation = item.get("explanation") or ""
    correct = item.get("correct_answer") or ""
    options = item.get("options") or []
    options_text = "\n".join(options) if isinstance(options, list) else ""

    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Edit Question Bank Item", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Update reusable question details and marking guide.", cls="text-muted small"),
                    ),
                    HtmlButton("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Form(
                    Div(
                        Div(
                            Label("Question Text", cls="form-label small fw-semibold"),
                            Textarea(text, name="question_text", rows=3, cls="form-control rounded-3", required=True),
                            cls="mb-3",
                        ),
                        Row(
                            Col(
                                Label("Difficulty", cls="form-label small fw-semibold"),
                                Select("difficulty", ("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), value=diff, cls="form-select rounded-3"),
                                md=4,
                            ),
                            Col(
                                Label("Marks", cls="form-label small fw-semibold"),
                                Input("marks", type="number", value=marks, min="1", max="100", cls="form-control rounded-3"),
                                md=4,
                            ),
                            Col(
                                Label("Correct Option", cls="form-label small fw-semibold"),
                                Input("correct_answer", value=correct, placeholder="e.g. A or answer", cls="form-control rounded-3"),
                                md=4,
                            ),
                            cls="mb-3",
                        ),
                        Div(
                            Label("Options (one per line for MCQ)", cls="form-label small fw-semibold"),
                            Textarea(options_text, name="options", rows=max(2, len(options) if options else 2), cls="form-control rounded-3 font-monospace"),
                            cls="mb-3",
                        ),
                        Div(
                            Label("Topic", cls="form-label small fw-semibold"),
                            Input("topic", value=topic, placeholder="e.g. Quadratic Equations", cls="form-control rounded-3"),
                            cls="mb-3",
                        ),
                        Div(
                            Label("Explanation", cls="form-label small fw-semibold"),
                            Textarea(explanation, name="explanation", rows=2, cls="form-control rounded-3"),
                            cls="mb-3",
                        ),
                        cls="modal-body py-2 px-4",
                    ),
                    Div(
                        HtmlButton("Cancel", type="button", cls="btn btn-light rounded-pill px-4 py-2 me-2", **{"data-bs-dismiss": "modal"}),
                        Button("Save Changes", type="submit", variant="success", cls="btn-brand rounded-pill px-4 py-2"),
                        cls="modal-footer border-0 pt-2 pb-4 px-4",
                    ),
                    action=f"/app/bank/items/{item_id}",
                    method="post",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=modal_id,
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _delete_bank_modal(item: dict, modal_id: str) -> Div:
    """Delete Bank Item Modal (closes cleanly before HTMX fires)."""
    item_id = str(item.get("id") or "")
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Delete from Question Bank", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Are you sure you want to remove this question from the school bank?", cls="text-muted small mt-1 d-block"),
                    ),
                    HtmlButton("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Div(
                    HtmlButton("Cancel", type="button", cls="btn btn-light rounded-pill px-4 py-2 me-2", **{"data-bs-dismiss": "modal"}),
                    HtmlButton(
                        "Delete Question",
                        type="button",
                        cls="btn btn-danger rounded-pill px-4 py-2",
                        **{
                            "hx-delete": f"/ui/bank/items/{item_id}",
                            "hx-target": f"#bank-card-{item_id}",
                            "hx-swap": "outerHTML",
                            "hx-on::before-request": (
                                f"var m=bootstrap.Modal.getInstance(document.getElementById('{modal_id}'));"
                                "if(m)m.hide();"
                            ),
                        },
                    ),
                    cls="modal-footer border-0 pt-3 pb-4 px-4 d-flex justify-content-end",
                ),
                cls="modal-content border-0 shadow-lg rounded-4 p-2",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=modal_id,
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _add_to_exam_modal(item: dict, modal_id: str, editable_exams: list[dict]) -> Div:
    """Modal to insert this bank item directly into an active exam's section."""
    item_id = str(item.get("id") or "")
    
    exam_options = []
    if editable_exams:
        for ex in editable_exams:
            eid = str(ex.get("id") or "")
            title = f"{ex.get('subject', '')} ({ex.get('grade_level', '')} - {ex.get('term', '')})"
            exam_options.append((eid, title))
    else:
        exam_options.append(("", "No active draft/review exams found"))

    section_options = [
        ("1", "Section A (Objectives / MCQ)"),
        ("2", "Section B (Theory / Short Answer)"),
        ("3", "Section C (Essay / Comprehension)"),
    ]

    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Add to Exam Section", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Select the target exam and section to append this question.", cls="text-muted small"),
                    ),
                    HtmlButton("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Form(
                    Div(
                        Div(
                            Label("Target Exam", cls="form-label small fw-semibold"),
                            Select("exam_id", *exam_options, cls="form-select rounded-3", required=True),
                            cls="mb-3",
                        ),
                        Div(
                            Label("Target Section", cls="form-label small fw-semibold"),
                            Select("section_number", *section_options, value="1", cls="form-select rounded-3"),
                            cls="mb-3",
                        ),
                        Div(id=f"add-to-exam-result-{item_id}", cls="mb-2"),
                        cls="modal-body py-2 px-4",
                    ),
                    Div(
                        HtmlButton("Cancel", type="button", cls="btn btn-light rounded-pill px-4 py-2 me-2", **{"data-bs-dismiss": "modal"}),
                        Button(
                            "Insert Question",
                            type="submit",
                            variant="success",
                            cls="btn-brand rounded-pill px-4 py-2",
                            disabled=not bool(editable_exams),
                        ),
                        cls="modal-footer border-0 pt-2 pb-4 px-4",
                    ),
                    hx_post=f"/ui/bank/items/{item_id}/add-to-exam",
                    hx_target=f"#add-to-exam-result-{item_id}",
                    hx_swap="innerHTML",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=modal_id,
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def AddQuestionModal() -> Div:
    """Add Question to Bank modal matching P07_question_bank_edit_modal_desktop.png."""
    grades = [
        ("JSS1", "JSS1"),
        ("JSS2", "JSS2"),
        ("JSS3", "JSS3"),
        ("SS1", "SS1"),
        ("SS2", "SS2"),
        ("SS3", "SS3"),
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
        ("Chemistry", "Chemistry"),
        ("Physics", "Physics"),
        ("Biology", "Biology"),
        ("Basic Science", "Basic Science"),
        ("Social Studies", "Social Studies"),
        ("Economics", "Economics"),
        ("Civic Education", "Civic Education"),
    ]
    types = [
        ("multiple_choice", "MCQ"),
        ("short_answer", "Short Answer"),
        ("essay", "Essay"),
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
                        Span("Manually add a reusable question.", cls="text-muted small mt-1 d-block"),
                    ),
                    HtmlButton("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start px-4 pt-4",
                ),
                Form(
                    Div(
                        Div(
                            Label("Question Text", cls="form-label small fw-semibold text-secondary"),
                            Textarea(
                                name="question_text",
                                rows=3,
                                placeholder="Enter the question...",
                                required=True,
                                cls="form-control rounded-3",
                            ),
                            cls="mb-3",
                        ),
                        Row(
                            Col(
                                Label("Subject", cls="form-label small fw-semibold text-secondary"),
                                Select("subject", *subjects, value="Mathematics", cls="form-select rounded-3"),
                                md=6,
                            ),
                            Col(
                                Label("Grade", cls="form-label small fw-semibold text-secondary"),
                                Select("grade_level", *grades, value="JSS1", cls="form-select rounded-3"),
                                md=6,
                            ),
                            cls="mb-3 g-3",
                        ),
                        Row(
                            Col(
                                Label("Type", cls="form-label small fw-semibold text-secondary"),
                                Select("question_type", *types, value="multiple_choice", cls="form-select rounded-3"),
                                md=6,
                            ),
                            Col(
                                Label("Difficulty", cls="form-label small fw-semibold text-secondary"),
                                Select("difficulty", *diffs, value="easy", cls="form-select rounded-3"),
                                md=6,
                            ),
                            cls="mb-3 g-3",
                        ),
                        Div(
                            Label("Topic", cls="form-label small fw-semibold text-secondary"),
                            Input("topic", placeholder="e.g. Quadratic Equations", cls="form-control rounded-3"),
                            cls="mb-3",
                        ),
                        # Dynamic options row for MCQ
                        Div(
                            Label("Options (one per line for MCQ)", cls="form-label small fw-semibold text-secondary"),
                            Textarea(
                                name="options",
                                rows=3,
                                placeholder="Option A\nOption B\nOption C\nOption D",
                                cls="form-control rounded-3 font-monospace",
                            ),
                            cls="mb-3",
                        ),
                        Row(
                            Col(
                                Label("Correct Answer", cls="form-label small fw-semibold text-secondary"),
                                Input("correct_answer", placeholder="e.g. A or full answer", cls="form-control rounded-3"),
                                md=6,
                            ),
                            Col(
                                Label("Marks", cls="form-label small fw-semibold text-secondary"),
                                Input("marks", type="number", value="1", min="1", max="100", cls="form-control rounded-3"),
                                md=6,
                            ),
                            cls="mb-3 g-3",
                        ),
                        Div(
                            Label("Explanation (optional)", cls="form-label small fw-semibold text-secondary"),
                            Textarea(name="explanation", rows=2, placeholder="Explanation or marking guide...", cls="form-control rounded-3"),
                            cls="mb-3",
                        ),
                        cls="modal-body py-2 px-4",
                    ),
                    Div(
                        HtmlButton("Cancel", type="button", cls="btn btn-light rounded-pill px-4 py-2 me-2", **{"data-bs-dismiss": "modal"}),
                        Button("Add Question", type="submit", variant="success", cls="btn-brand rounded-pill px-4 py-2"),
                        cls="modal-footer border-0 pt-2 pb-4 px-4 d-flex justify-content-end",
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
