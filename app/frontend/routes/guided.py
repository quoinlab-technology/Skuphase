"""Guided teacher entry point.

This is a simpler front door over the existing teaching and assessment
workflows. It deliberately does not duplicate those workflows: every action
links into the proven Advanced pages with the user's intent carried in the
query string for future progressive-disclosure work.
"""

from urllib.parse import quote

from fasthtml.common import A, Div, Form, H1, H2, Label, P, Span, Strong
from starlette.requests import Request

from faststrap import Button, Card, Col, Container, Icon, Row, Select

from app.frontend.api import call_api, unwrap
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _task_card(*, icon: str, title: str, description: str, href: str, tone: str = "success") -> Card:
    return Card(
        Div(
            Div(
                Icon(icon, cls=f"bi fs-4 text-{tone}"),
                cls=f"guided-task-icon bg-{tone}-subtle",
            ),
            H2(title, cls="fs-5 fw-bold text-dark mb-2 mt-3"),
            P(description, cls="text-muted small mb-4"),
            A(
                "Start here",
                Icon("arrow-right", cls="bi ms-2"),
                href=href,
                cls=f"btn btn-outline-{tone} rounded-pill px-3 stretched-link",
            ),
            cls="p-4 h-100 d-flex flex-column",
        ),
        cls="border-0 shadow-sm rounded-4 h-100 guided-task-card",
    )


def _terms() -> list[tuple[str, str]]:
    return [("First Term", "First Term"), ("Second Term", "Second Term"), ("Third Term", "Third Term")]


async def _scope_options(req: Request, class_level: str, subject: str):
    classes_resp = await call_api(req, "GET", "/curriculum/classes", params={"board": "NERDC"})
    ok_classes, classes_data = unwrap(classes_resp)
    classes = classes_data.get("classes", []) if ok_classes and isinstance(classes_data, dict) else []
    classes = classes or ["Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6"]
    if class_level not in classes:
        class_level = classes[0]

    subjects_resp = await call_api(req, "GET", "/curriculum/subjects", params={"class_level": class_level, "board": "NERDC"})
    ok_subjects, subjects_data = unwrap(subjects_resp)
    subjects = subjects_data.get("subjects", []) if ok_subjects and isinstance(subjects_data, dict) else []
    subject_names = [item.get("subject_name", "") for item in subjects if item.get("subject_name")]
    subject_names = subject_names or ["Mathematics", "English Language", "Basic Science"]
    if subject not in subject_names:
        subject = subject_names[0]
    return classes, subject_names, class_level, subject


def _context_form(classes: list[str], subjects: list[str], class_level: str, subject: str, term: str) -> Form:
    return Form(
        Div(
            Label("Class", cls="small fw-semibold text-muted mb-1"),
            Select("class_level", *[(item, item, item == class_level) for item in classes], cls="form-select border-0 rounded-3", style="background:#F1F4F1;"),
            cls="col-12 col-md-4",
        ),
        Div(
            Label("Subject", cls="small fw-semibold text-muted mb-1"),
            Select("subject", *[(item, item, item == subject) for item in subjects], cls="form-select border-0 rounded-3", style="background:#F1F4F1;"),
            cls="col-12 col-md-5",
        ),
        Div(
            Label("Term", cls="small fw-semibold text-muted mb-1"),
            Select("term", *[(value, label, value == term) for label, value in _terms()], cls="form-select border-0 rounded-3", style="background:#F1F4F1;"),
            cls="col-12 col-md-3",
        ),
        Div(Button("Use this context", type="submit", variant="success", cls="rounded-pill px-4 btn-brand"), cls="col-12 mt-1"),
        action="/app/start",
        method="get",
        cls="row g-3 align-items-end",
    )


def _output_href(output: str, class_level: str, subject: str, term: str) -> str:
    context = f"class_level={quote(class_level)}&subject={quote(subject)}&term={quote(term)}"
    if output == "lesson":
        return f"/app/teaching?mode=guided&output=lesson&{context}"
    if output == "exercise":
        return f"/app/teaching?mode=guided&output=exercise&{context}"
    if output == "exam":
        return f"/app/exams/new?mode=guided&{context}"
    return f"/app/exams?status=under_review&grade={quote(class_level)}&subject={quote(subject)}&mode=guided&output=review"


