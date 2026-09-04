"""Exam UI components + workflow rendering (FRONTEND_SPEC sec 3.1, sec 6.6)."""

from __future__ import annotations

from fasthtml.common import Div, P, Strong, H2, Span

from faststrap import Badge, Button, Card

from app.core.workflow import REFINABLE_STATES, SUBMITTABLE_STATES

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
    state = state_of(exam)
    if state == "failed":
        return Span("Failed", cls="badge-status badge-status-failed")
    if state == "approved":
        return Span("Approved", cls="badge-status badge-status-approved")
    if state in {"teacher_review", "final_submitted_by_teacher", "refinement_requested"}:
        return Span("Under Review", cls="badge-status badge-status-review")
    if state == "generation_requested":
        return Span("Generating", cls="badge-status badge-status-generating")
    return Span("Draft", cls="badge-status badge-status-draft")


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
                "Try again",
                as_="a",
                href="/app/exams/new",
                variant="primary",
                cls="btn-brand",
            )
        ]

    # F23/F29: Refine needs the textarea (rendered in _refine_panel), the
    # button is a plain trigger with an indicator spinner for feedback.
    if is_admin and state in REFINABLE_STATES:
        buttons.append(
            Button(
                "Refine with AI",
                hx_post=f"/ui/exams/{exam['id']}/refine",
                hx_include="#refine-feedback",
                hx_target="#exam-actions",
                hx_swap="outerHTML",
                hx_indicator="#refine-spinner",
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
        Button(
            "Print",
            type="button",
            cls="btn btn-sm btn-outline-dark rounded-pill no-print",
            onclick="window.print()",
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


def QuestionBlock(q: dict, number: int, show_answers: bool):
    """Render a single question (sec 6.6). FastHTML auto-escapes text."""
    parts = [Div(Strong(f"Q{number}. "), q.get("question_text", ""), cls="mb-1")]
    options = q.get("options") or []
    if options:
        # F26: render MC options as a proper ordered list.
        parts.append(
            Div(
                *[
                    P(opt, cls="mb-0 small text-muted")
                    for opt in options
                ],
                cls="ms-4 mb-1",
            )
        )
    if q.get("sub_parts"):
        parts.append(
            Div(
                *[
                    P(
                        f"({sp.get('part', '?')}) {sp.get('question', '')} "
                        f"[{sp.get('marks', 0)} marks]",
                        cls="mb-0 small",
                    )
                    for sp in q["sub_parts"]
                    if isinstance(sp, dict)
                ],
                cls="ms-4 mb-1 text-muted",
            )
        )
    line = f"[{q.get('marks', 0)} marks]"
    if q.get("difficulty"):
        line += f" - {q['difficulty']}"
    parts.append(P(line, cls="mb-0 small text-muted"))

    if show_answers:
        ans = []
        if q.get("correct_answer"):
            ans.append(f"Answer: {q['correct_answer']}")
        if q.get("explanation"):
            ans.append(q["explanation"])
        if ans:
            parts.append(P(" - ".join(ans), cls="mb-0 small text-success"))

    return Div(*parts, cls="mb-3 pb-2 border-bottom")


def PassageBlock(p: dict):
    """Render a comprehension passage once (sec 6.6)."""
    parts = []
    if p.get("title"):
        # F27: passage title as a heading for screen readers.
        parts.append(H2(p.get("title"), cls="h5 mb-2"))
    parts.append(P(p.get("body", ""), cls="mb-0"))
    return Div(
        P("Read the passage and answer the questions that follow.", cls="text-muted small mb-2"),
        *parts,
        cls="p-3 mb-3 border-start border-4 border-success",
    )


def render_questions(exam: dict, show_answers: bool = False):
    """Render questions grouped by passage (F17 dedupes PassageBlock).

    The API returns a flat question list + a passages list; questions link a
    passage via ``passage_id``. Comprehension questions render beneath their
    passage; all others in sequence.  F32: drop per-question Card chrome.
    """
    from fasthtml.common import Div as _Div

    questions = exam.get("questions") or []
    passages = exam.get("passages") or []
    passage_by_id = {str(p.get("id")): p for p in passages if p.get("id")}

    rendered = []
    standalone = []
    for idx, q in enumerate(questions, start=1):
        pid = q.get("passage_id")
        if pid and str(pid) in passage_by_id:
            rendered.append((passage_by_id[str(pid)], q, idx))
        else:
            standalone.append((None, q, idx))

    out = []
    # F17: render each unique passage once even if multiple questions share it.
    seen_passages: set = set()
    for p, q, n in rendered:
        if p.get("id") not in seen_passages:
            out.append(PassageBlock(p))
            seen_passages.add(p.get("id"))
        out.append(QuestionBlock(q, n, show_answers))
    out += [QuestionBlock(q, n, show_answers) for _, q, n in standalone]
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
