"""Teacher-facing curriculum delivery workspace (Package B)."""

import asyncio
import logging
import re
from uuid import UUID
from urllib.parse import urlencode

from fasthtml.common import (
    H1,
    H2,
    A,
    Details,
    Div,
    Form,
    Input,
    Label,
    Li,
    P,
    Script,
    Span,
    Strong,
    Summary,
    Textarea,
    Title,
    Ul,
)
from faststrap import Alert, Button, Card, Col, Container, Icon, Row, Select
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login
from app.frontend.curriculum_context import workspace_curriculum_board

logger = logging.getLogger(__name__)
TEACHING_API_TIMEOUT_SECONDS = 5


async def _fetch_data(req: Request, path: str, *, params: dict | None = None, source: str):
    """Fetch one teaching data source without letting it take down the page."""
    try:
        response = await asyncio.wait_for(
            call_api(req, "GET", path, params=params),
            timeout=TEACHING_API_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        # A failed refresh is a redirect signal from call_api, not a partial-data
        # failure. Preserve it so expired sessions still return to sign-in.
        from starlette.exceptions import HTTPException

        if isinstance(exc, HTTPException):
            raise
        category = "timeout" if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) else "error"
        logger.warning("teaching_workspace_fetch_failed source=%s category=%s", source, category)
        if category == "error":
            logger.exception("teaching_workspace_fetch_exception source=%s", source)
        return None, source

    ok, data = unwrap(response)
    if not ok:
        logger.warning(
            "teaching_workspace_fetch_failed source=%s category=http status=%s",
            source,
            response.status_code,
        )
        return None, source
    return data, None


def _terms() -> list[tuple[str, str]]:
    return [("First Term", "First Term"), ("Second Term", "Second Term"), ("Third Term", "Third Term")]


async def _scope(req: Request, class_level: str, subject: str, term: str, board: str = "NERDC"):
    warnings = []
    classes_data, failed_source = await _fetch_data(
        req, "/curriculum/classes", params={"board": board}, source="curriculum classes"
    )
    if failed_source:
        warnings.append(failed_source)
    classes = classes_data.get("classes", []) if isinstance(classes_data, dict) else []
    if not classes:
        classes = [class_level] if board.casefold() == "nerdc" and class_level else []
    if class_level not in classes:
        class_level = classes[0] if classes else ""

    subjects_data, failed_source = await _fetch_data(
        req,
        "/curriculum/subjects",
        params={"class_level": class_level, "board": board},
        source="curriculum subjects",
    )
    if failed_source:
        warnings.append(failed_source)
    subjects = subjects_data.get("subjects", []) if isinstance(subjects_data, dict) else []
    if not subject and subjects:
        subject = subjects[0].get("subject_name", "")
    if subjects and subject not in {item.get("subject_name") for item in subjects}:
        subject = subjects[0].get("subject_name", "")
    if not subjects and board.casefold() != "nerdc":
        subject = ""

    if not class_level or not subject:
        return classes, subjects, [], class_level, subject, warnings

    weeks_data, weeks_warning = await _fetch_data(
        req,
        "/curriculum/school/weeks",
        params={"class_level": class_level, "subject": subject, "term": term, "board": board},
        source="curriculum weeks",
    )
    weeks = weeks_data.get("weeks", []) if isinstance(weeks_data, dict) else []
    if weeks_warning:
        fallback_data, fallback_warning = await _fetch_data(
            req,
            "/curriculum/weeks",
            params={"class_level": class_level, "subject": subject, "term": term, "board": board},
            source="curriculum weeks fallback",
        )
        weeks = fallback_data.get("weeks", []) if isinstance(fallback_data, dict) else []
        if fallback_warning:
            warnings.append("curriculum weeks")
    return classes, subjects, weeks, class_level, subject, warnings


def _status_badge(status: str) -> Span:
    tone = {"approved": "success", "submitted": "primary", "returned": "danger"}.get(status, "warning")
    return Span(status.replace("_", " ").title(), cls=f"badge rounded-pill bg-{tone}-subtle text-{tone} border border-{tone}-subtle px-3 py-2")


