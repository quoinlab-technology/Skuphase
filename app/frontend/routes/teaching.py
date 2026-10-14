"""Teacher-facing curriculum delivery workspace (Package B)."""

import asyncio
import logging
import re
from uuid import UUID

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


async def _scope(req: Request, class_level: str, subject: str, term: str):
    warnings = []
    classes_data, failed_source = await _fetch_data(
        req, "/curriculum/classes", params={"board": "NERDC"}, source="curriculum classes"
    )
    if failed_source:
        warnings.append(failed_source)
    classes = classes_data.get("classes", []) if isinstance(classes_data, dict) else []
    if not classes:
        classes = [class_level]
    if class_level not in classes:
        class_level = classes[0]

    subjects_data, failed_source = await _fetch_data(
        req,
        "/curriculum/subjects",
        params={"class_level": class_level, "board": "NERDC"},
        source="curriculum subjects",
    )
    if failed_source:
        warnings.append(failed_source)
    subjects = subjects_data.get("subjects", []) if isinstance(subjects_data, dict) else []
    if not subject and subjects:
        subject = subjects[0].get("subject_name", "")
    if subjects and subject not in {item.get("subject_name") for item in subjects}:
        subject = subjects[0].get("subject_name", "")

    weeks_data, weeks_warning = await _fetch_data(
        req,
        "/curriculum/school/weeks",
        params={"class_level": class_level, "subject": subject, "term": term},
        source="curriculum weeks",
    )
    weeks = weeks_data.get("weeks", []) if isinstance(weeks_data, dict) else []
    if weeks_warning:
        fallback_data, fallback_warning = await _fetch_data(
            req,
            "/curriculum/weeks",
            params={"class_level": class_level, "subject": subject, "term": term},
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
    ai_note = plan.get("ai_lesson_note")
    
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
        cls="mb-2",
    ) if ai_note else None

    return Card(
        Div(
            Div(
                Div(Span(f"Week {plan.get('week_number', '-')}", cls="small text-success fw-bold"), _status_badge(plan.get("status", "draft"))),
                Strong(plan.get("title") or "Untitled lesson plan", cls="d-block fs-6 text-dark mt-2"),
                P(f"{plan.get('term', '')} · {plan.get('week_number', '')}", cls="small text-muted mb-0"),
                cls="d-flex justify-content-between align-items-start",
            ),
            P(" · ".join((plan.get("learning_objectives") or [])[:2]) or "Add learning objectives from the curriculum week.", cls="small text-muted mt-3 mb-3"),
            Div(
                Strong("Draft lesson note", cls="small text-success d-block mb-1"),
                refinement_chips,
                Form(
                    Label("Lesson note draft", for_=f"lesson-note-{plan_id}", cls="small fw-semibold text-muted mb-1"),
                    Textarea(ai_note or "", id=f"lesson-note-{plan_id}", name="ai_lesson_note", rows="6", aria_describedby=f"lesson-note-help-{plan_id}", data_note_editor="true", cls="form-control form-control-sm border-0 rounded-3", style="background:#F1F8F2; font-size: 0.9rem; line-height: 1.5;"),
                    P("Your edits are saved when you choose Save & submit. Refinements replace the draft, so you will be asked before unsaved changes are discarded.", id=f"lesson-note-help-{plan_id}", cls="form-text small text-muted"),
                    Input(type="hidden", name="status", value="submitted"),
                    Div(
                        Button(Icon("check-lg", cls="bi me-1"), "Save & submit for review", type="submit", variant="success", size="sm", cls="rounded-pill"),
                        cls="d-inline-block mt-2 me-2",
                    ),
                    action=f"/app/teaching/{plan_id}/save-note",
                    method="post",
                    cls="d-inline",
                ),
                A(
                    Icon("file-earmark-pdf", cls="bi me-1"),
                    "Print / download PDF",
                    href=f"/app/teaching/{plan_id}/lesson-note/export.pdf",
                    cls="btn btn-sm btn-outline-success rounded-pill mt-2 me-2",
                ),
                A(
                    Icon("file-earmark-word", cls="bi me-1"),
                    "Download Word",
                    href=f"/app/teaching/{plan_id}/lesson-note/export.docx",
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
                    Button(Icon("check2-circle", cls="bi me-1"), "Track syllabus coverage", type="submit", variant="outline-secondary", size="sm", cls="rounded-pill"),
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
            Span(badge_label, cls=f"badge rounded-pill bg-{tone}-subtle text-{tone} border border-{tone}-subtle px-3 py-1 fw-semibold"),
            P("School-wide record · staff progress is shared; an administrator confirms completed coverage.", cls="small text-muted mb-1 mt-2"),
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
        mode: str = "",
        output: str = "",
    ):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        classes, subjects, weeks, class_level, subject, scope_warnings = await _scope(
            req, class_level, subject, term
        )
        scope_notice = (
            f"{requested_subject} is not available for {class_level}. The subject has been changed to {subject or 'the first available subject'}; please confirm the scope before continuing."
            if (requested_subject := req.query_params.get("subject")) and requested_subject != subject
            else None
        )
        # Resolve scope first so an expired access token can refresh before the
        # independent workspace requests run concurrently.
        plans_data, summary_data, exercises_data, coverage_data = await asyncio.gather(
            _fetch_data(req, "/lesson-plans", source="lesson plans"),
            _fetch_data(req, "/lesson-plans/coverage/summary", source="coverage summary"),
            _fetch_data(req, "/lesson-plans/exercises", source="worksheets"),
            _fetch_data(req, "/lesson-plans/coverage", source="coverage records"),
        )
        plans, plans_warning = plans_data
        summary, summary_warning = summary_data
        exercises, exercises_warning = exercises_data
        coverage_rows, coverage_warning = coverage_data
        plans = plans if isinstance(plans, list) else []
        summary = summary if isinstance(summary, dict) else {"total": 0, "completed": 0, "verified": 0}
        exercises = exercises if isinstance(exercises, list) else []
        coverage_rows = coverage_rows if isinstance(coverage_rows, list) else []
        source_warnings = [
            warning for warning in (
                *scope_warnings, plans_warning, summary_warning,
                exercises_warning, coverage_warning,
            ) if warning
        ]

        select_cls = "border-0 rounded-3"
        select_style = "background:#F1F4F1;"
        scope_form = Form(
            Div(Label("Class", for_="class_level", cls="small fw-semibold text-muted mb-1"), Select("class_level", *[(c, c, c == class_level) for c in classes], cls=select_cls, style=select_style), cls="col-md-4"),
            Div(Label("Subject", for_="subject", cls="small fw-semibold text-muted mb-1"), Select("subject", *[(s.get("subject_name", ""), s.get("subject_name", ""), s.get("subject_name") == subject) for s in subjects], cls=select_cls, style=select_style), P("Subjects are based on the selected class. Changing class may reset this subject if it is not taught there.", cls="form-text small text-muted"), cls="col-md-5"),
            Div(Label("Term", for_="term", cls="small fw-semibold text-muted mb-1"), Select("term", *[(value, label, value == term) for label, value in _terms()], cls=select_cls, style=select_style), cls="col-md-3"),
            Div(Button("Refresh scheme", type="submit", variant="success", cls="rounded-pill px-4 btn-brand mt-3"), cls="col-12"),
            action="/app/teaching",
            method="get",
            cls="row g-3 align-items-end",
        )

        week_options = [
            (str(w.get("id")), f"Week {w.get('week_number')}: {w.get('topic', '')}", w.get("id") == (weeks[0].get("id") if weeks else None))
            for w in weeks
        ]
        selected_week = weeks[0] if weeks else {}
        create_form = Form(
            Input(type="hidden", name="curriculum_id", value=selected_week.get("curriculum_id", "")),
            Div(Label("Scheme week", for_="scheme_id", cls="small fw-semibold text-muted mb-1"), Select("scheme_id", *week_options, required=True, aria_describedby="scheme-week-help", cls=select_cls, style=select_style), P("Choose a teaching week. Open the topic list below to read the complete scheme wording.", id="scheme-week-help", cls="form-text small text-muted"), Details(Summary("Read full topics for this term", cls="small text-success fw-semibold"), Ul(*[Li(f"Week {w.get('week_number')}: {w.get('topic', '')}", cls="mb-1") for w in weeks], cls="small text-muted mb-0 ps-4") if weeks else P("No weeks are available for this scope.", cls="small text-muted mb-0"), cls="mt-2"), cls="col-12"),
            Div(Label("Plan title", for_="plan-title", cls="small fw-semibold text-muted mb-1"), Input(name="title", id="plan-title", required=True, value=f"{subject} · {term}", cls="form-control border-0 rounded-3", style="background:#F1F4F1;"), cls="col-12"),
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
        )
        active_plan = plans[0] if plans else {}
        question_fields = []
        for question_index in range(1, 5):
            question_fields.append(
                Div(
                    Strong(f"Question {question_index}", cls="small text-success d-block mb-2"),
                    Label("Question type", for_=f"exercise-type-{question_index}", cls="form-label small fw-semibold text-muted mb-1"),
                    Select(
                        f"question_type_{question_index}",
                        ("short_answer", "Short answer", True),
                        ("mcq", "Multiple choice"),
                        id=f"exercise-type-{question_index}",
                        cls="form-select form-select-sm mb-2",
                    ),
                    Label("Question", for_=f"exercise-question-{question_index}", cls="form-label small fw-semibold text-muted mb-1"),
                    Textarea(
                        name=f"question_text_{question_index}", id=f"exercise-question-{question_index}", rows="2",
                        maxlength="3000", aria_describedby=f"exercise-question-help-{question_index}",
                        placeholder="Write one clear question", cls="form-control mb-2",
                    ),
                    P("For multiple choice, enter 2–10 options, one per line below. Leave this question blank if you do not need it.", id=f"exercise-question-help-{question_index}", cls="form-text small text-muted mb-2"),
                    Label("Answer options (multiple choice only; one per line)", for_=f"exercise-options-{question_index}", cls="form-label small fw-semibold text-muted mb-1"),
                    Textarea(name=f"answer_options_{question_index}", id=f"exercise-options-{question_index}", rows="2", placeholder="Option A\nOption B", cls="form-control form-control-sm mb-2"),
                    Label("Marks", for_=f"exercise-marks-{question_index}", cls="form-label small fw-semibold text-muted mb-1"),
                    Input(type="number", name=f"question_marks_{question_index}", id=f"exercise-marks-{question_index}", value="1", min="1", max="100", cls="form-control form-control-sm mb-2"),
                    Label("Answer key / expected answer (staff only)", for_=f"exercise-key-{question_index}", cls="form-label small fw-semibold text-muted mb-1"),
                    Textarea(name=f"answer_key_{question_index}", id=f"exercise-key-{question_index}", rows="2", maxlength="3000", placeholder="Optional; not printed on the learner worksheet", cls="form-control form-control-sm"),
                    Button("Remove question", type="button", cls="btn btn-sm btn-link text-danger px-0 mt-2 remove-worksheet-question"),
                    cls="border rounded-3 p-3 mb-3 bg-light",
                    data_worksheet_question="true",
                    data_question_index=str(question_index),
                    role="group",
                    aria_label=f"Worksheet question {question_index}",
                )
            )

        exercise_form = Form(
            Input(type="hidden", name="lesson_plan_id", value=active_plan.get("id", "")),
            Div(Label("Exercise title", for_="exercise-title", cls="small fw-semibold text-muted mb-1"), Input(name="title", id="exercise-title", required=True, value=f"{subject} · Week {active_plan.get('week_number', 1)} practice", cls="form-control border-0 rounded-3", style="background:#F1F4F1;"), cls="col-12"),
            Div(
                Label("Instructions for learners", for_="exercise-instructions", cls="small fw-semibold text-muted mb-1"),
                Textarea(
                    name="instructions",
                    id="exercise-instructions",
                    rows="2",
                    placeholder="e.g. Answer all questions clearly in your exercise books. Marks are indicated against each question.",
                    cls="form-control border-0 rounded-3",
                    style="background:#F1F4F1; font-size: 0.88rem;",
                ),
                cls="col-12",
            ),
            Div(Label("Questions and marking guide", cls="small fw-semibold text-muted mb-1"), P("Add as many questions as needed (up to 20). Marks and optional answer keys are saved with the worksheet; answer keys are not printed for learners. For multiple choice, provide at least two options.", cls="form-text small text-muted"), Div(*question_fields, id="worksheet-question-list"), Button(Icon("plus-lg", cls="bi me-1"), "Add question", type="button", variant="outline-success", id="add-worksheet-question", cls="rounded-pill mb-3"), cls="col-12"),
            Div(Button(Icon("file-earmark-plus", cls="bi me-1"), "Create worksheet", type="submit", variant="success", cls="rounded-pill px-4 btn-brand", disabled=not bool(active_plan)), cls="col-12"),
            action="/app/teaching/exercises/create",
            method="post",
            cls="row g-3",
        )

        plans_view = Row(*[Col(_plan_card(p, user), span=12, md=6) for p in plans[:8]], g=3) if plans else Card(
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
            Card(Div(H2("Choose your teaching scope", cls="fs-5 fw-bold mb-3"), scope_form, cls="p-4"), cls="border-0 shadow-sm rounded-4 mb-4"),
            Row(
                Col(Card(Div(Span("SCHOOL COVERAGE RECORDS", cls="small text-muted fw-semibold"), Strong("—" if summary_warning else str(summary.get("total", 0)), cls="d-block fs-2 text-dark"), P("Tracked scheme weeks across the school", cls="small text-muted mb-0"), cls="p-3"), cls="border-0 shadow-sm rounded-4"), span=12, md=4),
                Col(Card(Div(Span("MARKED AS TAUGHT", cls="small text-muted fw-semibold"), Strong("—" if summary_warning else str(summary.get("completed", 0)), cls="d-block fs-2 text-success"), P("School records marked completed", cls="small text-muted mb-0"), cls="p-3"), cls="border-0 shadow-sm rounded-4"), span=12, md=4),
                Col(Card(Div(Span("CONFIRMED BY ADMIN", cls="small text-muted fw-semibold"), Strong("—" if summary_warning else str(summary.get("verified", 0)), cls="d-block fs-2 text-primary"), P("School records verified by an administrator", cls="small text-muted mb-0"), cls="p-3"), cls="border-0 shadow-sm rounded-4"), span=12, md=4),
                g=3,
                cls="mb-4",
            ),
            Div(Icon("exclamation-triangle", cls="bi me-2"), summary.get("warning"), cls="alert alert-warning rounded-4 border-0") if summary.get("warning") else None,
            Row(
                Col(Card(Div(H2("Build a weekly worksheet", cls="fs-5 fw-bold mb-3"), P("Turn a lesson plan into printable practice for learners.", cls="small text-muted mb-3"), exercise_form, cls="p-4"), cls="border-0 shadow-sm rounded-4"), span=12, lg=5),
                Col(Div(H2("Recent worksheets", cls="fs-5 fw-bold mb-3"), Row(*[Col(_exercise_card(item), span=12, md=6) for item in exercises[:6]], g=3) if exercises else P("Worksheets could not be loaded. Use Refresh scheme to try again." if exercises_warning else "Your exported worksheets will appear here.", cls="text-muted small")), span=12, lg=7),
                g=4,
                cls="mt-4",
            ),
            Card(
                Div(H2("Coverage progress", cls="fs-5 fw-bold mb-1"), P("This is a school-wide syllabus record, not a count of only your own lessons. Teachers update teaching progress; a school administrator confirms completed coverage.", cls="small text-muted mb-3"), Row(*[_coverage_card(row, user) for row in coverage_rows[:12]], g=3) if coverage_rows else P("Coverage records could not be loaded. Use Refresh scheme to try again." if coverage_warning else "No coverage records have been started by staff yet.", cls="text-muted small mb-0"), cls="p-4"),
                cls="border-0 shadow-sm rounded-4 mt-4",
            ),
            Row(
                Col(Card(Div(H2("Create a lesson plan", cls="fs-5 fw-bold mb-3"), P(f"Grounded in {subject or 'your selected subject'} · {term}.", cls="small text-muted mb-3"), create_form, cls="p-4"), cls="border-0 shadow-sm rounded-4"), span=12, lg=5),
                Col(Div(H2("Your teaching plans", cls="fs-5 fw-bold mb-3"), plans_view), span=12, lg=7),
                g=4,
            ),
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
          const questionList = document.getElementById('worksheet-question-list');
          const addQuestion = document.getElementById('add-worksheet-question');
          addQuestion?.addEventListener('click', () => {
            const rows = questionList?.querySelectorAll('[data-worksheet-question]') || [];
            if (!questionList || rows.length >= 20) return;
            const nextIndex = Math.max(0, ...Array.from(rows, (row) => Number(row.dataset.questionIndex) || 0)) + 1;
            if (nextIndex > 20) return;
            const clone = rows[0].cloneNode(true);
            clone.dataset.questionIndex = String(nextIndex);
            clone.setAttribute('aria-label', `Worksheet question ${nextIndex}`);
            const heading = clone.querySelector('strong');
            if (heading) heading.textContent = `Question ${nextIndex}`;
            clone.querySelectorAll('[id]').forEach((element) => { element.id = element.id.replace(/-[0-9]+$/, `-${nextIndex}`); });
            clone.querySelectorAll('[name]').forEach((field) => {
              const prefix = field.name.replace(/_[0-9]+$/, '');
              field.name = `${prefix}_${nextIndex}`;
              if (field.tagName === 'SELECT') field.selectedIndex = 0;
              else if (field.name.startsWith('question_marks_')) field.value = '1';
              else field.value = '';
            });
            clone.querySelectorAll('label[for]').forEach((label) => { label.htmlFor = label.htmlFor.replace(/-[0-9]+$/, `-${nextIndex}`); });
            clone.querySelectorAll('[aria-describedby]').forEach((element) => { element.setAttribute('aria-describedby', element.getAttribute('aria-describedby').replace(/-[0-9]+$/, `-${nextIndex}`)); });
            questionList.appendChild(clone);
            if (addQuestion) addQuestion.disabled = nextIndex >= 20;
            clone.querySelector('textarea')?.focus();
          });
          questionList?.addEventListener('click', (event) => {
            const remove = event.target.closest('.remove-worksheet-question');
            if (remove) {
              remove.closest('[data-worksheet-question]')?.remove();
              if (addQuestion) addQuestion.disabled = questionList.querySelectorAll('[data-worksheet-question]').length >= 20;
            }
          });
          questionList?.addEventListener('input', () => {
            if (addQuestion) addQuestion.disabled = questionList.querySelectorAll('[data-worksheet-question]').length >= 20;
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
        return RedirectResponse("/app/teaching", status_code=303)

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
        msg = f"AI lesson note updated ({guidance[:30]}...)." if guidance else "AI lesson note drafted from the scheme."
        push_flash(req, msg if ok else data.get("message", "Lesson note failed."), "success" if ok else "danger")
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
        push_flash(req, "Coverage tracking started for this week." if ok else data.get("message", "Could not start coverage."), "success" if ok else "danger")
        return RedirectResponse("/app/teaching", status_code=303)

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
        return RedirectResponse("/app/teaching", status_code=303)

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
            return RedirectResponse("/app/teaching", status_code=303)
        payload = {
            "lesson_plan_id": str(form.get("lesson_plan_id", "")),
            "title": str(form.get("title", "")),
            "instructions": str(form.get("instructions", "")) or None,
            "questions": questions,
        }
        resp = await call_api(req, "POST", "/lesson-plans/exercises", json=payload)
        ok, data = unwrap(resp)
        push_flash(req, "Weekly worksheet created." if ok else data.get("message", "Could not create worksheet."), "success" if ok else "danger")
        return RedirectResponse("/app/teaching", status_code=303)

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
            push_flash(req, "Could not export this lesson note. Save or generate it, then try again.", "danger")
            return RedirectResponse("/app/teaching", status_code=303)
        return Response(
            content=download_resp.content,
            media_type=download_resp.headers.get("content-type", "application/pdf"),
            headers={
                "Content-Disposition": f'attachment; filename="lesson-note-{safe_plan_id}.pdf"',
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
            push_flash(req, "Could not export this lesson note as Word. Save or generate it, then try again.", "danger")
            return RedirectResponse("/app/teaching", status_code=303)
        return Response(
            content=download_resp.content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="lesson-note-{safe_plan_id}.docx"',
                "Cache-Control": "private, no-store",
            },
        )