def guided_routes(app):
    @app.get("/app/start")
    async def guided_start(
        req: Request,
        class_level: str = "Primary 4",
        subject: str = "",
        term: str = "First Term",
        output: str = "",
    ):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        name = (user.get("full_name") or user.get("email") or "teacher").split()[0]
        classes, subjects, class_level, subject = await _scope_options(req, class_level, subject)
        output_labels = {"lesson": "Lesson note", "exercise": "Classwork", "exam": "Examination", "review": "Review and export"}
        output_label = output_labels.get(output)

        context_card = Card(
            Div(
                H2("1. Set your teaching context", cls="fs-5 fw-bold mb-1"),
                P("SkuPhase will keep this class, subject, and term with the work you create.", cls="small text-muted mb-3"),
                _context_form(classes, subjects, class_level, subject, term),
                cls="p-4",
            ),
            cls="border-0 shadow-sm rounded-4 mb-4",
        )

        output_choices = Row(
            Col(_task_card(icon="journal-bookmark", title="Prepare a lesson", description="Draft a curriculum-grounded lesson note with activities and resources.", href=_output_href("lesson", class_level, subject, term)), span=12, md=6, lg=3),
            Col(_task_card(icon="file-earmark-plus", title="Create classwork", description="Turn the selected context into a practical exercise or worksheet.", href=_output_href("exercise", class_level, subject, term), tone="primary"), span=12, md=6, lg=3),
            Col(_task_card(icon="lightning-charge", title="Create an exam", description="Generate curriculum-aligned questions and review them before export.", href=_output_href("exam", class_level, subject, term)), span=12, md=6, lg=3),
            Col(_task_card(icon="check2-square", title="Review and export", description="Return to drafts and submitted work that needs your attention.", href=_output_href("review", class_level, subject, term), tone="secondary"), span=12, md=6, lg=3),
            g=3,
            cls="mb-4",
        )

        content = Container(
            Div(
                Div(
                    Span("GUIDED MODE", cls="small fw-bold text-success letter-spacing-1"),
                    H1(f"What are you preparing today, {name}?", cls="fs-2 fw-bold text-dark mb-2 mt-2"),
                    P(
                        "Choose one task and SkuPhase will take you into the right workspace. Your advanced tools remain available whenever you need them.",
                        cls="text-muted mb-0",
                    ),
                    cls="flex-grow-1",
                ),
                A(
                    Icon("sliders2", cls="bi me-2"),
                    "Open Advanced workspace",
                    href="/app/teaching?mode=advanced",
                    cls="btn btn-outline-secondary rounded-pill px-4 align-self-start d-none d-sm-inline-flex",
                ),
                cls="d-flex justify-content-between align-items-start gap-3 mb-4 flex-wrap",
            ),
            context_card,
            Div(H2("2. What would you like to create?", cls="fs-5 fw-bold mb-3"), output_choices),
            Card(
                Div(
                    Strong(f"Selected context: {class_level} · {subject} · {term}", cls="d-block text-dark"),
                    P(
                        f"Next: continue with {output_label.lower()}." if output_label else "Choose one output above. You can still open the full Advanced workspace at any time.",
                        cls="small text-muted mb-0",
                    ),
                    cls="p-3",
                ),
                cls="border-0 shadow-sm rounded-4 mb-4 bg-white",
            ) if output_label else None,
            Card(
                Div(
                    Div(
                        Icon("compass", cls="bi fs-4 text-success"),
                        cls="guided-help-icon me-3",
                    ),
                    Div(
                        Strong("Not sure where to begin?", cls="d-block text-dark"),
                        P(
                            "Browse the curriculum first, then choose a week. SkuPhase will keep the class, subject, term, and topic together as you continue.",
                            cls="text-muted small mb-0",
                        ),
                    ),
                    A(
                        "Browse curriculum",
                        Icon("arrow-right", cls="bi ms-2"),
                        href="/app/curriculum",
                        cls="btn btn-outline-success rounded-pill px-3 ms-auto flex-shrink-0",
                    ),
                    cls="p-4 d-flex align-items-center gap-2 flex-wrap",
                ),
                cls="border-0 shadow-sm rounded-4",
            ),
            Div(
                P(
                    "Advanced users can continue using the full manual editor, blueprints, diagrams, formulas, approval tools, and export controls from the existing workspaces.",
                    cls="small text-muted text-center mb-0",
                ),
                cls="mt-4 mb-2",
            ),
            cls="py-4 pt-lg-5 guided-page",
        )
        return AppShell(content, user=user, active="start", crumbs=[("Start here", None)])