def _plan_card(plan: dict, user: dict) -> Card:
    plan_id = plan.get("id", "")
    raw_ai_note = (plan.get("ai_lesson_note") or "").strip()
    # Treat empty or corrupted placeholder like "[1]" as empty
    ai_note = raw_ai_note if raw_ai_note and raw_ai_note != "[1]" else ""
    
    refinement_chips = Div(
        Span("Quick refinements:", cls="small fw-semibold text-muted d-block mb-1"),
        Div(
            Form(
                Input(type="hidden", name="lesson_plan_id", value=plan_id),
                Input(type="hidden", name="guidance", value="Include relatable Nigerian examples, local market contexts, and cultural applications familiar to primary pupils."),
                Button(Icon("geo-alt-fill", cls="bi me-1 text-success"), "+ Nigerian Context", type="submit", variant="outline-success", aria_label="Refine this lesson note with Nigerian context", cls="btn btn-sm rounded-pill teaching-refinement me-1 mb-1"),
                action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline",
            ),
            Form(
                Input(type="hidden", name="lesson_plan_id", value=plan_id),
                Input(type="hidden", name="guidance", value="Make the lesson note concise, bulleted, and easy to deliver within a single 40-minute classroom period."),
                Button(Icon("scissors", cls="bi me-1 text-success"), "Make Shorter", type="submit", variant="outline-success", aria_label="Refine this lesson note to be shorter", cls="btn btn-sm rounded-pill teaching-refinement me-1 mb-1"),
                action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline",
            ),
            Form(
                Input(type="hidden", name="lesson_plan_id", value=plan_id),
                Input(type="hidden", name="guidance", value="Simplify vocabulary and explanations so slower learners and early ESL readers can follow easily."),
                Button(Icon("lightbulb", cls="bi me-1 text-success"), "Simplify Language", type="submit", variant="outline-success", aria_label="Refine this lesson note with simpler language", cls="btn btn-sm rounded-pill teaching-refinement me-1 mb-1"),
                action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline",
            ),
            Form(
                Input(type="hidden", name="lesson_plan_id", value=plan_id),
                Input(type="hidden", name="guidance", value="Add a step-by-step practical demonstration using everyday classroom items (chalk, cup, ruler, seeds)."),
                Button(Icon("tools", cls="bi me-1 text-success"), "Add Activity", type="submit", variant="outline-success", aria_label="Refine this lesson note by adding a practical activity", cls="btn btn-sm rounded-pill teaching-refinement me-1 mb-1"),
                action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline",
            ),
            cls="d-flex flex-wrap align-items-center mb-2",
        ),
        cls="mb-2 d-none d-lg-block",
    ) if ai_note else None

    return Card(
        Div(
            Div(
                Div(Span(f"Week {plan.get('week_number', '-')}", cls="small text-success fw-bold"), _status_badge(plan.get("status", "draft")), cls="d-flex align-items-center flex-wrap gap-2"),
                Strong(plan.get("title") or "Untitled lesson plan", cls="d-block fs-5 text-dark mt-2 text-break"),
                P(f"{plan.get('term', '')}", cls="small text-muted mb-0 mt-1"),
                cls="mb-2",
            ),
            P(" · ".join((plan.get("learning_objectives") or [])[:2]) or "Add learning objectives from the curriculum week.", cls="small text-muted mt-3 mb-3"),
            Div(
                Strong("Draft lesson note", cls="small text-success d-block mb-1"),
                refinement_chips,
                Details(
                    Summary(Icon("sliders", cls="bi me-2"), "Quick refinements", cls="small fw-semibold text-success py-2"),
                    Div(
                        Form(Input(type="hidden", name="lesson_plan_id", value=plan_id), Input(type="hidden", name="guidance", value="Include relatable Nigerian examples, local market contexts, and cultural applications familiar to primary pupils."), Button(Icon("geo-alt-fill", cls="bi me-1"), "Nigerian context", type="submit", variant="outline-success", size="sm", cls="rounded-pill"), action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline-block me-2 mb-2"),
                        Form(Input(type="hidden", name="lesson_plan_id", value=plan_id), Input(type="hidden", name="guidance", value="Make the lesson note concise, bulleted, and easy to deliver within a single 40-minute classroom period."), Button(Icon("scissors", cls="bi me-1"), "Make shorter", type="submit", variant="outline-success", size="sm", cls="rounded-pill"), action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline-block me-2 mb-2"),
                        Form(Input(type="hidden", name="lesson_plan_id", value=plan_id), Input(type="hidden", name="guidance", value="Simplify vocabulary and explanations so slower learners and early ESL readers can follow easily."), Button(Icon("lightbulb", cls="bi me-1"), "Simplify language", type="submit", variant="outline-success", size="sm", cls="rounded-pill"), action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline-block me-2 mb-2"),
                        Form(Input(type="hidden", name="lesson_plan_id", value=plan_id), Input(type="hidden", name="guidance", value="Add a step-by-step practical demonstration using everyday classroom items (chalk, cup, ruler, seeds)."), Button(Icon("tools", cls="bi me-1"), "Add activity", type="submit", variant="outline-success", size="sm", cls="rounded-pill"), action=f"/app/teaching/{plan_id}/lesson-note", method="post", cls="d-inline-block mb-2"),
                        cls="pt-2",
                    ),
                    cls="mb-2 d-lg-none",
                ) if ai_note else None,
                Form(
                    Label("Lesson note draft", for_=f"lesson-note-{plan_id}", cls="small fw-semibold text-muted mb-1"),
                    Textarea(ai_note or "", id=f"lesson-note-{plan_id}", name="ai_lesson_note", rows="6", aria_describedby=f"lesson-note-help-{plan_id}", data_note_editor="true", cls="form-control form-control-sm border-0 rounded-3", style="background:#F1F8F2; font-size: 0.9rem; line-height: 1.5;"),
                    P("Your edits are saved when you choose Save & submit. Refinements replace the draft, so you will be asked before unsaved changes are discarded.", id=f"lesson-note-help-{plan_id}", cls="form-text small text-muted"),
                    Details(
                        Summary("Preview lesson note", cls="small fw-semibold text-success py-2"),
                        Div(P("Open this preview to see the formatted lesson note.", cls="small text-muted mb-0"), data_note_preview=f"lesson-note-{plan_id}", cls="lesson-note-preview border rounded-3 bg-white p-3 mt-2"),
                        cls="mb-2",
                    ),
                    Input(type="hidden", name="status", value="submitted"),
                    Div(
                        Button(Icon("check-lg", cls="bi me-1"), Span("Save & submit for review", cls="d-none d-sm-inline"), Span("Submit", cls="d-inline d-sm-none"), type="submit", variant="success", size="sm", aria_label="Save and submit lesson note for review", cls="rounded-pill"),
                        cls="d-inline-block mt-2 me-2",
                    ),
                    action=f"/app/teaching/{plan_id}/save-note",
                    method="post",
                    cls="d-inline",
                ),
                A(
                    Icon("file-earmark-pdf", cls="bi me-1"),
                    Span("Print / download PDF", cls="d-none d-sm-inline"),
                    href=f"/app/teaching/{plan_id}/lesson-note/export.pdf",
                    aria_label="Print or download lesson note PDF",
                    title="Print or download PDF",
                    cls="btn btn-sm btn-outline-success rounded-pill mt-2 me-2",
                ),
                A(
                    Icon("file-earmark-word", cls="bi me-1"),
                    Span("Download Word", cls="d-none d-sm-inline"),
                    href=f"/app/teaching/{plan_id}/lesson-note/export.docx",
                    aria_label="Download lesson note Word document",
                    title="Download Word document",
                    cls="btn btn-sm btn-outline-success rounded-pill mt-2 me-2",
                ),
                Form(
                    Button(Icon("patch-check", cls="bi me-1"), "Confirm for school", type="submit", variant="outline-primary", size="sm", cls="rounded-pill mt-2"),
                    action=f"/app/teaching/{plan_id}/approve",
                    method="post",
                    cls="d-inline-block",
                ) if user.get("role") == "school_admin" and plan.get("status") == "submitted" else None,
                cls="rounded-3 p-3 mb-3",
                style="background:#F1F8F2;",
            ) if ai_note else None,
            Div(
                Form(
                    Input(type="hidden", name="lesson_plan_id", value=plan_id),
                    Button(Icon("sparkles", cls="bi me-1"), "Draft with AI" if not ai_note else "Regenerate draft", type="submit", variant="outline-success", size="sm", cls="rounded-pill teaching-refinement"),
                    action=f"/app/teaching/{plan_id}/lesson-note",
                    method="post",
                    cls="d-inline",
                ),
                Form(
                    Input(type="hidden", name="lesson_plan_id", value=plan_id),
                    Button(Icon("check2-circle", cls="bi me-1"), "Start coverage tracking", type="submit", variant="outline-success", size="sm", cls="rounded-pill"),
                    action=f"/app/teaching/{plan_id}/coverage",
                    method="post",
                    cls="d-inline ms-2",
                ),
            ),
            cls="p-3",
        ),
        cls="border rounded-4 shadow-sm bg-white h-100",
    )


def _exercise_card(exercise: dict) -> Card:
    questions = exercise.get("questions") or []
    total_marks = 0
    for item in questions:
        if isinstance(item, dict):
            try:
                total_marks += max(0, int(item.get("marks", 1) or 1))
            except (TypeError, ValueError):
                continue
    answer_key_items = [
        Li(f"{index}. {question.get('question_text', '')} — {question.get('answer_key')}", cls="mb-1")
        for index, question in enumerate(questions, start=1)
        if isinstance(question, dict) and question.get("answer_key")
    ]
    return Card(
        Div(
            Strong(exercise.get("title") or "Weekly exercise", cls="d-block text-dark"),
            Span(f"{len(questions)} questions · {total_marks} marks", cls="small text-muted d-block mb-2"),
            P(exercise.get("instructions") or "No instructions added.", cls="small text-muted mb-3"),
            Details(Summary("Staff marking guide", cls="small fw-semibold text-success"), Ul(*answer_key_items, cls="small text-muted mt-2 ps-4 mb-0"), cls="mb-3") if answer_key_items else None,
            A(Icon("download", cls="bi me-1"), "Export worksheet", href=f"/app/teaching/exercises/{exercise.get('id')}/export", cls="btn btn-sm btn-outline-success rounded-pill"),
            cls="p-3",
        ),
        cls="border rounded-4 shadow-sm bg-white h-100",
    )


def _worksheet_form(subject: str, term: str, plans: list[dict]) -> Form:
    """Compact worksheet builder; teachers can add question rows as needed."""
    active_plan = plans[0] if plans else {}
    question = Div(
        Strong("Question 1", cls="small text-success d-block mb-2", data_question_heading="true"),
        Label("Question type", for_="exercise-type-1", cls="form-label small fw-semibold text-muted mb-1"),
        Select("question_type_1", ("short_answer", "Short answer", True), ("mcq", "Multiple choice"), id="exercise-type-1", cls="form-select form-select-sm mb-2"),
        Label("Question", for_="exercise-question-1", cls="form-label small fw-semibold text-muted mb-1"),
        Textarea(name="question_text_1", id="exercise-question-1", rows="2", maxlength="3000", aria_describedby="exercise-question-help-1", placeholder="Write one clear question", cls="form-control mb-2"),
        P("For multiple choice, enter 2–10 options, one per line. Leave blank if you do not need this question.", id="exercise-question-help-1", cls="form-text small text-muted mb-2"),
        Label("Answer options (multiple choice only; one per line)", for_="exercise-options-1", cls="form-label small fw-semibold text-muted mb-1"),
        Textarea(name="answer_options_1", id="exercise-options-1", rows="2", placeholder="Option A\nOption B", cls="form-control form-control-sm mb-2"),
        Label("Marks", for_="exercise-marks-1", cls="form-label small fw-semibold text-muted mb-1"),
        Input(type="number", name="question_marks_1", id="exercise-marks-1", value="1", min="1", max="100", cls="form-control form-control-sm mb-2"),
        Label("Answer key / expected answer (staff only)", for_="exercise-key-1", cls="form-label small fw-semibold text-muted mb-1"),
        Textarea(name="answer_key_1", id="exercise-key-1", rows="2", maxlength="3000", placeholder="Optional; not printed on the learner worksheet", cls="form-control form-control-sm"),
        Button(Icon("trash3", cls="bi me-1"), "Remove question", type="button", variant="outline-danger", disabled=True, cls="btn-sm rounded-pill mt-3 remove-worksheet-question"),
        cls="border rounded-3 p-3 mb-3 bg-light",
        data_worksheet_question="true", data_question_index="1", role="group", aria_label="Worksheet question 1",
    )
    options = [(str(plan.get("id", "")), f"Week {plan.get('week_number', '—')} · {plan.get('title') or 'Untitled lesson plan'}", index == 0) for index, plan in enumerate(plans)]
    return Form(
        Div(Label("Lesson plan", for_="lesson-plan-id", cls="small fw-semibold text-muted mb-1"), Select("lesson_plan_id", *options, required=True, id="lesson-plan-id", cls="form-select border-0 rounded-3", style="background:#F1F4F1;"), cls="col-12"),
        Div(Label("Exercise title", for_="exercise-title", cls="small fw-semibold text-muted mb-1"), Input(name="title", id="exercise-title", required=True, value=f"{subject} · {term} practice", cls="form-control border-0 rounded-3", style="background:#F1F4F1;"), cls="col-12"),
        Div(Label("Instructions for learners", for_="exercise-instructions", cls="small fw-semibold text-muted mb-1"), Textarea(name="instructions", id="exercise-instructions", rows="2", placeholder="e.g. Answer all questions clearly in your exercise books. Marks are indicated against each question.", cls="form-control border-0 rounded-3", style="background:#F1F4F1; font-size: 0.88rem;"), cls="col-12"),
        Div(Label("Questions and marking guide", cls="small fw-semibold text-muted mb-1"), P("Start with one question, then add more only when you need them. Marks and answer keys are saved; answer keys are not printed for learners. Multiple-choice questions need at least two options.", cls="form-text small text-muted"), Div(question, id="worksheet-question-list"), Button(Icon("plus-lg", cls="bi me-1"), "Add question", type="button", variant="outline-success", id="add-worksheet-question", cls="rounded-pill mb-3"), cls="col-12"),
        Div(Button(Icon("file-earmark-plus", cls="bi me-1"), "Create worksheet", type="submit", variant="success", cls="rounded-pill px-4 btn-brand", disabled=not bool(active_plan)), cls="col-12"),
        action="/app/teaching/exercises/create", method="post", cls="row g-3",
    )


def _coverage_card(row: dict, user: dict) -> Card:
    status = row.get("status", "planned")
    status_config = {
        "planned": ("Not started", "secondary", "in_progress", "Start teaching", "play-fill"),
        "in_progress": ("Teaching now", "primary", "completed", "Mark as taught", "check2-circle"),
        "completed": ("Taught", "success", "verified", "Confirm for school", "patch-check-fill"),
        "verified": ("Confirmed by Admin", "dark", None, None, None),
    }
    badge_label, tone, next_status, btn_label, btn_icon = status_config.get(
        status, (status.replace("_", " ").title(), "secondary", None, None, None)
    )
    action = None
    if next_status and (next_status != "verified" or user.get("role") == "school_admin"):
        action = Form(
            Input(type="hidden", name="status", value=next_status),
            Button(Icon(btn_icon, cls="bi me-1") if btn_icon else None, btn_label, type="submit", variant=f"outline-{tone}", size="sm", cls="rounded-pill mt-2"),
            action=f"/app/teaching/coverage/{row.get('id')}",
            method="post",
        )
    elif status == "verified":
        action = Span(Icon("check2-all", cls="bi me-1 text-success"), "Official school record", cls="small text-muted d-block mt-2")
    elif status == "completed":
        action = Span(Icon("hourglass-split", cls="bi me-1 text-muted"), "Marked taught · awaiting admin confirmation", cls="small text-muted d-block mt-2")

    return Card(
        Div(
            Strong(f"{row.get('class_level') or 'Class'} / {row.get('subject') or 'Subject'}", cls="d-block text-dark"),
            Span(f"{row.get('term') or ''} / Week {row.get('week_number') or '-'}", cls="small text-muted d-block mt-1"),
            P(row.get("topic") or "Curriculum week", cls="small fw-semibold text-dark mb-2 mt-2"),
            Span(badge_label, cls=f"badge rounded-pill bg-{tone}-subtle text-{tone} border border-{tone}-subtle px-3 py-1 fw-semibold"),
            P("Shared school record. Staff mark a week taught; an administrator confirms it.", cls="small text-muted mb-1 mt-2"),
            action,
            cls="p-3",
        ),
        cls="border rounded-4 shadow-sm bg-white h-100",
    )


def teaching_routes(app):
    @app.get("/app/teaching")
    async def teaching_workspace(
        req: Request,
        class_level: str = "Primary 4",
        subject: str = "",
        term: str = "First Term",
        scheme_id: str = "",
        mode: str = "",
        output: str = "",
        show_coverage: bool = False,
    ):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        board = await workspace_curriculum_board(req, user)
        classes, subjects, weeks, class_level, subject, scope_warnings = await _scope(
            req, class_level, subject, term, board
        )
        selected_week = next(
            (week for week in weeks if scheme_id and str(week.get("id")) == scheme_id),
            weeks[0] if weeks else {},
        )
        scheme_notice = (
            "That curriculum week is not available for the selected class, subject, and term. "
            "Choose a week below to continue."
            if scheme_id and (not selected_week or str(selected_week.get("id")) != scheme_id)
            else None
        )
        scope_notice = (
            f"{requested_subject} is not available for {class_level}. The subject has been changed to {subject or 'the first available subject'}; please confirm the scope before continuing."
            if (requested_subject := req.query_params.get("subject")) and requested_subject != subject
            else None
        )
        # Resolve scope first so an expired access token can refresh before the
        # independent workspace requests run concurrently.
        plans_data, summary_data, coverage_data = await asyncio.gather(
            _fetch_data(req, "/lesson-plans", source="lesson plans"),
            _fetch_data(req, "/lesson-plans/coverage/summary", source="coverage summary"),
            _fetch_data(req, "/lesson-plans/coverage", source="coverage records"),
        )
        plans, plans_warning = plans_data
        summary, summary_warning = summary_data
        coverage_rows, coverage_warning = coverage_data
        plans = plans if isinstance(plans, list) else []
        summary = summary if isinstance(summary, dict) else {"total": 0, "completed": 0, "verified": 0}
        coverage_rows = coverage_rows if isinstance(coverage_rows, list) else []
        source_warnings = [
            warning for warning in (
                *scope_warnings, plans_warning, summary_warning, coverage_warning,
            ) if warning
        ]

        select_cls = "border-0 rounded-3"
        select_style = "background:#F1F4F1;"
        scope_form = Form(
            Div(Label("Class", for_="class_level", cls="small fw-semibold text-muted mb-1"), Select("class_level", *[(c, c, c == class_level) for c in classes], cls=select_cls, style=select_style, data_scope_reload="true"), Span(Span("", cls="spinner-border spinner-border-sm me-1", aria_hidden="true"), "Updating subjects and lesson weeks…", id="scope-loading", cls="small text-success d-none mt-2", role="status"), cls="col-md-4"),
            Div(Label("Subject", for_="subject", cls="small fw-semibold text-muted mb-1"), Select("subject", *[(s.get("subject_name", ""), s.get("subject_name", ""), s.get("subject_name") == subject) for s in subjects], cls=select_cls, style=select_style, data_scope_reload="true"), P("Changing class refreshes the available subjects and lesson-plan form automatically.", cls="form-text small text-muted"), cls="col-md-5"),
            Div(Label("Term", for_="term", cls="small fw-semibold text-muted mb-1"), Select("term", *[(value, label, value == term) for label, value in _terms()], cls=select_cls, style=select_style, data_scope_reload="true"), cls="col-md-3"),
            Div(Button("Refresh scheme", type="submit", variant="success", cls="rounded-pill px-4 btn-brand mt-3"), cls="col-12"),
            action="/app/teaching",
            method="get",
            cls="row g-3 align-items-end",
            data_scope_form="true",
        )

        week_options = [
            (str(w.get("id")), f"Week {w.get('week_number')}: {w.get('topic', '')}", str(w.get("id")) == str(selected_week.get("id")))
            for w in weeks
        ]
        create_form = Form(
            Input(type="hidden", name="curriculum_id", value=selected_week.get("curriculum_id", "")),
            Input(type="hidden", name="return_class_level", value=class_level),
            Input(type="hidden", name="return_subject", value=subject),
            Input(type="hidden", name="return_term", value=term),
            Input(type="hidden", name="return_board", value=board),
            Div(Label("Scheme week", for_="scheme_id", cls="small fw-semibold text-muted mb-1"), Select("scheme_id", *week_options, required=True, aria_describedby="scheme-week-help", cls=select_cls, style=select_style), P("Choose a teaching week. Open the topic list below to read the complete scheme wording.", id="scheme-week-help", cls="form-text small text-muted"), Details(Summary("Read full topics for this term", cls="small text-success fw-semibold"), Ul(*[Li(f"Week {w.get('week_number')}: {w.get('topic', '')}", cls="mb-1") for w in weeks], cls="small text-muted mb-0 ps-4") if weeks else P("No weeks are available for this scope.", cls="small text-muted mb-0"), cls="mt-2"), cls="col-12"),
            Div(Label("Plan title", for_="plan-title", cls="small fw-semibold text-muted mb-1"), Input(name="title", id="plan-title", required=True, value=f"{subject} - {term}", cls="form-control border-0 rounded-3", style="background:#F1F4F1;"), cls="col-12"),
            Div(
                Label("Learning activities (examples below)", for_="plan-activities", cls="small fw-semibold text-muted mb-1"),
                Textarea(
                    name="activities",
                    id="plan-activities",
                    placeholder="e.g.\n1. Demonstrate evaporation using a bowl of warm water and chalkboard sketch.\n2. Guide pupils in pairs to list 3 domestic uses of clean water.\n3. Class discussion on water conservation in the community.",
                    rows="4",
                    cls="form-control border-0 rounded-3",
                    style="background:#F1F4F1; font-size: 0.88rem;",
                ),
                cls="col-md-6",
            ),
            Div(
                Label("Assessment & check for understanding", for_="plan-assessment", cls="small fw-semibold text-muted mb-1"),
                Textarea(
                    name="assessment_notes",
                    id="plan-assessment",
                    placeholder="e.g.\n1. Oral check: Ask pupils to define evaporation in their own words.\n2. Pair exercise: State 2 differences between boiling and evaporation.\n3. Workbook task: Questions 1 to 3.",
                    rows="4",
                    cls="form-control border-0 rounded-3",
                    style="background:#F1F4F1; font-size: 0.88rem;",
                ),
                cls="col-md-6",
            ),
            Div(
                Label("Instructional materials & local teaching resources", for_="plan-resources", cls="small fw-semibold text-muted mb-1"),
                Textarea(
                    name="resources",
                    id="plan-resources",
                    placeholder="e.g.\n1. Wall chart of the water cycle\n2. Realia: Transparent cup of water, chalkboard ruler\n3. Primary Science Textbook, page 42",
                    rows="3",
                    cls="form-control border-0 rounded-3",
                    style="background:#F1F4F1; font-size: 0.88rem;",
                ),
                cls="col-12",
            ),
            Div(Button(Icon("plus-lg", cls="bi me-1"), "Create lesson plan", type="submit", variant="success", cls="rounded-pill px-4 btn-brand"), cls="col-12"),
            action="/app/teaching/create",
            method="post",
            cls="row g-3",
            id="create-lesson-plan",
        )
        plans_view = Div(*[_plan_card(plan, user) for plan in plans[:8]], cls="d-grid gap-3") if plans else Card(
            Div(
                Icon("journal-text", cls="bi fs-2 text-success mb-2"),
                P(
                    "Plans could not be loaded. Use Refresh scheme to try again."
                    if plans_warning else
                    "No plans yet. Select a week above to create your first grounded lesson plan.",
                    cls="text-muted small mb-0",
                ),
                cls="p-4 text-center",
            ),
            cls="border-0 shadow-sm rounded-4",
        )

        guided_output = {"lesson": "Lesson note", "exercise": "Classwork"}.get(output)
        guided_context = Card(
            Div(
                Div(
                    Icon("compass", cls="bi text-success fs-5 me-2"),
                    Div(
                        Strong("Guided workflow", cls="d-block text-dark"),
                        P(
                            f"{guided_output or 'Teaching'} for {class_level} · {subject or 'your subject'} · {term}. Change the scope above without losing your place.",
                            cls="small text-muted mb-0",
                        ),
                    ),
                ),
                A("Back to start", href="/app/start", cls="btn btn-outline-success rounded-pill px-3 ms-auto flex-shrink-0"),
                cls="d-flex align-items-center gap-2 flex-wrap p-3",
            ),
            cls="border-0 shadow-sm rounded-4 mb-4 bg-white",
        ) if mode == "guided" else None

        content = Container(
            Div(
                Div(Span("PACKAGE B · CURRICULUM DELIVERY", cls="small fw-bold text-success letter-spacing-1"), H1("Teach from the scheme, week by week.", cls="fs-2 fw-bold text-dark mb-2 mt-2"), P("Turn the national curriculum into a practical lesson plan, an AI-assisted note, a weekly exercise, and verified coverage.", cls="text-muted mb-0"), cls="flex-grow-1"),
                A(Icon("book-half", cls="bi me-2"), "Browse curriculum", href="/app/curriculum", cls="btn btn-outline-success rounded-pill px-4 align-self-start"),
                cls="d-flex justify-content-between align-items-start gap-3 mb-4 flex-wrap",
            ),
            guided_context,
            Alert(
                "Some teaching information could not be loaded. Use Refresh scheme to retry.",
                variant="warning",
                cls="rounded-4 border-0",
            ) if source_warnings else None,
            Alert(scope_notice, variant="info", cls="rounded-4") if scope_notice else None,
            Alert(
                f"Lesson planning opened for Week {selected_week.get('week_number')}: {selected_week.get('topic', 'selected curriculum topic')}.",
                variant="success",
                cls="rounded-4",
            ) if scheme_id and selected_week and not scheme_notice else None,
            Card(Div(H2("Choose your teaching scope", cls="fs-5 fw-bold mb-3"), scope_form, cls="p-4"), cls="border-0 shadow-sm rounded-4 mb-4"),
            Row(
                Col(Card(Div(H2("Teaching tools", cls="fs-5 fw-bold mb-2"), P("Create printable classwork from your lesson plans.", cls="small text-muted mb-3"), A(Icon("plus-lg", cls="bi me-1"), "Open worksheets", href=f"/app/teaching/worksheets?{urlencode({'class_level': class_level, 'subject': subject, 'term': term})}", cls="btn btn-brand rounded-pill px-4"), cls="p-4 h-100"), cls="border-0 shadow-sm rounded-4 h-100"), span=12, lg=4),
                Col(Card(Details(
                    Summary("Coverage progress", cls="fs-5 fw-bold text-dark"),
                    P("Use this shared tracker after choosing a lesson week: mark it as taught when delivered, then a school administrator confirms it. It tracks syllabus delivery, not lesson-note approval.", cls="small text-muted mt-2 mb-3"),
                    Div(Span("Step 1: Start tracking", cls="badge rounded-pill bg-light text-dark me-2"), Span("Step 2: Mark taught", cls="badge rounded-pill bg-light text-dark me-2"), Span("Step 3: Admin confirms", cls="badge rounded-pill bg-light text-dark"), cls="mb-3"),
                    P(f"{summary.get('total', 0)} weeks tracked | {summary.get('planned', 0)} not started | {summary.get('in_progress', 0)} in progress | {summary.get('completed', 0)} marked taught | {summary.get('verified', 0)} admin-confirmed" if not summary_warning else "Coverage counts are temporarily unavailable.", cls="small fw-semibold text-success mb-3", role="status"),
                    Row(*[Col(_coverage_card(row, user), span=12, md=6, xl=4) for row in coverage_rows[:12]], g=3) if coverage_rows else P("Coverage records could not be loaded. Use Refresh scheme to retry." if coverage_warning else "No weeks are being tracked yet. Choose a lesson plan below and select Start coverage tracking; the new record will appear here.", cls="text-muted small mb-0"),
                    cls="p-4", open=show_coverage, id="coverage-progress",
                ), cls="border-0 shadow-sm rounded-4 h-100"), span=12, lg=8),
                g=3, cls="mb-4 align-items-stretch",
            ),
            Alert(scheme_notice, variant="warning", cls="rounded-4") if scheme_notice else None,
            Card(Div(H2("Create a lesson plan", cls="fs-5 fw-bold mb-3"), P(f"Grounded in {subject or 'your selected subject'} - {term}.", cls="small text-muted mb-3"), create_form, cls="p-4"), cls="border-0 shadow-sm rounded-4 mb-4"),
            Div(H2("Your teaching plans", cls="fs-5 fw-bold mb-3"), plans_view, cls="teaching-plans-section"),
            cls="py-4 pt-lg-5 teaching-workspace",
        )
        confirmation = Div(
            Div(
                Div(
                    Div(Icon("exclamation-triangle", cls="bi text-warning fs-4 me-3"), Div(H2("Replace this draft?", id="lesson-note-confirm-title", cls="fs-5 fw-bold mb-1"), P("This refinement will replace the current lesson note. Your unsaved edits will be lost.", id="lesson-note-confirm-message", cls="text-muted mb-0")), cls="d-flex align-items-start"),
                    cls="modal-body p-4",
                ),
                Div(Button("Keep editing", type="button", variant="outline-secondary", cls="rounded-pill px-4", **{"data-bs-dismiss": "modal"}), Button("Replace draft", type="button", id="confirm-lesson-note-refinement", cls="btn btn-brand rounded-pill px-4"), cls="modal-footer border-0 pt-0"),
                cls="modal-content border-0 rounded-4 shadow-lg",
            ),
            cls="modal-dialog modal-dialog-centered",
        )
        confirmation = Div(confirmation, id="lesson-note-confirm-modal", cls="modal fade", tabindex="-1", aria_labelledby="lesson-note-confirm-title", aria_describedby="lesson-note-confirm-message", aria_hidden="true")
        confirmation_script = Script("""
        (() => {
          let pending = null;
          let pendingTrigger = null;
          const modal = document.getElementById('lesson-note-confirm-modal');
          const confirm = document.getElementById('confirm-lesson-note-refinement');
          function restorePendingButton(button) {
            if (!button || button.dataset.loadingActive !== 'true') return;
            if (button.dataset.loadingOriginalHtml) button.innerHTML = button.dataset.loadingOriginalHtml;
            button.disabled = false;
            button.removeAttribute('aria-busy');
            delete button.dataset.loadingActive;
            delete button.dataset.loadingOriginalHtml;
            if (button.form) delete button.form.dataset.loadingButton;
          }
          document.addEventListener('submit', (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement) || !form.matches('form[action*="/lesson-note"]')) return;
            const editor = form.closest('.card')?.querySelector('[data-note-editor="true"]');
            if (!editor || editor.value === editor.defaultValue) return;
            if (form.dataset.refinementConfirmed === 'true') { delete form.dataset.refinementConfirmed; return; }
            event.preventDefault();
            pending = form;
            pendingTrigger = event.submitter;
            // The global capture-phase handler may have already swapped this
            // submitter for a spinner before the dirty-draft guard runs.
            // This submission is cancelled, so clear that loading state while
            // the confirmation is open, not only after the user dismisses it.
            restorePendingButton(pendingTrigger);
            if (modal && window.bootstrap?.Modal) bootstrap.Modal.getOrCreateInstance(modal).show();
          });
          confirm?.addEventListener('click', () => {
            if (!pending) return;
            const form = pending;
            pending = null;
            form.dataset.refinementConfirmed = 'true';
            bootstrap.Modal.getOrCreateInstance(modal).hide();
            form.requestSubmit();
          });
          modal?.addEventListener('hidden.bs.modal', () => {
            // The global mutation-button handler starts its spinner during the
            // capture phase, before this dirty-draft guard cancels submission.
            // Restore it only when the user dismissed the confirmation. On
            // Replace, pending is cleared before the form is resubmitted.
            if (pending && pendingTrigger?.isConnected) restorePendingButton(pendingTrigger);
            if (pendingTrigger?.isConnected) pendingTrigger.focus();
            pendingTrigger = null;
            pending = null;
          });
        })();

        (() => {
          const scopeForm = document.querySelector('[data-scope-form="true"]');
          const loading = document.getElementById('scope-loading');
          scopeForm?.querySelectorAll('[data-scope-reload="true"]').forEach(control => {
            control.addEventListener('change', () => {
              if (loading) loading.classList.remove('d-none');
              scopeForm.querySelectorAll('button[type="submit"]').forEach(button => {
                button.disabled = true;
                button.setAttribute('aria-busy', 'true');
              });
              scopeForm.requestSubmit();
            });
          });

          function inlineMarkdown(parent, text) {
            const pattern = /(\\$\\$[\\s\\S]+?\\$\\$|\\$[^$\\n]+\\$|\\\\\\([\\s\\S]+?\\\\\\)|\\([^()]+\\)\\/\\([^()]+\\)|\\*\\*[^*]+\\*\\*|\\*[^*]+\\*|`[^`]+`|[A-Za-z]+_[A-Za-z0-9]+|[A-Za-z0-9]\\^[A-Za-z0-9]+)/g;
            let cursor = 0;
            for (const match of text.matchAll(pattern)) {
              const at = match.index;
              if (at > cursor) parent.append(document.createTextNode(text.slice(cursor, at)));
              const token = match[0];
              let element;
              if (token.startsWith('**')) element = document.createElement('strong');
              else if (token.startsWith('*')) element = document.createElement('em');
              else if (token.startsWith('`')) element = document.createElement('code');
              else if (/^[A-Za-z]+_[A-Za-z0-9]+$/.test(token) || /^[A-Za-z0-9]\\^[A-Za-z0-9]+$/.test(token)) {
                const splitAt = token.includes('_') ? token.indexOf('_') : token.indexOf('^');
                const base = document.createElement('span');
                base.textContent = token.slice(0, splitAt);
                const script = document.createElement(token[splitAt] === '_' ? 'sub' : 'sup');
                script.textContent = token.slice(splitAt + 1);
                parent.append(base, script);
                cursor = at + token.length;
                continue;
              } else if (/^\\([^()]+\\)\\/\\([^()]+\\)$/.test(token)) {
                const slashAt = token.indexOf('/');
                const numerator = document.createElement('sup');
                inlineMarkdown(numerator, token.slice(1, slashAt - 1));
                const denominator = document.createElement('sub');
                inlineMarkdown(denominator, token.slice(slashAt + 2, -1));
                parent.append(numerator, document.createTextNode('/'), denominator);
                cursor = at + token.length;
                continue;
              }
              if (element) {
                element.textContent = token.slice(token.startsWith('**') ? 2 : 1, token.startsWith('**') ? -2 : -1);
                parent.append(element);
              } else parent.append(document.createTextNode(token));
              cursor = at + token.length;
            }
            if (cursor < text.length) parent.append(document.createTextNode(text.slice(cursor)));
          }

          function renderPreview(editor, target) {
            target.replaceChildren();
            let list = null;
            (editor.value || '').split(/\\r?\\n/).forEach(raw => {
              const line = raw.trim();
              if (!line) { list = null; return; }
              if (/^[-*]\\s+/.test(line) || /^\\d+[.)]\\s+/.test(line)) {
                const ordered = /^\\d+[.)]\\s+/.test(line);
                if (!list || list.tagName !== (ordered ? 'OL' : 'UL')) {
                  list = document.createElement(ordered ? 'ol' : 'ul');
                  list.className = 'mb-2 ps-4';
                  target.append(list);
                }
                const item = document.createElement('li');
                inlineMarkdown(item, line.replace(/^(?:[-*]|\\d+[.)])\\s+/, ''));
                list.append(item);
                return;
              }
              list = null;
              const heading = line.match(/^(#{1,3})\\s+(.*)$/);
              const el = heading ? document.createElement(`h${heading[1].length + 2}`) : document.createElement('p');
              el.className = heading ? 'text-success mt-3 mb-2' : 'mb-2';
              inlineMarkdown(el, heading ? heading[2] : line);
              target.append(el);
            });
            if (!target.childNodes.length) target.textContent = 'The lesson note is empty.';
            if (typeof renderMathInElement === 'function') {
              renderMathInElement(target, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\\\(',right:'\\\\)',display:false},{left:'\\\\[',right:'\\\\]',display:true}],throwOnError:false});
            }
          }

          document.querySelectorAll('[data-note-preview]').forEach(target => {
            const editor = document.getElementById(target.dataset.notePreview);
            if (!editor) return;
            const details = target.closest('details');
            editor.addEventListener('input', () => { if (details?.open) renderPreview(editor, target); });
            details?.addEventListener('toggle', () => { if (details.open) renderPreview(editor, target); });
            if (details?.open) renderPreview(editor, target);
          });
        })();
        """)
        return AppShell(
            Title("Teaching workspace — SkuPhase"),
            Div(content, confirmation, confirmation_script),
            user=user,
            active="teaching",
            flash=pop_flash(req),
            crumbs=[("Teaching workspace", None)],
        )

    @app.get("/app/teaching/worksheets")
    async def teaching_worksheets(
        req: Request,
        class_level: str = "Primary 4",
        subject: str = "",
        term: str = "First Term",
    ):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        board = await workspace_curriculum_board(req, user)
        classes, subjects, weeks, class_level, subject, warnings = await _scope(req, class_level, subject, term, board)
        plans_data, exercises_data = await asyncio.gather(
            _fetch_data(req, "/lesson-plans", source="lesson plans"),
            _fetch_data(req, "/lesson-plans/exercises", source="worksheets"),
        )
        plans, plans_warning = plans_data
        exercises, exercises_warning = exercises_data
        plans = plans if isinstance(plans, list) else []
        exercises = exercises if isinstance(exercises, list) else []
        source_warnings = [warning for warning in (*warnings, plans_warning, exercises_warning) if warning]
        exercises_view = Row(*[Col(_exercise_card(item), span=12, md=6, xl=4) for item in exercises[:12]], g=3) if exercises else Card(
            Div(Icon("file-earmark-text", cls="bi fs-2 text-success mb-2"), P("No worksheets yet. Build one above and your saved worksheets will appear here.", cls="small text-muted mb-0"), cls="p-4 text-center"),
            cls="border-0 rounded-4 bg-light",
        )
        content = Container(
            A(Icon("arrow-left", cls="bi me-2"), "Back to teaching", href=f"/app/teaching?{urlencode({'class_level': class_level, 'subject': subject, 'term': term})}", cls="btn btn-link text-success text-decoration-none px-0 mb-3"),
            Div(Span("TEACHING TOOLS", cls="small fw-bold text-success"), H1("Weekly worksheets", cls="fs-2 fw-bold text-dark mt-2 mb-2"), P(f"Create and revisit printable classwork for {class_level} · {subject or 'your subject'} · {term}.", cls="text-muted mb-0"), cls="mb-4"),
            Alert("Some worksheet information could not be loaded. You can still draft a worksheet; refresh this page to retry.", variant="warning", cls="rounded-4 border-0") if source_warnings else None,
            Card(Div(H2("Build a weekly worksheet", cls="fs-5 fw-bold mb-2"), P("Start with one question. Add more only as needed.", cls="small text-muted mb-3"), _worksheet_form(subject, term, plans), cls="p-4"), cls="border-0 shadow-sm rounded-4 mb-4"),
            Div(H2("Recent worksheets", cls="fs-5 fw-bold mb-3"), exercises_view),
            cls="py-4 pt-lg-5 teaching-workspace teaching-worksheets",
        )
        question_script = Script("""
        (() => {
          const list = document.getElementById('worksheet-question-list');
          const add = document.getElementById('add-worksheet-question');
          add?.addEventListener('click', () => {
            const rows = list?.querySelectorAll('[data-worksheet-question]') || [];
            if (!list || rows.length >= 20) return;
            const used = new Set(Array.from(rows, row => Number(row.dataset.questionIndex)));
            let next = 1;
            while (used.has(next) && next <= 20) next += 1;
            if (next > 20) return;
            const clone = rows[0].cloneNode(true);
            clone.dataset.questionIndex = String(next);
            clone.setAttribute('aria-label', `Worksheet question ${next}`);
            const heading = clone.querySelector('[data-question-heading]');
            if (heading) heading.textContent = `Question ${next}`;
            clone.querySelectorAll('[id]').forEach(el => { el.id = el.id.replace(/-[0-9]+$/, `-${next}`); });
            clone.querySelectorAll('[name]').forEach(field => {
              const prefix = field.name.replace(/_[0-9]+$/, '');
              field.name = `${prefix}_${next}`;
              if (field.tagName === 'SELECT') field.selectedIndex = 0;
              else if (field.name.startsWith('question_marks_')) field.value = '1';
              else field.value = '';
            });
            clone.querySelectorAll('label[for]').forEach(label => { label.htmlFor = label.htmlFor.replace(/-[0-9]+$/, `-${next}`); });
            clone.querySelectorAll('[aria-describedby]').forEach(el => el.setAttribute('aria-describedby', el.getAttribute('aria-describedby').replace(/-[0-9]+$/, `-${next}`)));
            list.appendChild(clone);
            list.querySelectorAll('.remove-worksheet-question').forEach(button => { button.disabled = false; });
            add.disabled = rows.length + 1 >= 20;
            clone.querySelector('textarea')?.focus();
          });
          list?.addEventListener('click', event => {
            const remove = event.target.closest('.remove-worksheet-question');
            if (!remove) return;
            if (list.querySelectorAll('[data-worksheet-question]').length <= 1) return;
            remove.closest('[data-worksheet-question]')?.remove();
            if (list.querySelectorAll('[data-worksheet-question]').length === 1) {
              list.querySelector('.remove-worksheet-question').disabled = true;
            }
            add.disabled = list.querySelectorAll('[data-worksheet-question]').length >= 20;
          });
        })();
        """)
        return AppShell(
            Title("Weekly worksheets — SkuPhase"),
            Div(content, question_script),
            user=user,
            active="teaching",
            flash=pop_flash(req),
            crumbs=[("Teaching workspace", "/app/teaching"), ("Weekly worksheets", None)],
        )

    @app.post("/app/teaching/create")
    async def create_plan(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        activities = [line.strip() for line in str(form.get("activities", "")).splitlines() if line.strip()]
        resources = [line.strip() for line in str(form.get("resources", "")).splitlines() if line.strip()]
        payload = {"curriculum_id": str(form.get("curriculum_id", "")), "scheme_id": str(form.get("scheme_id", "")), "title": str(form.get("title", "")), "activities": activities, "resources": resources, "assessment_notes": str(form.get("assessment_notes", "")) or None}
        resp = await call_api(req, "POST", "/lesson-plans", json=payload)
        ok, data = unwrap(resp)
        if ok:
            push_flash(req, "Lesson plan created from the selected scheme week.", "success")
        else:
            push_flash(req, data.get("message", "Could not create lesson plan."), "danger")
        scope_url = urlencode({"class_level": form.get("return_class_level", "Primary 4"), "subject": form.get("return_subject", ""), "term": form.get("return_term", "First Term")})
        return RedirectResponse(f"/app/teaching?{scope_url}", status_code=303)

    @app.post("/app/teaching/{plan_id}/lesson-note")
    async def lesson_note(req: Request, plan_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        guidance = (form.get("guidance") or "").strip()
        payload = {"lesson_plan_id": plan_id}
        if guidance:
            payload["additional_guidance"] = guidance
        resp = await call_api(req, "POST", f"/lesson-plans/{plan_id}/lesson-note", json=payload)
        ok, data = unwrap(resp)
        if ok and data.get("ai_lesson_note"):
            msg = f"AI lesson note updated ({guidance[:30]}...)." if guidance else "AI lesson note drafted from the scheme."
            push_flash(req, msg, "success")
        else:
            err_detail = data.get("message") or "AI generation timed out or could not complete. Please tap 'Draft with AI' to try again."
            push_flash(req, f"Lesson note generation incomplete: {err_detail}", "warning")
        return RedirectResponse("/app/teaching", status_code=303)

    @app.post("/app/teaching/{plan_id}/save-note")
    async def save_note(req: Request, plan_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        status = str(form.get("status", "submitted"))
        payload = {"ai_lesson_note": str(form.get("ai_lesson_note", "")), "status": status}
        resp = await call_api(req, "PATCH", f"/lesson-plans/{plan_id}", json=payload)
        ok, data = unwrap(resp)
        push_flash(req, "Lesson note saved and submitted for review." if ok else data.get("message", "Could not save lesson note."), "success" if ok else "danger")
        return RedirectResponse("/app/teaching", status_code=303)

    @app.post("/app/teaching/{plan_id}/approve")
    async def approve_plan(req: Request, plan_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "PATCH", f"/lesson-plans/{plan_id}", json={"status": "approved"})
        ok, data = unwrap(resp)
        push_flash(req, "Lesson plan approved for teaching." if ok else data.get("message", "Could not approve lesson plan."), "success" if ok else "danger")
        return RedirectResponse("/app/teaching", status_code=303)

    @app.post("/app/teaching/{plan_id}/coverage")
    async def start_coverage(req: Request, plan_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/lesson-plans/{plan_id}/coverage")
        ok, data = unwrap(resp)
        message = ("Coverage tracking started. The week is now visible in Coverage progress." if resp.status_code == 201 else "This week is already on the school coverage tracker.") if ok else data.get("message", "Could not start coverage.")
        push_flash(req, message, "success" if ok else "danger")
        return RedirectResponse("/app/teaching?show_coverage=1#coverage-progress", status_code=303)

    @app.post("/app/teaching/coverage/{coverage_id}")
    async def update_coverage(req: Request, coverage_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        status = str(form.get("status", "planned"))
        resp = await call_api(req, "PATCH", f"/lesson-plans/coverage/{coverage_id}", json={"status": status})
        ok, data = unwrap(resp)
        push_flash(req, "Coverage status updated." if ok else data.get("message", "Could not update coverage."), "success" if ok else "danger")
        return RedirectResponse("/app/teaching?show_coverage=1#coverage-progress", status_code=303)

    @app.post("/app/teaching/exercises/create")
    async def create_exercise(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        questions = []
        legacy_marks = {}
        question_rows = form.getlist("question_text")
        if not question_rows:
            # Compatibility with the earlier one-question-per-line form.
            legacy_text = str(form.get("questions", ""))
            if legacy_text:
                for line in legacy_text.splitlines():
                    question_text = line.strip()
                    if not question_text:
                        continue
                    question_text = re.sub(r"^(?:question\s*)?\d+[.)\-:]\s*", "", question_text, flags=re.IGNORECASE)
                    mark_suffix = re.search(r"\s*\[(\d+)\s+marks?\]\s*$", question_text, flags=re.IGNORECASE)
                    marks = int(mark_suffix.group(1)) if mark_suffix else 1
                    if mark_suffix:
                        question_text = question_text[:mark_suffix.start()].strip()
                    question_rows.append(question_text)
                    legacy_marks[len(question_rows)] = marks
            else:
                question_rows = [form.get(f"question_text_{index}", "") for index in range(1, 21)]
        for index, raw_text in enumerate(question_rows, start=1):
            question_text = str(form.get(f"question_text_{index}", raw_text) or "").strip()
            if not question_text:
                continue
            try:
                marks = int(form.get(f"question_marks_{index}", legacy_marks.get(index, 1)) or legacy_marks.get(index, 1))
            except (TypeError, ValueError):
                marks = 1
            question_type = str(form.get(f"question_type_{index}", "short_answer") or "short_answer")
            options = [item.strip() for item in str(form.get(f"answer_options_{index}", "")).splitlines() if item.strip()]
            if question_type == "mcq" and len(options) < 2:
                push_flash(req, f"Question {index} is multiple choice; add at least two answer options.", "danger")
                return RedirectResponse("/app/teaching", status_code=303)
            if question_type not in {"short_answer", "mcq"}:
                push_flash(req, f"Question {index} has an unsupported question type.", "danger")
                return RedirectResponse("/app/teaching", status_code=303)
            questions.append({
                "question_number": len(questions) + 1,
                "type": question_type,
                "question_text": question_text,
                "marks": max(1, min(marks, 100)),
                "answer_lines": 0 if question_type == "mcq" else 2,
                "answer_options": options if options else None,
                "answer_key": str(form.get(f"answer_key_{index}", "")).strip() or None,
            })
        if not questions:
            push_flash(req, "Enter at least one question before creating the worksheet.", "danger")
            return RedirectResponse("/app/teaching/worksheets", status_code=303)
        payload = {
            "lesson_plan_id": str(form.get("lesson_plan_id", "")),
            "title": str(form.get("title", "")),
            "instructions": str(form.get("instructions", "")) or None,
            "questions": questions,
        }
        resp = await call_api(req, "POST", "/lesson-plans/exercises", json=payload)
        ok, data = unwrap(resp)
        push_flash(req, "Weekly worksheet created." if ok else data.get("message", "Could not create worksheet."), "success" if ok else "danger")
        return RedirectResponse("/app/teaching/worksheets", status_code=303)

    @app.get("/app/teaching/exercises/{exercise_id}/export")
    async def export_exercise(req: Request, exercise_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        export_resp = await call_api(req, "POST", f"/lesson-plans/exercises/{exercise_id}/export")
        ok, data = unwrap(export_resp)
        if not ok:
            push_flash(req, data.get("message", "Could not export worksheet."), "danger")
            return RedirectResponse("/app/teaching", status_code=303)
        filename = data.get("filename", "worksheet.pdf")
        if not re.fullmatch(r"[0-9a-f]{32}\.pdf", str(filename or "")):
            push_flash(req, "The worksheet export returned an invalid file name.", "danger")
            return RedirectResponse("/app/teaching", status_code=303)
        download_resp = await call_api(req, "GET", f"/lesson-plans/exercises/{exercise_id}/download/{filename}")
        if not download_resp.is_success:
            push_flash(req, "Worksheet was generated but could not be downloaded.", "danger")
            return RedirectResponse("/app/teaching", status_code=303)
        return Response(
            content=download_resp.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "private, no-store",
            },
        )

    @app.get("/app/teaching/{lesson_plan_id}/lesson-note/export.pdf")
    async def export_lesson_note_pdf_route(req: Request, lesson_plan_id: str):
        """Proxy a lesson-note PDF through the signed browser session."""
        guard = ensure_login(req)
        if guard:
            return guard
        try:
            safe_plan_id = str(UUID(lesson_plan_id))
        except (ValueError, TypeError):
            push_flash(req, "That lesson note link is invalid.", "danger")
            return RedirectResponse("/app/teaching", status_code=303)

        download_resp = await call_api(
            req,
            "GET",
            f"/lesson-plans/{safe_plan_id}/lesson-note/export.pdf",
        )
        if not download_resp.is_success:
            push_flash(req, "This lesson note has no content yet — tap 'Draft with AI' to generate it before exporting.", "warning")
            return RedirectResponse("/app/teaching", status_code=303)
        disposition = download_resp.headers.get("content-disposition", "")
        filename_match = re.search(r'filename="([a-zA-Z0-9._-]+\.pdf)"', disposition)
        filename = filename_match.group(1) if filename_match else f"lesson-note-{safe_plan_id[:8]}.pdf"
        return Response(
            content=download_resp.content,
            media_type=download_resp.headers.get("content-type", "application/pdf"),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "private, no-store",
            },
        )

    @app.get("/app/teaching/{lesson_plan_id}/lesson-note/export.docx")
    async def export_lesson_note_docx_route(req: Request, lesson_plan_id: str):
        """Proxy a lesson-note DOCX through the signed browser session."""
        guard = ensure_login(req)
        if guard:
            return guard
        try:
            safe_plan_id = str(UUID(lesson_plan_id))
        except (ValueError, TypeError):
            push_flash(req, "That lesson note link is invalid.", "danger")
            return RedirectResponse("/app/teaching", status_code=303)

        download_resp = await call_api(
            req,
            "GET",
            f"/lesson-plans/{safe_plan_id}/lesson-note/export.docx",
        )
        if not download_resp.is_success:
            push_flash(req, "This lesson note has no content yet — tap 'Draft with AI' to generate it before exporting as Word.", "warning")
            return RedirectResponse("/app/teaching", status_code=303)
        disposition = download_resp.headers.get("content-disposition", "")
        filename_match = re.search(r'filename="([a-zA-Z0-9._-]+\.docx)"', disposition)
        filename = filename_match.group(1) if filename_match else f"lesson-note-{safe_plan_id[:8]}.docx"
        return Response(
            content=download_resp.content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "private, no-store",
            },
        )
