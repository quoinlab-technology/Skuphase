"""Teacher-facing curriculum delivery workspace (Package B)."""

from urllib.parse import quote

from fasthtml.common import A, Div, Form, H1, H2, Input, Label, Option, P, Span, Strong, Textarea
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Button, Card, Col, Container, Icon, Row, Select

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import pop_flash, push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _terms() -> list[tuple[str, str]]:
    return [("First Term", "First Term"), ("Second Term", "Second Term"), ("Third Term", "Third Term")]


async def _scope(req: Request, class_level: str, subject: str, term: str):
    classes_resp = await call_api(req, "GET", "/curriculum/classes", params={"board": "NERDC"})
    ok_classes, classes_data = unwrap(classes_resp)
    classes = classes_data.get("classes", []) if ok_classes and isinstance(classes_data, dict) else []
    if not classes:
        classes = [class_level]
    if class_level not in classes:
        class_level = classes[0]

    subjects_resp = await call_api(req, "GET", "/curriculum/subjects", params={"class_level": class_level, "board": "NERDC"})
    ok_subjects, subjects_data = unwrap(subjects_resp)
    subjects = subjects_data.get("subjects", []) if ok_subjects and isinstance(subjects_data, dict) else []
    if not subject and subjects:
        subject = subjects[0].get("subject_name", "")
    if subjects and subject not in {item.get("subject_name") for item in subjects}:
        subject = subjects[0].get("subject_name", "")

    weeks_resp = await call_api(
        req,
        "GET",
        "/curriculum/weeks",
        params={"class_level": class_level, "subject": subject, "term": term},
    )
    ok_weeks, weeks_data = unwrap(weeks_resp)
    weeks = weeks_data.get("weeks", []) if ok_weeks and isinstance(weeks_data, dict) else []
    return classes, subjects, weeks, class_level, subject


def _status_badge(status: str) -> Span:
    tone = {"approved": "success", "submitted": "primary", "returned": "danger"}.get(status, "warning")
    return Span(status.replace("_", " ").title(), cls=f"badge rounded-pill bg-{tone}-subtle text-{tone} border border-{tone}-subtle px-3 py-2")


def _plan_card(plan: dict) -> Card:
    plan_id = plan.get("id", "")
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
                Form(
                    Input(type="hidden", name="lesson_plan_id", value=plan_id),
                    Button(Icon("sparkles", cls="bi me-1"), "Draft lesson note", type="submit", variant="outline-success", size="sm", cls="rounded-pill"),
                    action=f"/app/teaching/{plan_id}/lesson-note",
                    method="post",
                    cls="d-inline",
                ),
                Form(
                    Input(type="hidden", name="lesson_plan_id", value=plan_id),
                    Button(Icon("check2-circle", cls="bi me-1"), "Track coverage", type="submit", variant="outline-secondary", size="sm", cls="rounded-pill"),
                    action=f"/app/teaching/{plan_id}/coverage",
                    method="post",
                    cls="d-inline ms-2",
                ),
            ),
            cls="p-3",
        ),
        cls="border rounded-4 shadow-sm bg-white h-100",
    )


