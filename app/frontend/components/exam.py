"""Exam UI components + workflow rendering (FRONTEND_SPEC sec 3.1, sec 6.6)."""

from __future__ import annotations

from fasthtml.common import (
    A,
    Button as HtmlButton,
    Div,
    Form,
    H2,
    H4,
    Input,
    P,
    Span,
    Strong,
    Textarea,
    Label,
    NotStr,
)

from faststrap import Badge, Button, Card, Row, Col, Icon

from app.core.workflow import REFINABLE_STATES, SUBMITTABLE_STATES
from app.utils.exam_utils import format_mcq_option

def render_rich_text(text: str) -> Span:
    """Render text with math equation delimiters so KaTeX auto-renders it."""
    if not text:
        return Span("")
    return Span(text, cls="math-content")

_STATUS_BADGE = {
    "generation_requested": ("Generating", "info"),
    "draft": ("Draft", "info"),
    "teacher_review": ("Under review", "warning"),
    "refinement_requested": ("Refining", "warning"),
    "final_submitted_by_teacher": ("Submitted for approval", "secondary"),
    "approved": ("Approved", "success"),
}


def state_of(exam: dict) -> str:
    """Public state resolver (was ``_state_of``)."""
    if exam.get("status") == "failed":
        return "failed"
    return exam.get("workflow_state") or exam.get("status") or "draft"


# Backwards-compat alias for code that imported the private name.
_state_of = state_of


def StatusBadge(exam: dict):
    """Status badge matching the prototype design.

    Prototype uses Tailwind classes:
      - approved:   bg-emerald-100 text-emerald-800 border-emerald-200  + dot
      - review:     bg-purple-100 text-purple-800 border-purple-200     + dot
      - generating: bg-blue-100 text-blue-800 border-blue-200           + dot
      - draft:      bg-gray-100 text-gray-700 border-gray-200            + dot
      - failed:     bg-red-100 text-red-800 border-red-200              + dot
    """
    state = state_of(exam)
    label_map = {
        "approved": ("Approved", "badge-status-approved"),
        "failed": ("Failed", "badge-status-failed"),
        "teacher_review": ("Under Review", "badge-status-review"),
        "final_submitted_by_teacher": ("Under Review", "badge-status-review"),
        "refinement_requested": ("Refining", "badge-status-review"),
        "generation_requested": ("Generating", "badge-status-generating"),
    }
    label, cls = label_map.get(state, ("Draft", "badge-status-draft"))
    return Span(
        Span(cls="w-1.5 h-1.5 rounded-full bg-current opacity-70 d-inline-block me-1"),
        label,
        cls=f"badge-status {cls}",
    )


