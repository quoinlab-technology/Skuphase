"""Guided teacher entry point.

This is a simpler front door over the existing teaching and assessment
workflows. It deliberately does not duplicate those workflows: every action
links into the proven Advanced pages with the user's intent carried in the
query string for future progressive-disclosure work.
"""

from fasthtml.common import A, Div, H1, H2, P, Span, Strong
from starlette.requests import Request

from faststrap import Button, Card, Col, Container, Icon, Row

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


def guided_routes(app):
    @app.get("/app/start")
    async def guided_start(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        name = (user.get("full_name") or user.get("email") or "teacher").split()[0]

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
            Row(
                Col(
                    _task_card(
                        icon="journal-bookmark",
                        title="Prepare a lesson",
                        description="Choose a curriculum week, draft a lesson note, add activities and resources, then save it for teaching.",
                        href="/app/teaching?mode=guided&output=lesson",
                    ),
                    span=12,
                    md=4,
                ),
                Col(
                    _task_card(
                        icon="file-earmark-plus",
                        title="Create classwork",
                        description="Turn a lesson plan into a practical exercise or printable worksheet for your learners.",
                        href="/app/teaching?mode=guided&output=exercise",
                        tone="primary",
                    ),
                    span=12,
                    md=4,
                ),
                Col(
                    _task_card(
                        icon="lightning-charge",
                        title="Generate an exam",
                        description="Select curriculum topics, generate questions with AI, review them, and prepare the school paper.",
                        href="/app/exams/new?mode=guided",
                        tone="success",
                    ),
                    span=12,
                    md=4,
                ),
                g=3,
                cls="mb-4",
            ),
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
            cls="py-4 pt-lg-5",
        )
        return AppShell(content, user=user, active="start", crumbs=[("Start here", None)])
