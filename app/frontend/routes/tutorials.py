"""Tutorials and interactive guides hub for teachers and school administrators."""

from fasthtml.common import A, Div, H1, H2, H3, Img, P, Span, Strong, Title
from starlette.requests import Request

from faststrap import Badge, Card, Col, Icon, Row

from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _tutorial_step(
    num: int,
    title: str,
    description: str,
    desktop_img: str | None = None,
    mobile_img: str | None = None,
    tips: list[str] | None = None,
):
    step_id = f"step-{num}"
    
    img_component = None
    if desktop_img and mobile_img:
        img_component = Div(
            Div(
                # Tab buttons
                Div(
                    A(
                        Icon("laptop", cls="bi me-1"),
                        "Desktop View",
                        href=f"#{step_id}-desktop",
                        cls="btn btn-sm btn-outline-success rounded-pill active me-2",
                        **{
                            "data-bs-toggle": "pill",
                            "data-bs-target": f"#{step_id}-desktop",
                            "role": "tab",
                        },
                    ),
                    A(
                        Icon("phone", cls="bi me-1"),
                        "Mobile View",
                        href=f"#{step_id}-mobile",
                        cls="btn btn-sm btn-outline-success rounded-pill",
                        **{
                            "data-bs-toggle": "pill",
                            "data-bs-target": f"#{step_id}-mobile",
                            "role": "tab",
                        },
                    ),
                    cls="nav nav-pills mb-3",
                    role="tablist",
                ),
                # Tab content
                Div(
                    Div(
                        Img(
                            src=f"/assets/img/tutorials/{desktop_img}",
                            alt=f"{title} - Desktop",
                            cls="img-fluid rounded-3 border shadow-sm",
                            style="max-height: 480px; object-fit: contain; width: 100%;",
                        ),
                        id=f"{step_id}-desktop",
                        cls="tab-pane fade show active",
                        role="tabpanel",
                    ),
                    Div(
                        Div(
                            Img(
                                src=f"/assets/img/tutorials/{mobile_img}",
                                alt=f"{title} - Mobile",
                                cls="img-fluid rounded-3 border shadow-sm mx-auto d-block",
                                style="max-height: 520px; max-width: 340px; object-fit: contain;",
                            ),
                            cls="text-center bg-light p-3 rounded-3",
                        ),
                        id=f"{step_id}-mobile",
                        cls="tab-pane fade",
                        role="tabpanel",
                    ),
                    cls="tab-content",
                ),
            ),
            cls="mt-3",
        )
    elif desktop_img:
        img_component = Div(
            Img(
                src=f"/assets/img/tutorials/{desktop_img}",
                alt=title,
                cls="img-fluid rounded-3 border shadow-sm mt-3",
                style="max-height: 480px; object-fit: contain; width: 100%;",
            )
        )
    elif mobile_img:
        img_component = Div(
            Div(
                Img(
                    src=f"/assets/img/tutorials/{mobile_img}",
                    alt=title,
                    cls="img-fluid rounded-3 border shadow-sm mx-auto d-block",
                    style="max-height: 520px; max-width: 340px; object-fit: contain;",
                ),
                cls="text-center bg-light p-3 rounded-3 mt-3",
            )
        )

    tips_component = None
    if tips:
        tips_component = Div(
            *[
                P(
                    Icon("lightbulb-fill", cls="bi text-warning me-2"),
                    Span(tip),
                    cls="small mb-1 text-muted",
                )
                for tip in tips
            ],
            cls="mt-3 p-3 bg-light rounded-3 border-start border-success border-3",
        )

    return Div(
        Div(
            Span(f"Step {num}", cls="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3 py-1 mb-2"),
            H3(title, cls="h5 fw-bold text-dark mb-2"),
            P(description, cls="text-muted mb-0", style="line-height: 1.6;"),
            img_component if img_component else Div(),
            tips_component if tips_component else Div(),
            cls="p-4 bg-white rounded-4 border shadow-sm mb-4",
        )
    )