def action_buttons(exam: dict, user: dict) -> list:
    """Action buttons valid for this exam's state + role (sec 6.6)."""
    state = state_of(exam)
    role = user.get("role")
    account = user.get("account_type")
    is_admin = role == "school_admin" or account == "individual_teacher"
    is_teacher = role in {"teacher", "school_admin"}
    exam_id = str(exam.get("id") or "")
    buttons = []

    if state == "failed":
        return [
            Button(
                "Delete and start over",
                hx_delete=f"/ui/exams/{exam['id']}",
                hx_confirm="This permanently deletes the failed exam. Continue?",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                variant="danger",
                cls="btn-brand",
            ),
            Button(
                "Try again",
                as_="a",
                href="/app/exams/new",
                variant="primary",
                cls="btn-brand",
            ),
        ]

    # F23/F29: Refine needs the textarea (rendered in _refine_panel), the
    # button is a plain trigger with an indicator spinner for feedback.
    if is_admin and state in REFINABLE_STATES:
        buttons.append(
            Button(
                "Refine with AI",
                hx_post=f"/ui/exams/{exam['id']}/refine",
                hx_include="#refine-feedback",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                hx_indicator="#refine-spinner",
                **{
                    "hx-on::before-request": "this.innerHTML='<span class=\\'spinner-border spinner-border-sm me-2\\'></span>Regenerating…'; this.disabled=true;",
                    "hx-on::after-request": "this.innerHTML='Refine with AI'; this.disabled=false;",
                },
                variant="outline-secondary",
            )
        )

    # F14: backend accepts any teacher or school_admin regardless of
    # account_type.  Removed the over-restrictive ``account == school_staff``
    # check that was hiding the button from individual teachers.
    if is_teacher and state in SUBMITTABLE_STATES:
        buttons.append(
            Button(
                "Submit for approval",
                hx_post=f"/ui/exams/{exam['id']}/submit-final",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                hx_indicator=f"#submit-spinner-{exam['id']}",
                variant="primary",
            )
        )
        # F56: a "previously submitted" exam in teacher_review state is the
        # post-rejection bounce path — surface a clearer label.
        if state == "teacher_review" and exam.get("workflow_state") == "teacher_review" \
                and exam.get("status") == "under_review":
            # already covered by the same button; no extra UI needed
            pass

    if is_admin and state in SUBMITTABLE_STATES:
        buttons.append(
            Button(
                "Approve",
                hx_post=f"/ui/exams/{exam['id']}/approve",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                hx_confirm="Approved exams are locked for editing. Continue?",
                hx_indicator=f"#approve-spinner-{exam['id']}",
                variant="success",
                cls="btn-brand",
            )
        )
        # Audit: no reject action existed for exams. "Reject" sends the exam
        # back to teacher_review so the teacher can refine and resubmit.
        buttons.append(
            Button(
                "Reject",
                hx_post=f"/ui/exams/{exam['id']}/reject",
                hx_include="#refine-feedback",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                hx_confirm="Send this exam back to the teacher for changes?",
                variant="outline-danger",
            )
        )

    if is_admin and state not in {"draft", "generation_requested", "failed"}:
        buttons.append(
            Button(
                "Export PDF",
                hx_post=f"/ui/exams/{exam['id']}/export",
                hx_include="#export-answers",
                hx_target="#export-result",
                hx_swap="innerHTML",
                hx_indicator="#export-spinner",
                variant="outline-success",
            )
        )

    if is_teacher and exam.get("questions"):
        buttons.append(
            Button(
                "Save to Bank",
                type="button",
                cls="btn btn-sm btn-outline-primary rounded-pill",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#saveBankModal-{exam_id}"},
            )
        )

    if is_admin and state not in {"draft", "generation_requested", "failed"}:
        buttons.append(
            Button(
                "Past Exports",
                type="button",
                cls="btn btn-sm btn-outline-secondary rounded-pill",
                hx_get=f"/ui/exams/{exam_id}/exports-history",
                hx_target=f"#exports-history-container-{exam_id}",
                hx_swap="innerHTML",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#exportsHistoryModal-{exam_id}"},
            )
        )

    buttons.append(
        A(
            "Print",
            href=f"/app/exams/{exam_id}/print",
            target="_blank",
            cls="btn btn-sm btn-outline-dark rounded-pill no-print",
        )
    )

    # F05/F08/F19: DELETE goes via hx_delete, target is the page itself so the
    # 303 redirect to /app/exams replaces the whole detail page.
    buttons.append(
        Button(
            "Delete",
            hx_delete=f"/ui/exams/{exam_id}",
            hx_confirm="This permanently deletes the exam and all its questions.",
            hx_target="#exam-detail-view",
            hx_swap="outerHTML",
            hx_indicator=f"#delete-spinner-{exam_id}",
            variant="danger",
            size="sm",
        )
    )
    return buttons


