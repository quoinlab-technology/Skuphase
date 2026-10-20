"""Tutorials and interactive guides hub for teachers and school administrators."""

from fasthtml.common import A, Code, Div, H1, H2, H3, Img, P, Span, Strong, Title
from starlette.requests import Request

from faststrap import Badge, Card, Col, Icon, Row

from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def _tutorial_step(
    num: int,
    title: str,
    description,
    desktop_img: str | None = None,
    mobile_img: str | None = None,
    tips: list[str] | None = None,
    action_link: tuple[str, str] | None = None,
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
                        A(
                            Img(
                                src=f"/assets/img/tutorials/{desktop_img}",
                                alt=f"{title} - Desktop",
                                cls="img-fluid rounded-3 border shadow-sm",
                                style="max-height: 480px; object-fit: contain; width: 100%; cursor: zoom-in;",
                            ),
                            href=f"/assets/img/tutorials/{desktop_img}",
                            target="_blank",
                            title="Click to view full image in new tab",
                        ),
                        id=f"{step_id}-desktop",
                        cls="tab-pane fade show active",
                        role="tabpanel",
                    ),
                    Div(
                        Div(
                            A(
                                Img(
                                    src=f"/assets/img/tutorials/{mobile_img}",
                                    alt=f"{title} - Mobile",
                                    cls="img-fluid rounded-3 border shadow-sm mx-auto d-block",
                                    style="max-height: 520px; max-width: 340px; object-fit: contain; cursor: zoom-in;",
                                ),
                                href=f"/assets/img/tutorials/{mobile_img}",
                                target="_blank",
                                title="Click to view full image in new tab",
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
            A(
                Img(
                    src=f"/assets/img/tutorials/{desktop_img}",
                    alt=title,
                    cls="img-fluid rounded-3 border shadow-sm mt-3",
                    style="max-height: 480px; object-fit: contain; width: 100%; cursor: zoom-in;",
                ),
                href=f"/assets/img/tutorials/{desktop_img}",
                target="_blank",
                title="Click to view full image in new tab",
            )
        )
    elif mobile_img:
        img_component = Div(
            Div(
                A(
                    Img(
                        src=f"/assets/img/tutorials/{mobile_img}",
                        alt=title,
                        cls="img-fluid rounded-3 border shadow-sm mx-auto d-block",
                        style="max-height: 520px; max-width: 340px; object-fit: contain; cursor: zoom-in;",
                    ),
                    href=f"/assets/img/tutorials/{mobile_img}",
                    target="_blank",
                    title="Click to view full image in new tab",
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

    action_btn = None
    if action_link:
        btn_text, btn_href = action_link
        action_btn = Div(
            A(
                Icon("arrow-right-circle", cls="bi me-2"),
                btn_text,
                href=btn_href,
                cls="btn btn-sm btn-outline-success rounded-pill px-3 mt-2",
            ),
            cls="mt-2",
        )

    return Div(
        Div(
            Span(f"Step {num}", cls="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3 py-1 mb-2"),
            H3(title, cls="h5 fw-bold text-dark mb-2"),
            P(description, cls="text-muted mb-0", style="line-height: 1.6;") if isinstance(description, str) else description,
            img_component if img_component else Div(),
            tips_component if tips_component else Div(),
            action_btn if action_btn else Div(),
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
                            src="/assets/img/tutorials/annotated/step1_teaching_workspace_annotated.png",
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

        exam_guide_card = Card(
            Row(
                Col(
                    Div(
                        Badge("Visual Walkthrough", variant="primary", pill=True, cls="mb-2"),
                        H2("How to Generate & Review an Exam with AI", cls="h4 fw-bold text-dark mb-2"),
                        P(
                            "Walk through the 4-step Generation Wizard, configure curriculum sections, select Bloom's taxonomy cognitive levels, monitor the live generation pipeline, review math formulas, and approve the paper for student printing.",
                            cls="text-muted mb-3",
                            style="line-height: 1.6;",
                        ),
                        Div(
                            A(
                                Icon("stars", cls="bi me-2"),
                                "Read Exam Guide",
                                href="/app/tutorials/exam-generation-workflow",
                                cls="btn btn-outline-success rounded-pill px-4 me-2",
                            ),
                            Span("⏱ ~3 mins to read", cls="small text-muted align-self-center"),
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
                            src="/assets/img/tutorials/annotated/exam_step1_scope_annotated.png",
                            alt="Exam Generation Wizard",
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

        bank_guide_card = Card(
            Row(
                Col(
                    Div(
                        Badge("Visual Walkthrough", variant="info", pill=True, cls="mb-2"),
                        H2("Question Bank & Manual Exam Builder", cls="h4 fw-bold text-dark mb-2"),
                        P(
                            "Learn how to create custom exams manually without AI, type questions with live KaTeX math formula previews, bookmark top exam questions into your school's shared Question Bank, and insert saved questions into new papers.",
                            cls="text-muted mb-3",
                            style="line-height: 1.6;",
                        ),
                        Div(
                            A(
                                Icon("book", cls="bi me-2"),
                                "Read Question Bank Guide",
                                href="/app/tutorials/question-bank-workflow",
                                cls="btn btn-outline-success rounded-pill px-4 me-2",
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
                            src="/assets/img/tutorials/annotated/bank_step2_math_annotated.png",
                            alt="Question Bank & Math",
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

        admin_guide_card = Card(
            Row(
                Col(
                    Div(
                        Badge("Admin & Setup", variant="warning", pill=True, cls="mb-2"),
                        H2("School Setup, Branding & Staff Invites", cls="h4 fw-bold text-dark mb-2"),
                        P(
                            "A step-by-step guide for School Principals and Administrators: upload your official school crest/logo, customize exam headers, configure terms, invite subject teachers with custom roles, and oversee teaching coverage.",
                            cls="text-muted mb-3",
                            style="line-height: 1.6;",
                        ),
                        Div(
                            A(
                                Icon("gear-wide-connected", cls="bi me-2"),
                                "Read Admin Guide",
                                href="/app/tutorials/school-setup-workflow",
                                cls="btn btn-outline-success rounded-pill px-4 me-2",
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
                            src="/assets/img/tutorials/annotated/admin_step1_branding_annotated.png",
                            alt="Admin & Dashboard Setup",
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
            exam_guide_card,
            bank_guide_card,
            admin_guide_card,
            troubleshooting_card,
            cls="container py-4",
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
                "Sign in and click 'Teaching' in the navigation bar. On mobile phones, tap the menu (☰) in the bottom navigation bar and select 'Teaching'.",
                desktop_img="annotated/step1_teaching_workspace_annotated.png",
                mobile_img="annotated/mobile_step1_scope_annotated.png",
                tips=[
                    "See Callout ① pointing to 'Teaching' in the sidebar navigation.",
                    "See Callout ② highlighting the 'Choose your teaching scope' card where your active class, subject, and term are configured.",
                ],
                action_link=("Open Teaching Workspace", "/app/teaching"),
            ),
            _tutorial_step(
                2,
                "Choose Your Scope & Fill Lesson Plan Form",
                "Pick your Class (e.g. Primary 4), Subject (e.g. Mathematics), and Term (e.g. First Term). Then select the scheme week, title your lesson, and outline learning activities.",
                desktop_img="annotated/step2_plan_form_annotated.png",
                tips=[
                    "See Callout ①: Select your teaching week from the Scheme week dropdown.",
                    "See Callout ②: Tap the green '+ Create lesson plan' button when your details and local instructional materials are filled.",
                ],
            ),
            _tutorial_step(
                3,
                "Draft the Note with AI",
                "Once the plan card appears under 'Your teaching plans', tap 'Draft with AI'. SkuPhase generates a complete lesson note grounded in Nigerian curriculum standards.",
                desktop_img="annotated/step3_draft_with_ai_annotated.png",
                tips=[
                    "See Callout ① showing the 'Draft' badge for your newly created lesson plan.",
                    "See Callout ② pointing to the green 'Draft with AI' button. AI drafting takes roughly 20–30 seconds.",
                ],
            ),
            _tutorial_step(
                4,
                "Preview & Personalize Your Note",
                "Review the generated note. You can directly edit the draft or tap quick refinement chips to tailor the content for your classroom.",
                desktop_img="annotated/step4_preview_annotated.png",
                tips=[
                    "See Callout ①: Tap quick refinement buttons like '🌍 Nigerian Context' or '✂ Make Shorter' to instantly adapt the tone.",
                    "See Callout ②: Click 'Preview lesson note' to see full mathematical and formatted output before submitting.",
                ],
            ),
            _tutorial_step(
                5,
                "Save & Submit for Review",
                "When your lesson note looks great, click 'Save & submit for review'. The card status flips to 'Submitted', keeping your record safe for academic audits.",
                desktop_img="annotated/step5_submit_exports_annotated.png",
                mobile_img="annotated/mobile_step2_submit_annotated.png",
                tips=[
                    "See Callout ① pointing to 'Save & submit for review'.",
                    "On mobile devices, Callout ① highlights the green 'Submit' button, and Callout ② indicates the download icons.",
                ],
            ),
            _tutorial_step(
                6,
                "Export Clean PDF or Word Document",
                "Download your lesson note for classroom use. The exported document is formatted with your school's official masthead and logo.",
                desktop_img="annotated/step5_submit_exports_annotated.png",
                mobile_img="annotated/mobile_step3_export_annotated.png",
                tips=[
                    "See Callout ② for 'Print / download PDF' and Callout ③ for 'Download Word'.",
                    "On mobile screens, Callout ① shows export options and Callout ② shows 'Regenerate draft' if you ever need a fresh draft.",
                ],
                action_link=("Configure School Logo in Settings", "/app/settings"),
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
            cls="container py-4",
        )

        return AppShell(
            Title("Lesson Note Walkthrough — SkuPhase"),
            content,
            user=user,
            active="tutorials",
            crumbs=[("Tutorials", "/app/tutorials"), ("Lesson Note Guide", "/app/tutorials/lesson-note-workflow")],
        )

    @app.get("/app/tutorials/exam-generation-workflow")
    async def exam_generation_guide(req: Request):
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
            H1("Generating & Printing an Exam Paper (AI Walkthrough)", cls="h3 fw-bold text-dark mb-2"),
            P(
                "A complete guide to configuring your exam parameters, launching AI generation, reviewing formulas, and exporting student-ready exam papers.",
                cls="text-muted mb-4",
            ),
            cls="mb-4",
        )

        steps = [
            _tutorial_step(
                1,
                "Start the AI Exam Generator",
                "From your dashboard or exams page, click 'Generate with AI'. This launches the 4-step generation wizard designed specifically around the NERDC curriculum.",
                desktop_img="annotated/exam_step1_scope_annotated.png",
                tips=[
                    "See Callout ① indicating the 4-step wizard progress bar (Scope, Curriculum, Structure, Confirm).",
                    "See Callout ② for the Exam Title field.",
                    "See Callout ③ pointing to the 'Next' button to proceed.",
                ],
                action_link=("Launch Exam Wizard", "/app/exams/new"),
            ),
            _tutorial_step(
                2,
                "Verify Curriculum Grounding & Bloom Levels",
                "Choose how many sections your exam will have (e.g. Section A: Multiple Choice, Section B: Theory). Configure marks and select Bloom's taxonomy cognitive levels.",
                desktop_img="annotated/exam_step2_curriculum_annotated.png",
                tips=[
                    "See Callout ①: SkuPhase checks your topics against the NERDC curriculum scheme.",
                    "See Callout ②: Select Bloom's Taxonomy cognitive levels (Remember, Understand, Apply, Analyse).",
                    "See Callout ③: Tap 'Next' to move to Structure configuration.",
                ],
            ),
            _tutorial_step(
                3,
                "Confirm & Launch Generation",
                "Review your parameters on the confirmation step, then tap 'Generate Exam'. The backend will enqueue the generation job and begin AI drafting.",
                desktop_img="annotated/exam_step3_confirm_annotated.png",
                tips=[
                    "See Callout ①: Review all question breakdown counts and duration parameters in the summary card.",
                    "See Callout ②: Tap 'Generate Exam' to launch the background AI generation pipeline.",
                ],
            ),
            _tutorial_step(
                4,
                "Monitor Generation Progress",
                "While the exam is generating, the live progress screen keeps you updated. Generation typically finishes in under 60 seconds.",
                desktop_img="annotated/exam_step4_progress_annotated.png",
                tips=[
                    "See Callout ①: Live status spinner indicating server-side question synthesis.",
                    "See Callout ②: Real-time progress items tracking grounding, drafting, and quality check phases.",
                ],
            ),
            _tutorial_step(
                5,
                "Review Questions & Math Formulas",
                "Once generated, inspect each question. SkuPhase renders KaTeX equations (e.g. fractions, square roots, matrices) cleanly for both screen and print.",
                desktop_img="annotated/exam_step5_review_annotated.png",
                tips=[
                    "See Callout ①: Click 'Approve' when satisfied with the paper.",
                    "See Callout ②: Toggle 'Show answers & explanations' to reveal solution keys and grading criteria.",
                    "See Callout ③: Each question card clearly displays mark distribution, question type, and KaTeX math formatting.",
                ],
            ),
            _tutorial_step(
                6,
                "Approve and Print Student Paper",
                "When approved, you can print clean student question papers with your official school header or download master answer keys.",
                desktop_img="annotated/exam_step6_approved_annotated.png",
                tips=[
                    "See Callout ① confirming the green 'Approved' status.",
                    "See Callout ②: Tap 'Print / Save Student Paper' to launch the print preview.",
                ],
                action_link=("View Your Exams List", "/app/exams"),
            ),
            _tutorial_step(
                7,
                "Duplication-Ready Student Printout",
                "The print preview formats the paper cleanly in 2-column eco mode, perfect for photocopying without wasted paper or platform watermarks.",
                desktop_img="annotated/exam_step6_print_annotated.png",
                tips=[
                    "See Callout ①: Click 'Print Exam Paper (2-Col Eco Mode)' to send directly to your printer or save as PDF.",
                    "See Callout ②: Official school header is embedded at the top with student name and date lines.",
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
                    Icon("stars", cls="bi me-2"),
                    "Generate an Exam Now",
                    href="/app/exams/new",
                    cls="btn btn-brand text-white rounded-pill px-4 ms-2",
                ),
                cls="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-3 pb-5",
            ),
            cls="container py-4",
        )

        return AppShell(
            Title("Exam Generation Walkthrough — SkuPhase"),
            content,
            user=user,
            active="tutorials",
            crumbs=[("Tutorials", "/app/tutorials"), ("Exam Generation Guide", "/app/tutorials/exam-generation-workflow")],
        )

    @app.get("/app/tutorials/question-bank-workflow")
    async def question_bank_guide(req: Request):
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
            H1("Using the Question Bank & Manual Exam Builder", cls="h3 fw-bold text-dark mb-2"),
            P(
                "Learn how to manually create custom exam papers without AI, write KaTeX formulas, and reuse top questions across your school's Question Bank.",
                cls="text-muted mb-4",
            ),
            cls="mb-4",
        )

        steps = [
            _tutorial_step(
                1,
                "Access the Manual Exam Creator",
                "When you already have a past examination paper or specific exam questions to type in directly, click 'Manual Exam' on the Exams workspace.",
                tips=[
                    "Manual exams bypass the AI generation queue, creating an editable draft immediately.",
                ],
                action_link=("Start a Manual Exam", "/app/exams/new/manual"),
            ),
            _tutorial_step(
                2,
                "Format Questions with Math Delimiters",
                P(
                    "Type question text and options. Wrap inline math in single dollar signs — e.g. ",
                    Code("$x^2 + y^2 = r^2$"),
                    " — or block equations in double dollar signs — e.g. ",
                    Code(r"$$rac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$"),
                    " — and SkuPhase will render them instantly.",
                    cls="text-muted mb-0",
                    style="line-height: 1.6;",
                ),
                desktop_img="annotated/bank_step2_math_annotated.png",
                tips=[
                    "See Callout ①: Question cards render equations with live KaTeX formatting for both screen and print.",
                ],
            ),
            _tutorial_step(
                3,
                "Bookmark Verified Questions to the School Bank",
                "On any approved or reviewed exam detail page, open the question's action menu (⋮) and tap 'Save to Question Bank'.",
                desktop_img="annotated/bank_step3_bookmark_annotated.png",
                tips=[
                    "See Callout ①: Tap the three-dot (⋮) menu button in the top action bar to bookmark verified questions into your school's private bank.",
                ],
            ),
            _tutorial_step(
                4,
                "Browse and Filter the Question Bank",
                "Go to 'Bank' in the main navigation. You can filter questions by Subject, Class Level, Difficulty (Easy, Medium, Hard), and Type (MCQ, Short Answer, Essay).",
                tips=[
                    "Teachers can quickly search by keywords or topic names to assemble quick weekly revision tests.",
                ],
                action_link=("Explore Question Bank", "/app/bank"),
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
                    Icon("book", cls="bi me-2"),
                    "Open Question Bank",
                    href="/app/bank",
                    cls="btn btn-brand text-white rounded-pill px-4 ms-2",
                ),
                cls="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-3 pb-5",
            ),
            cls="container py-4",
        )

        return AppShell(
            Title("Question Bank Guide — SkuPhase"),
            content,
            user=user,
            active="tutorials",
            crumbs=[("Tutorials", "/app/tutorials"), ("Question Bank Guide", "/app/tutorials/question-bank-workflow")],
        )

    @app.get("/app/tutorials/school-setup-workflow")
    async def school_setup_guide(req: Request):
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
            H1("School Setup, Branding & Staff Invites (Admin Guide)", cls="h3 fw-bold text-dark mb-2"),
            P(
                "A visual guide for School Principals & Administrators to configure your school identity, upload custom logos, and invite teaching staff.",
                cls="text-muted mb-4",
            ),
            cls="mb-4",
        )

        steps = [
            _tutorial_step(
                1,
                "Configure School Profile & Upload Official Crest",
                "From your admin dashboard, locate the 'School Branding & Exam Settings' banner to upload your school's logo or crest and configure exam mastheads.",
                desktop_img="annotated/admin_step1_branding_annotated.png",
                tips=[
                    "See Callout ①: The 'School Branding & Exam Settings' overview banner on the dashboard.",
                    "See Callout ②: Click 'Configure School Profile' to upload your PNG or JPEG crest and set postal addresses.",
                    "Your uploaded logo automatically embeds in all exported lesson notes and exam headers.",
                ],
                action_link=("Go to School Settings", "/app/settings"),
            ),
            _tutorial_step(
                2,
                "Verify Active School & Role Switcher",
                "If you manage multiple school branches or need to toggle between Teacher and Admin views, use the header selector pills.",
                desktop_img="annotated/admin_step2_settings_annotated.png",
                tips=[
                    "See Callout ①: Role indicator (School Admin) showing administrative permissions.",
                    "See Callout ②: School switcher (Impath Academy) allowing multi-branch administrators to toggle campuses.",
                ],
            ),
            _tutorial_step(
                3,
                "Manage Staff & Roles in Administration",
                "Click 'Administration' in the left sidebar to manage staff accounts, invite teachers, and configure role-based access.",
                desktop_img="annotated/admin_step3_staff_annotated.png",
                tips=[
                    "See Callout ① pointing to 'Administration' at the bottom of the navigation menu.",
                    "Invited teachers receive email credentials and immediately get access to curriculum schemes and the Question Bank.",
                ],
                action_link=("Manage School Staff", "/app/staff"),
            ),
            _tutorial_step(
                4,
                "Track Syllabus Delivery & Coverage",
                "Principals can review the Teaching workspace coverage tracker to see weekly curriculum completion progress across all primary and secondary arms.",
                desktop_img="annotated/admin_step4_coverage_annotated.png",
                tips=[
                    "See Callout ① highlighting the 'Coverage progress' status section.",
                    "See Callout ②: Detailed records list showing Planned vs. Teacher-completed vs. Admin-verified weekly curriculum delivery.",
                ],
                action_link=("View Coverage Progress", "/app/teaching?show_coverage=true"),
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
                    Icon("gear", cls="bi me-2"),
                    "Go to Settings",
                    href="/app/settings",
                    cls="btn btn-brand text-white rounded-pill px-4 ms-2",
                ),
                cls="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-3 pb-5",
            ),
            cls="container py-4",
        )

        return AppShell(
            Title("School Setup & Admin Guide — SkuPhase"),
            content,
            user=user,
            active="tutorials",
            crumbs=[("Tutorials", "/app/tutorials"), ("Admin Guide", "/app/tutorials/school-setup-workflow")],
        )