def register_routes(app):
    @app.get("/app/tutorials")
    async def tutorials_index(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}

        header = Div(
            H1("Tutorials & Guides", cls="h3 fw-bold text-dark mb-2"),
            P(
                "Step-by-step visual walkthroughs to help you master curriculum planning, AI drafting, and paper printing.",
                cls="text-muted mb-4",
            ),
            cls="mb-4",
        )

        overview_card = Card(
            Row(
                Col(
                    Div(
                        Badge("Visual Walkthrough", variant="success", pill=True, cls="mb-2"),
                        H2("How to Draft & Export a Lesson Note", cls="h4 fw-bold text-dark mb-2"),
                        P(
                            "Learn how to select your curriculum scope, generate an AI lesson note grounded in Nigerian curriculum standards, customize it with local classroom activities, and export print-ready PDF & Word documents with your school's logo.",
                            cls="text-muted mb-3",
                            style="line-height: 1.6;",
                        ),
                        Div(
                            A(
                                Icon("book-half", cls="bi me-2"),
                                "Read Guide",
                                href="/app/tutorials/lesson-note-workflow",
                                cls="btn btn-brand text-white rounded-pill px-4 me-2",
                            ),
                            Span("⏱ ~2 mins to read", cls="small text-muted align-self-center"),
                            cls="d-flex align-items-center flex-wrap gap-2",
                        ),
                        cls="p-4",
                    ),
                    span=12,
                    md=8,
                ),
                Col(
                    Div(
                        Img(
                            src="/assets/img/tutorials/01_teaching_workspace.png",
                            alt="Lesson Note Workspace",
                            cls="img-fluid rounded-3 border shadow-sm",
                            style="max-height: 220px; width: 100%; object-fit: cover;",
                        ),
                        cls="p-3 d-none d-md-block h-100",
                    ),
                    span=12,
                    md=4,
                ),
            ),
            cls="border-0 shadow-sm rounded-4 overflow-hidden mb-4",
            style="background: #F8FAF9;",
        )

        troubleshooting_card = Card(
            Div(
                H2("Quick Troubleshooting & FAQs", cls="h5 fw-bold text-dark mb-3"),
                Div(
                    Strong("Q: What if the lesson note shows empty or takes longer than expected?", cls="d-block text-dark small fw-bold mb-1"),
                    P("AI generation typically takes 20-30 seconds. If the page was refreshed or interrupted, simply click 'Regenerate draft' on your plan card. Your plan title and activities are safely kept.", cls="small text-muted mb-3"),
                    Strong("Q: Where does the school logo appear?", cls="d-block text-dark small fw-bold mb-1"),
                    P("Your uploaded school logo from School Settings is automatically embedded on all exported PDF and Word documents in the header masthead.", cls="small text-muted mb-3"),
                    Strong("Q: Can I edit the lesson note after the AI generates it?", cls="d-block text-dark small fw-bold mb-1"),
                    P("Yes! You can type directly in the draft box to add local materials (e.g. bottle caps, local market examples), then click 'Save & submit'.", cls="small text-muted mb-0"),
                    cls="p-4",
                ),
            ),
            cls="border rounded-4 bg-white shadow-sm mb-4",
        )

        content = Div(
            header,
            overview_card,
            troubleshooting_card,
            cls="container-fluid px-3 px-md-4 py-4",
            style="max-width: 1080px;",
        )

        return AppShell(
            Title("Tutorials — SkuPhase"),
            content,
            user=user,
            active="tutorials",
            crumbs=[("Tutorials", "/app/tutorials")],
        )

    @app.get("/app/tutorials/lesson-note-workflow")
    async def lesson_note_guide(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}

        header = Div(
            A(
                Icon("arrow-left", cls="bi me-1"),
                "Back to Tutorials",
                href="/app/tutorials",
                cls="text-decoration-none small text-success fw-medium mb-2 d-inline-block",
            ),
            H1("Generating a Lesson Note (Teacher Walkthrough)", cls="h3 fw-bold text-dark mb-2"),
            P(
                "A complete walkthrough from selecting your teaching scope to downloading a branded PDF or Word document for your classroom.",
                cls="text-muted mb-4",
            ),
            cls="mb-4",
        )

        steps = [
            _tutorial_step(
                1,
                "Open the Teaching Workspace",
                "Sign in and click 'Teaching' in the navigation bar. On mobile phones, open the menu (☰) at the top-left and choose 'Teaching'.",
                desktop_img="01_teaching_workspace.png",
                mobile_img="mobile_01_teaching_workspace.png",
                tips=[
                    "The Teaching workspace filters everything by Class, Subject, and Term. Check these selectors first before creating plans.",
                ],
            ),
            _tutorial_step(
                2,
                "Choose Your Scope (Class, Subject, Term)",
                "Pick your Class (e.g. Primary 4), Subject (e.g. Mathematics), and Term (e.g. First Term). Click 'Refresh scheme' to load the official NERDC curriculum scheme of work.",
                tips=[
                    "If you ever see a brief connection notification, pulling down to refresh or tapping 'Refresh scheme' reloads your saved selection safely.",
                ],
            ),
            _tutorial_step(
                3,
                "Fill in the Lesson Plan Form",
                "Select the scheme week from the dropdown, give your plan a title, and provide brief notes on learning activities, assessment checks, and local materials.",
                desktop_img="02_plan_form_filled.png",
                tips=[
                    "Include familiar local teaching materials (e.g. bundle sticks, chalkboard, Nigerian Naira coins/notes) to make the AI draft fit your classroom.",
                ],
            ),
            _tutorial_step(
                4,
                "Draft the Note with AI",
                "Once the plan card appears under 'Your teaching plans', tap 'Draft with AI'. The server generates a complete lesson note including objectives, starter, explanation, guided practice, assessment, and differentiation.",
                desktop_img="03_plan_card_draft_with_ai.png",
                tips=[
                    "AI generation takes approximately 20–30 seconds. Keep the tab open while the spinner is active.",
                    "If a draft is ever interrupted, simply tap 'Regenerate draft' to fetch a fresh note.",
                ],
            ),
            _tutorial_step(
                5,
                "Preview & Personalize Your Note",
                "Review the generated note. You can directly type inside the draft text area to add local notes or instructions. Tap 'Preview lesson note' to see the formatted output.",
                desktop_img="04_ai_lesson_note_generated.png",
                tips=[
                    "You can also use quick refinement chips (e.g. 'Nigerian context', 'Make shorter', 'Simplify language') to adjust the tone.",
                ],
            ),
            _tutorial_step(
                6,
                "Save & Submit for Review",
                "Tap 'Save & submit for review'. The card badge updates from 'Draft' to 'Submitted', and your notes are securely stored for school administration.",
                desktop_img="06_submitted_card_exports.png",
                mobile_img="mobile_02_submitted_card_note.png",
            ),
            _tutorial_step(
                7,
                "Export Clean PDF or Word Document",
                "Click 'Print / download PDF' or 'Download Word'. Your document downloads with your school's official masthead, logo, teacher name, term, and week ready for the staffroom printer.",
                desktop_img="06_submitted_card_exports.png",
                mobile_img="mobile_03_export_links.png",
                tips=[
                    "The exported document includes your configured school branding with no platform watermarks in the body.",
                ],
            ),
        ]

        content = Div(
            header,
            *steps,
            Div(
                A(
                    Icon("arrow-left", cls="bi me-2"),
                    "Return to Tutorials Overview",
                    href="/app/tutorials",
                    cls="btn btn-outline-secondary rounded-pill px-4",
                ),
                A(
                    Icon("journal-bookmark", cls="bi me-2"),
                    "Go to Teaching Workspace",
                    href="/app/teaching",
                    cls="btn btn-brand text-white rounded-pill px-4 ms-2",
                ),
                cls="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-3 pb-5",
            ),
            cls="container-fluid px-3 px-md-4 py-4",
            style="max-width: 960px;",
        )

        return AppShell(
            Title("Lesson Note Walkthrough — SkuPhase"),
            content,
            user=user,
            active="tutorials",
            crumbs=[("Tutorials", "/app/tutorials"), ("Lesson Note Guide", "/app/tutorials/lesson-note-workflow")],
        )