def QuestionBlock(q: dict, number: int, show_answers: bool, can_edit: bool = False, exam_id: str = "", user: dict = None, section_title: str = ""):
    """Render a single question matching P06_exam_detail_questions_desktop.png.

    Collapsible card with number pill, type badge, section label, marks pill,
    collapse chevron, 2-column MCQ options grid with correct answer highlight,
    and Edit question button.
    """
    user = user or {}
    qid = str(q.get("id") or "")
    q_type_raw = str(q.get("type") or "mcq").lower()
    if "mcq" in q_type_raw or "choice" in q_type_raw:
        type_label = "Mcq"
    elif "short" in q_type_raw:
        type_label = "Short Answer"
    elif "essay" in q_type_raw:
        type_label = "Essay"
    elif "true" in q_type_raw:
        type_label = "True / False"
    else:
        type_label = q_type_raw.replace("_", " ").title()

    marks = q.get("marks", 1)
    marks_str = f"{marks} mark" if marks == 1 else f"{marks} marks"
    section_label = section_title or q.get("section_name") or f"Section {q.get('section_number', 'A')}"
    correct_ans = (q.get("correct_answer") or "").strip()

    # Question header row: Number pill, Type badge, Section, Marks, Chevron
    card_id = f"question-card-{number}"
    collapse_id = f"q-collapse-{number}"

    # Question text: Persistent and always readable!
    q_text_display = Div(
        render_rich_text(q.get("question_text", "")),
        cls="my-2 text-dark fw-medium fs-6 cursor-pointer",
        style="line-height:1.55; cursor:pointer;",
        **{
            "data-bs-toggle": "collapse",
            "data-bs-target": f"#{collapse_id}",
            "aria-expanded": "true",
            "aria-controls": collapse_id,
        },
    )

    # Body details: Collapsed/expanded when toggled
    body_parts = []

    options = q.get("options") or []
    if options:
        mcq_cols = []
        for idx, opt in enumerate(options):
            opt_str = format_mcq_option(opt, idx)
            # Check if this option is the correct answer (e.g. letter matches or full text matches)
            letter = chr(65 + idx)
            is_correct = False
            if correct_ans:
                if correct_ans.upper() == letter or correct_ans.upper().startswith(letter + ".") or opt_str.strip() == correct_ans:
                    is_correct = True
            
            box_cls = "mcq-option-box is-correct" if is_correct else "mcq-option-box"
            opt_content = [
                Span(render_rich_text(opt_str)),
            ]
            if is_correct:
                opt_content.append(Span("✔", cls="mcq-correct-icon"))

            mcq_cols.append(
                Col(
                    Div(*opt_content, cls=box_cls),
                    cls="col-12 col-md-6",
                )
            )
        body_parts.append(
            Div(Row(*mcq_cols, cls="g-2 mb-3"))
        )

    if q.get("sub_parts"):
        sub_items = []
        for sp in q["sub_parts"]:
            if isinstance(sp, dict):
                sub_items.append(
                    P(
                        Span(f"({sp.get('part', '?')}) ", cls="fw-semibold text-dark"),
                        render_rich_text(sp.get("question", "")),
                        Span(f" [{sp.get('marks', 0)} marks]", cls="text-muted ms-1"),
                        cls="mb-1 small",
                    )
                )
        body_parts.append(Div(*sub_items, cls="ms-3 mb-2"))

    if q.get("explanation") and show_answers:
        body_parts.append(
            Div(
                Strong("Explanation: ", cls="text-success small"),
                Span(render_rich_text(q["explanation"]), cls="small text-muted"),
                cls="p-2 bg-light rounded-3 mb-2",
            )
        )

    # Edit & Delete Action Buttons + Modals
    edit_modal = Div()
    delete_modal = Div()
    if can_edit and qid and exam_id:
        delete_modal_id = f"deleteQuestionModal-{exam_id}-{qid}"
        action_buttons = [
            Button(
                Icon("pencil", cls="bi me-1"),
                "Edit question",
                type="button",
                variant="light",
                size="sm",
                cls="rounded-pill px-3 py-1 text-muted border me-2",
                style="font-size:0.82rem; background:#f8fafc;",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#editQuestionModal-{exam_id}-{qid}"},
            ),
            Button(
                Icon("trash", cls="bi me-1 text-danger"),
                "Delete",
                type="button",
                variant="light",
                size="sm",
                cls="rounded-pill px-3 py-1 text-danger border",
                style="font-size:0.82rem; background:#fff1f2; border-color:#fecdd3 !important;",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#{delete_modal_id}"},
            ),
        ]
        body_parts.append(
            Div(*action_buttons, cls="mt-3 d-flex align-items-center"),
        )

        # Hand-crafted delete modal — NOT using ConfirmDialog because faststrap's ConfirmDialog
        # puts data-bs-dismiss on the confirm button, which causes Bootstrap to destroy the DOM
        # element before HTMX can fire the DELETE request. Instead we close the modal via
        # hx-on::before-request (fires inside HTMX's pipeline, before the request is sent).
        delete_modal = Div(
            Div(
                Div(
                    Div(
                        Strong(f"Delete Question {number}", cls="fs-5 fw-bold text-dark d-block"),
                        Span(
                            f"Are you sure you want to delete Question {number}? "
                            "Remaining questions will be automatically renumbered and total marks recalculated.",
                            cls="text-muted small mt-1 d-block",
                        ),
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
                            "hx-delete": f"/ui/exams/{exam_id}/questions/{qid}",
                            "hx-target": "#tab-content",
                            "hx-swap": "innerHTML",
                            # Close the modal BEFORE HTMX fires — avoids data-bs-dismiss destroying
                            # the element before the request is sent.
                            "hx-on::before-request": (
                                f"var m=bootstrap.Modal.getInstance(document.getElementById('{delete_modal_id}'));"
                                "if(m)m.hide();"
                            ),
                        },
                    ),
                    cls="modal-footer border-0 pt-3 pb-4 px-4 d-flex justify-content-end",
                ),
                cls="modal-content border-0 shadow-lg rounded-4 p-2",
            ),
            cls="modal-dialog modal-dialog-centered",
        )
        delete_modal = Div(delete_modal, cls="modal fade", id=delete_modal_id, tabindex="-1", **{"aria-hidden": "true"})

        edit_modal = Div(
            Div(
                Div(
                    Div(
                        Div(
                            Strong(f"Edit Question {number}", cls="fs-5 fw-bold text-dark d-block"),
                            Span("Update question details. Total exam marks will recalculate automatically.", cls="text-muted small"),
                        ),
                        HtmlButton("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                        cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                    ),
                    Form(
                        Div(
                            Div(
                                Label("Question text", cls="form-label small fw-semibold"),
                                Textarea(
                                    q.get("question_text", ""),
                                    name="question_text",
                                    cls="form-control rounded-3",
                                    rows=3,
                                    required=True,
                                ),
                                cls="mb-3",
                            ),
                            Div(
                                Label("Options (one per line for MCQ)", cls="form-label small fw-semibold"),
                                Textarea(
                                    "\n".join(options or []),
                                    name="options",
                                    cls="form-control rounded-3 font-monospace",
                                    rows=max(2, len(options or [])),
                                ),
                                cls="mb-3",
                            ),
                            Div(
                                Row(
                                    Col(
                                        Label("Correct answer (e.g. A or full answer)", cls="form-label small fw-semibold"),
                                        Input("correct_answer", value=q.get("correct_answer", ""), cls="form-control rounded-3"),
                                        md=6,
                                    ),
                                    Col(
                                        Label("Marks", cls="form-label small fw-semibold"),
                                        Input("marks", type="number", value=q.get("marks", 1), min=1, max=100, cls="form-control rounded-3"),
                                        md=6,
                                    ),
                                    cls="g-3",
                                ),
                                cls="mb-3",
                            ),
                            Div(
                                Label("Explanation", cls="form-label small fw-semibold"),
                                Textarea(
                                    q.get("explanation", ""),
                                    name="explanation",
                                    cls="form-control rounded-3",
                                    rows=2,
                                ),
                                cls="mb-3",
                            ),
                            Input("_workflow_state", type="hidden", value=user.get("workflow_state", "")),
                            Input("_status", type="hidden", value=user.get("status", "")),
                            Div(id=f"edit-result-{qid}", cls="mb-2"),
                            cls="modal-body py-2 px-4",
                        ),
                        Div(
                            Button("Cancel", type="button", variant="light", cls="rounded-pill px-3 me-2", **{"data-bs-dismiss": "modal"}),
                            Button("Save changes", type="submit", variant="success", cls="btn-brand rounded-pill px-4"),
                            cls="modal-footer border-0 pt-2 pb-4 px-4",
                        ),
                        hx_post=f"/ui/exams/{exam_id}/questions/{qid}/edit",
                        hx_target=f"#edit-result-{qid}",
                        hx_swap="innerHTML",
                    ),
                    cls="modal-content border-0 shadow-lg rounded-4",
                ),
                cls="modal-dialog modal-dialog-centered",
            ),
            cls="modal fade",
            id=f"editQuestionModal-{exam_id}-{qid}",
            tabindex="-1",
            **{"aria-hidden": "true"},
        )

    # Question Card Container
    header_toggle = Div(
        Div(
            Span(str(number), cls="app-q-num-pill me-2"),
            Span(type_label, cls="app-q-type-badge me-2"),
            Span(section_label, cls="app-q-section-label"),
            cls="d-flex align-items-center flex-wrap gap-1",
        ),
        Div(
            Span(marks_str, cls="app-q-marks-pill me-2"),
            Icon("chevron-down", cls="bi text-muted collapse-chevron", style="transition:transform 0.2s ease; font-size:0.85rem;"),
            cls="d-flex align-items-center",
        ),
        cls="d-flex justify-content-between align-items-center cursor-pointer",
        style="cursor:pointer; user-select:none;",
        **{
            "data-bs-toggle": "collapse",
            "data-bs-target": f"#{collapse_id}",
            "aria-expanded": "true",
            "aria-controls": collapse_id,
        },
    )

    card = Div(
        header_toggle,
        q_text_display,
        Div(
            Div(*body_parts, cls="pt-3 border-top mt-2"),
            id=collapse_id,
            cls="collapse show",
        ),
        id=card_id,
        cls="app-question-card mb-3",
    )

    elements = [card]
    if edit_modal:
        elements.append(edit_modal)
    if delete_modal:
        elements.append(delete_modal)
    return Div(*elements)


def PassageBlock(p: dict):
    """Render a comprehension passage once (sec 6.6)."""
    parts = []
    if p.get("title"):
        parts.append(H2(p.get("title"), cls="h5 mb-2"))
    parts.append(P(p.get("body", ""), cls="mb-0"))
    return Div(
        P("Read the passage and answer the questions that follow.", cls="text-muted small mb-2"),
        *parts,
        cls="p-3 mb-3 border-start border-4 border-success bg-light rounded-2",
    )


def SectionHeader(title: str, count: int = 0, total_marks: int = 0):
    """Clean Nigerian exam section header dividing objectives, theory, essay."""
    meta = f"{count} question" if count == 1 else f"{count} questions"
    if total_marks:
        meta += f" · {total_marks} marks"
    return Div(
        Div(
            H4(title, cls="fs-6 fw-bold text-dark mb-0"),
            Span(meta, cls="badge bg-light text-secondary border fw-medium px-2 py-1 rounded-pill", style="font-size:0.75rem;"),
            cls="d-flex justify-content-between align-items-center",
        ),
        cls="app-exam-section-header bg-white border rounded-3 p-3 mb-3 shadow-xs mt-4",
    )


def render_questions(exam: dict, show_answers: bool = False, can_edit: bool = False, user: dict = None):
    """Render questions with Nigerian section headers (Objectives, Theory, Essay)."""
    from fasthtml.common import Div as _Div

    questions = exam.get("questions") or []
    passages = exam.get("passages") or []
    passage_by_id = {str(p.get("id")): p for p in passages if p.get("id")}
    exam_id = str(exam.get("id") or "")
    user = user or {}

    def get_section_info(q):
        sec_name = q.get("section_name")
        sec_num = q.get("section_number") or 1
        q_type = (q.get("question_type") or "").lower()
        if sec_name:
            return sec_num, sec_name
        if sec_num == 1 or "choice" in q_type or "mcq" in q_type:
            return 1, "Section A (Objectives)"
        elif sec_num == 2 or "short" in q_type:
            return 2, "Section B (Theory)"
        elif sec_num == 3 or "essay" in q_type:
            return 3, "Section C (Essay)"
        return sec_num, f"Section {sec_num}"

    # Pre-calculate section question counts and marks
    sec_counts: dict[str, int] = {}
    sec_marks: dict[str, int] = {}
    for q in questions:
        _, s_title = get_section_info(q)
        sec_counts[s_title] = sec_counts.get(s_title, 0) + 1
        sec_marks[s_title] = sec_marks.get(s_title, 0) + (q.get("marks") or 1)

    out = []
    seen_passages: set = set()
    current_section = None

    for idx, q in enumerate(questions, start=1):
        _, s_title = get_section_info(q)
        if s_title != current_section:
            current_section = s_title
            out.append(SectionHeader(s_title, sec_counts.get(s_title, 0), sec_marks.get(s_title, 0)))

        pid = q.get("passage_id")
        if pid and str(pid) in passage_by_id and pid not in seen_passages:
            out.append(PassageBlock(passage_by_id[str(pid)]))
            seen_passages.add(pid)

        out.append(QuestionBlock(q, idx, show_answers, can_edit=can_edit, exam_id=exam_id, user=user))

    return _Div(*out)


def exam_header(exam: dict):
    return Card(
        Div(
            Div(
                Strong(exam.get("subject", "")),
                P(
                    f"{exam.get('grade_level', '')} - {exam.get('total_marks', 0)} marks"
                    + (f" - {exam.get('duration_minutes')} min" if exam.get("duration_minutes") else "")
                    + f" - {exam.get('language', 'English')}",
                    cls="mb-0 text-muted small",
                ),
                cls="d-flex flex-column",
            ),
            Div(StatusBadge(exam)),
            cls="d-flex justify-content-between align-items-start",
        ),
        cls="p-3 mb-3",
    )