def teaching_routes(app):
    @app.get("/app/teaching")
    async def teaching_workspace(req: Request, class_level: str = "Primary 4", subject: str = "", term: str = "First Term"):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        classes, subjects, weeks, class_level, subject = await _scope(req, class_level, subject, term)
        plans_resp = await call_api(req, "GET", "/lesson-plans")
        ok_plans, plans_data = unwrap(plans_resp)
        plans = plans_data if ok_plans and isinstance(plans_data, list) else []
        summary_resp = await call_api(req, "GET", "/lesson-plans/coverage/summary")
        ok_summary, summary = unwrap(summary_resp)
        summary = summary if ok_summary and isinstance(summary, dict) else {"total": 0, "completed": 0, "verified": 0}

        scope_form = Form(
            Div(Label("Class", cls="small fw-semibold text-muted mb-1"), Select(*[Option(c, value=c, selected=c == class_level) for c in classes], name="class_level", cls="form-select border-0 rounded-3", style="background:#F1F4F1;"), cls="col-md-4"),
            Div(Label("Subject", cls="small fw-semibold text-muted mb-1"), Select(*[Option(s.get("subject_name", ""), value=s.get("subject_name", ""), selected=s.get("subject_name") == subject) for s in subjects], name="subject", cls="form-select border-0 rounded-3", style="background:#F1F4F1;"), cls="col-md-5"),
            Div(Label("Term", cls="small fw-semibold text-muted mb-1"), Select(*[Option(label, value=value, selected=value == term) for label, value in _terms()], name="term", cls="form-select border-0 rounded-3", style="background:#F1F4F1;"), cls="col-md-3"),
            Div(Button("Refresh scheme", type="submit", variant="success", cls="rounded-pill px-4 btn-brand mt-3"), cls="col-12"),
            action="/app/teaching",
            method="get",
            cls="row g-3 align-items-end",
        )

        week_options = [Option(f"Week {w.get('week_number')}: {w.get('topic', '')}", value=str(w.get("id"))) for w in weeks]
        selected_week = weeks[0] if weeks else {}
        create_form = Form(
            Input(type="hidden", name="curriculum_id", value=selected_week.get("curriculum_id", "")),
            Div(Label("Scheme week", cls="small fw-semibold text-muted mb-1"), Select(*week_options, name="scheme_id", required=True, cls="form-select border-0 rounded-3", style="background:#F1F4F1;"), cls="col-12"),
            Div(Label("Plan title", cls="small fw-semibold text-muted mb-1"), Input(name="title", required=True, value=f"{subject} · {term}", cls="form-control border-0 rounded-3", style="background:#F1F4F1;"), cls="col-12"),
            Div(Label("Activities", cls="small fw-semibold text-muted mb-1"), Textarea(name="activities", placeholder="One activity per line", rows="3", cls="form-control border-0 rounded-3", style="background:#F1F4F1;"), cls="col-md-6"),
            Div(Label("Assessment notes", cls="small fw-semibold text-muted mb-1"), Textarea(name="assessment_notes", placeholder="How will learners demonstrate understanding?", rows="3", cls="form-control border-0 rounded-3", style="background:#F1F4F1;"), cls="col-md-6"),
            Div(Button(Icon("plus-lg", cls="bi me-1"), "Create lesson plan", type="submit", variant="success", cls="rounded-pill px-4 btn-brand"), cls="col-12"),
            action="/app/teaching/create",
            method="post",
            cls="row g-3",
        )

        plans_view = Row(*[Col(_plan_card(p), span=12, md=6) for p in plans[:8]], g=3) if plans else Card(
            Div(
                Icon("journal-text", cls="bi fs-2 text-success mb-2"),
                P("No plans yet. Select a week above to create your first grounded lesson plan.", cls="text-muted small mb-0"),
                cls="p-4 text-center",
            ),
            cls="border-0 shadow-sm rounded-4",
        )

        content = Container(
            Div(
                Div(Span("PACKAGE B · CURRICULUM DELIVERY", cls="small fw-bold text-success letter-spacing-1"), H1("Teach from the scheme, week by week.", cls="fs-2 fw-bold text-dark mb-2 mt-2"), P("Turn the national curriculum into a practical lesson plan, an AI-assisted note, a weekly exercise, and verified coverage.", cls="text-muted mb-0"), cls="flex-grow-1"),
                A(Icon("book-half", cls="bi me-2"), "Browse curriculum", href="/app/curriculum", cls="btn btn-outline-success rounded-pill px-4 align-self-start"),
                cls="d-flex justify-content-between align-items-start gap-3 mb-4 flex-wrap",
            ),
            Card(Div(H2("Choose your teaching scope", cls="fs-5 fw-bold mb-3"), scope_form, cls="p-4"), cls="border-0 shadow-sm rounded-4 mb-4"),
            Row(
                Col(Card(Div(Span("PLANNED WEEKS", cls="small text-muted fw-semibold"), Strong(str(summary.get("total", 0)), cls="d-block fs-2 text-dark"), P("Coverage records", cls="small text-muted mb-0"), cls="p-3"), cls="border-0 shadow-sm rounded-4"), span=12, md=4),
                Col(Card(Div(Span("COMPLETED", cls="small text-muted fw-semibold"), Strong(str(summary.get("completed", 0)), cls="d-block fs-2 text-success"), P("Teacher-marked complete", cls="small text-muted mb-0"), cls="p-3"), cls="border-0 shadow-sm rounded-4"), span=12, md=4),
                Col(Card(Div(Span("VERIFIED", cls="small text-muted fw-semibold"), Strong(str(summary.get("verified", 0)), cls="d-block fs-2 text-primary"), P("Admin-confirmed coverage", cls="small text-muted mb-0"), cls="p-3"), cls="border-0 shadow-sm rounded-4"), span=12, md=4),
                g=3,
                cls="mb-4",
            ),
            Row(
                Col(Card(Div(H2("Create a lesson plan", cls="fs-5 fw-bold mb-3"), P(f"Grounded in {subject or 'your selected subject'} · {term}.", cls="small text-muted mb-3"), create_form, cls="p-4"), cls="border-0 shadow-sm rounded-4"), span=12, lg=5),
                Col(Div(H2("Your teaching plans", cls="fs-5 fw-bold mb-3"), plans_view), span=12, lg=7),
                g=4,
            ),
            cls="py-4 pt-lg-5",
        )
        return AppShell(content, user=user, active="teaching", crumbs=[("Teaching workspace", None)])

    @app.post("/app/teaching/create")
    async def create_plan(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        activities = [line.strip() for line in str(form.get("activities", "")).splitlines() if line.strip()]
        payload = {"curriculum_id": str(form.get("curriculum_id", "")), "scheme_id": str(form.get("scheme_id", "")), "title": str(form.get("title", "")), "activities": activities, "assessment_notes": str(form.get("assessment_notes", "")) or None}
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
        resp = await call_api(req, "POST", f"/lesson-plans/{plan_id}/lesson-note", json={"lesson_plan_id": plan_id})
        ok, data = unwrap(resp)
        push_flash(req, "AI lesson note drafted from the scheme." if ok else data.get("message", "Lesson note failed."), "success" if ok else "danger")
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
