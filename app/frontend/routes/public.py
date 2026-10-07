from fasthtml.common import A, Div, Form, H1, H2, H3, Input, Label, Li, Option, P, Select, Span, Strong, Textarea, Title, Ul
from starlette.requests import Request
from starlette.responses import RedirectResponse

from faststrap import Alert, Button, Card, Col, Container, Icon, Row

from app.frontend.components.layout import PublicShell


def home():
    """Landing page matching prototype screenshot:

    - Hero: "Generate Better Exams, Faster", badge "Built for Nigerian Primary Education",
      subtitle, "Start Free >" and "Book Demo" CTAs, 3 trust indicators.
    - Features: the real curriculum-first capabilities of the platform.
    - Workflow: from curriculum scope to an exam-ready paper.
    - Pricing: "Simple, transparent pricing", 3 tier cards: Starter (Free), Academy (₦25,000/mo, featured dark green), Enterprise (Custom).
    - FAQ: "Frequently asked questions", 5 clean cards.
    - CTA Banner: "Ready to transform your exam workflow?", graduation cap icon, dark green background.
    """
    return PublicShell(
        Title("SkuPhase — Curriculum-Aligned Nigerian Primary School Exam Generator"),
        # 1. Hero Section (Full-width pale sage background #E6ECE5)
        Div(
            Container(
                Div(
                    # Pill Tag matching prototype: outline star + exact copy
                    Div(
                        Span(
                            Icon("star", cls="bi me-2 small"),
                            "Built for Nigerian schools",
                            cls="badge rounded-pill px-3 py-2 fw-medium ",
                            style="background-color: rgba(0, 65, 46, 0.08); color: #00412E; border: 1px solid rgba(0, 65, 46, 0.18); font-size: 0.82rem; letter-spacing: 0.01em;",
                        ),
                        cls="mb-4 text-center",
                    ),
                    # H1 Headline matching prototype
                    H1(
                        "Generate Better Exams, Faster",
                        cls="fw-bold text-center mb-4",
                        style="font-size: clamp(2.6rem, 5.5vw, 4.2rem); color: #00412E; letter-spacing: -0.03em; line-height: 1.1; font-weight: 800;",
                    ),
                    # Subtitle: 3-line centered block
                    P(
                        "SkuPhase uses AI to generate high-quality, curriculum-aligned ",
                        "examinations from the official NERDC curriculum — with human review, ",
                        "quality checks, and clean print-ready exports.",
                        cls="text-center mb-4 pb-2",
                        style="font-size: 1.15rem; color: #475569; max-width: 680px; margin: 0 auto; line-height: 1.65;",
                    ),
                    # CTAs: Pill Start Free -> + Rounded Rectangle Book Demo
                    Div(
                        Button(
                            "Start Free",
                            Span(" →", cls="ms-1 fw-bold"),
                            as_="a",
                            href="/register",
                            variant="success",
                            size="md",
                            cls="btn-brand rounded-pill px-4 py-3 fw-semibold text-white shadow-sm text-decoration-none",
                            style="background-color: #00412E !important; border-color: #00412E !important; padding: 12px 28px !important;",
                        ),
                        Button(
                            "Book Demo",
                            as_="a",
                            href="/contact",
                            size="md",
                            cls="btn bg-white text-dark fw-semibold shadow-sm text-decoration-none",
                            style="padding: 12px 28px !important; border: 1px solid rgba(0, 0, 0, 0.14) !important; border-radius: 10px !important;",
                        ),
                        cls="d-flex justify-content-center align-items-center flex-wrap gap-3 mb-5",
                    ),
                    # 3 Trust Indicators matching prototype
                    Div(
                        Span(
                            Icon("check-circle", cls="bi me-2 text-dark opacity-75"),
                            "No credit card required",
                            cls="small fw-medium",
                            style="color: #475569;",
                        ),
                        Span(
                            Icon("check-circle", cls="bi me-2 text-dark opacity-75"),
                            "NERDC-aligned output",
                            cls="small fw-medium",
                            style="color: #475569;",
                        ),
                        Span(
                            Icon("check-circle", cls="bi me-2 text-dark opacity-75"),
                            "Setup in 30 minutes",
                            cls="small fw-medium",
                            style="color: #475569;",
                        ),
                        cls="d-flex justify-content-center align-items-center flex-wrap gap-4 gap-md-5",
                    ),
                    cls="py-5 my-2",
                ),
                style="max-width: 1080px;",
            ),
            style="background-color: #E6ECE5; padding-top: 3.5rem; padding-bottom: 4.5rem;",
            cls="w-100 border-bottom",
        ),

        # 2. Features: "Everything your school needs for exam excellence"
        Container(
            Div(
                Div(
                    H2("Everything your school needs for exam excellence", cls="fw-bold text-center text-dark mb-2", style="letter-spacing: -0.02em;"),
                    P("A focused, reliable exam workflow for Nigerian primary schools.", cls="text-muted text-center mb-5"),
                ),
                Row(
                    Col(
                        Div(
                            Div(
                                Div(Icon("file-earmark-text", cls="bi text-success fs-4"), cls="rounded-circle bg-white shadow-sm d-flex align-items-center justify-content-center me-3 flex-shrink-0", style="width: 48px; height: 48px;"),
                                Div(
                                    Strong("NERDC Curriculum Built In", cls="fs-6 text-dark d-block mb-1"),
                                    P("Choose class, subject, term and weeks from the national scheme of work. Every AI draft starts from a clear curriculum scope.", cls="text-muted small mb-0 lh-sm"),
                                ),
                                cls="d-flex align-items-start",
                            ),
                            cls="p-4 rounded-4 h-100",
                            style="background-color: #F2F5F0; border: 1px solid #E2E8DF;",
                        ),
                        span=12, md=6, cls="mb-4",
                    ),
                    Col(
                        Div(
                            Div(
                                Div(Icon("sliders", cls="bi text-success fs-4"), cls="rounded-circle bg-white shadow-sm d-flex align-items-center justify-content-center me-3 flex-shrink-0", style="width: 48px; height: 48px;"),
                                Div(
                                    Strong("Past-Question Support", cls="fs-6 text-dark d-block mb-1"),
                                    P("Approved questions in the bank help teachers reuse strong material and give AI generation useful local examples.", cls="text-muted small mb-0 lh-sm"),
                                ),
                                cls="d-flex align-items-start",
                            ),
                            cls="p-4 rounded-4 h-100",
                            style="background-color: #F2F5F0; border: 1px solid #E2E8DF;",
                        ),
                        span=12, md=6, cls="mb-4",
                    ),
                    Col(
                        Div(
                            Div(
                                Div(Icon("shield-check", cls="bi text-success fs-4"), cls="rounded-circle bg-white shadow-sm d-flex align-items-center justify-content-center me-3 flex-shrink-0", style="width: 48px; height: 48px;"),
                                Div(
                                    Strong("Quality Preflight Checks", cls="fs-6 text-dark d-block mb-1"),
                                    P("Deterministic preflight checks catch duplicate questions, unclear stems, missing answer keys, and invalid options before exams ever reach print.", cls="text-muted small mb-0 lh-sm"),
                                ),
                                cls="d-flex align-items-start",
                            ),
                            cls="p-4 rounded-4 h-100",
                            style="background-color: #F2F5F0; border: 1px solid #E2E8DF;",
                        ),
                        span=12, md=6, cls="mb-4",
                    ),
                    Col(
                        Div(
                            Div(
                                Div(Icon("people-fill", cls="bi text-success fs-4"), cls="rounded-circle bg-white shadow-sm d-flex align-items-center justify-content-center me-3 flex-shrink-0", style="width: 48px; height: 48px;"),
                                Div(
                                    Strong("Admin Governance & Roles", cls="fs-6 text-dark d-block mb-1"),
                                    P("Headteachers and administrators maintain full control. Review, approve, reject, or request revisions on teacher-submitted exams with complete audit logging.", cls="text-muted small mb-0 lh-sm"),
                                ),
                                cls="d-flex align-items-start",
                            ),
                            cls="p-4 rounded-4 h-100",
                            style="background-color: #F2F5F0; border: 1px solid #E2E8DF;",
                        ),
                        span=12, md=6, cls="mb-4",
                    ),
                    g=3,
                    cls="mb-5 pb-3",
                ),
                id="features",
                cls="py-4",
            ),
        ),

        # 3. Workflow Section (Full-width soft background #EEF2EB)
        Div(
            Container(
                Div(
                    H2("From curriculum scope to exam-ready paper in minutes", cls="fw-bold text-center text-dark mb-2", style="letter-spacing: -0.02em;"),
                    P("A simple 6-step workflow from draft to classroom-ready print", cls="text-muted text-center mb-5"),
                ),
                Row(
                    Col(
                        Card(
                            Div("01", cls="fw-bold text-muted-custom fs-3 mb-2", style="color: #94A3B8;"),
                            Strong("Choose curriculum scope", cls="fs-6 text-dark d-block mb-2"),
                            P("Select class, subject, term and teaching weeks from the Nigerian NERDC curriculum.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white",
                        ),
                        span=12, md=6, lg=4, cls="mb-4",
                    ),
                    Col(
                        Card(
                            Div("02", cls="fw-bold text-muted-custom fs-3 mb-2", style="color: #94A3B8;"),
                            Strong("Create generation request", cls="fs-6 text-dark d-block mb-2"),
                            P("Specify grade level, subject, term, weeks, question types, and difficulty distribution.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white",
                        ),
                        span=12, md=6, lg=4, cls="mb-4",
                    ),
                    Col(
                        Card(
                            Div("03", cls="fw-bold text-muted-custom fs-3 mb-2", style="color: #94A3B8;"),
                            Strong("Teacher submit proposal", cls="fs-6 text-dark d-block mb-2"),
                            P("Teachers submit generation proposals to school admins for review, or generate directly in solo mode.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white",
                        ),
                        span=12, md=6, lg=4, cls="mb-4",
                    ),
                    Col(
                        Card(
                            Div("04", cls="fw-bold text-muted-custom fs-3 mb-2", style="color: #94A3B8;"),
                            Strong("AI-grounded generation", cls="fs-6 text-dark d-block mb-2"),
                            P("Our pipeline generates curriculum-aligned questions with automatic answers, distractors, and marking guides.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white",
                        ),
                        span=12, md=6, lg=4, cls="mb-4",
                    ),
                    Col(
                        Card(
                            Div("05", cls="fw-bold text-muted-custom fs-3 mb-2", style="color: #94A3B8;"),
                            Strong("Quality preflight & audit", cls="fs-6 text-dark d-block mb-2"),
                            P("Automated checks verify question quality, taxonomy balance, syllabus coverage, and flag duplicate stems.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white",
                        ),
                        span=12, md=6, lg=4, cls="mb-4",
                    ),
                    Col(
                        Card(
                            Div("06", cls="fw-bold text-muted-custom fs-3 mb-2", style="color: #94A3B8;"),
                            Strong("Multi-format export", cls="fs-6 text-dark d-block mb-2"),
                            P("Admins review, approve, and export to Word (.docx) or PDF formatted and ready for the examination hall.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white",
                        ),
                        span=12, md=6, lg=4, cls="mb-4",
                    ),
                    g=3,
                ),
                cls="py-5",
            ),
            id="how-it-works",
            style="background-color: #EEF2EB;",
            cls="w-100 my-5",
        ),

        # 4. Pricing Section
        Container(
            Div(
                Div(
                    H2("Simple, transparent pricing", cls="fw-bold text-center text-dark mb-2", style="letter-spacing: -0.02em;"),
                    P("Start free, upgrade as your school grows", cls="text-muted text-center mb-5"),
                ),
                Row(
                    # Starter Plan
                    Col(
                        Card(
                            Span("Starter", cls="text-muted small fw-bold text-uppercase d-block mb-2"),
                            Div(Span("Free", cls="fs-1 fw-bold text-dark"), cls="mb-2"),
                            P("For individual teachers & small tutorial centers", cls="text-muted small mb-4"),
                            Ul(
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "3 exams per month", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "Single teacher account", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "NERDC curriculum scheme", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "Word (.docx) export format", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "Community support", cls="mb-2 small d-flex align-items-center"),
                                cls="list-unstyled mb-4",
                            ),
                            Button("Start Free", as_="a", href="/register?mode=individual", variant="success", cls="btn-brand w-100 rounded-pill py-2 text-white fw-semibold mt-auto"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white d-flex flex-column",
                            style="border: 1px solid #E2E8DF !important;",
                        ),
                        span=12, lg=4, cls="mb-4",
                    ),
                    # Academy Plan (FEATURED - Dark Green #00412E)
                    Col(
                        Card(
                            Span("Academy", cls="text-white-50 small fw-bold text-uppercase d-block mb-2"),
                            Div(Span("₦25,000", cls="fs-1 fw-bold text-white"), Span("/mo", cls="text-white-50 small"), cls="mb-2"),
                            P("For growing primary schools with up to 20 teachers", cls="text-white-50 small mb-4"),
                            Ul(
                                Li(Icon("check-circle-fill", cls="bi text-white me-2"), "Unlimited exams", cls="mb-2 small text-white d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-white me-2"), "Up to 20 teacher accounts", cls="mb-2 small text-white d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-white me-2"), "Admin approval workflow", cls="mb-2 small text-white d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-white me-2"), "Question bank with export", cls="mb-2 small text-white d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-white me-2"), "Quality preflight checks", cls="mb-2 small text-white d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-white me-2"), "Dedicated school branding", cls="mb-2 small text-white d-flex align-items-center"),
                                cls="list-unstyled mb-4",
                            ),
                            Button("Get Started", as_="a", href="/register?mode=school", variant="light", cls="w-100 rounded-pill py-2 text-success fw-bold mt-auto shadow-sm"),
                            cls="p-4 h-100 border-0 shadow-lg rounded-4 text-white d-flex flex-column",
                            style="background-color: #00412E !important; transform: scale(1.02);",
                        ),
                        span=12, lg=4, cls="mb-4",
                    ),
                    # Enterprise Plan
                    Col(
                        Card(
                            Span("Enterprise", cls="text-muted small fw-bold text-uppercase d-block mb-2"),
                            Div(Span("Custom", cls="fs-1 fw-bold text-dark"), cls="mb-2"),
                            P("For school networks & education boards", cls="text-muted small mb-4"),
                            Ul(
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "Unlimited teachers", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "Multi-school manage", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "Custom curriculum grounding", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "API access", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "SLA guarantee", cls="mb-2 small d-flex align-items-center"),
                                Li(Icon("check-circle-fill", cls="bi text-success me-2"), "On-site training", cls="mb-2 small d-flex align-items-center"),
                                cls="list-unstyled mb-4",
                            ),
                            Button("Contact Sales", as_="a", href="/about", variant="success", cls="btn-brand w-100 rounded-pill py-2 text-white fw-semibold mt-auto"),
                            cls="p-4 h-100 border-0 shadow-sm rounded-4 bg-white d-flex flex-column",
                            style="border: 1px solid #E2E8DF !important;",
                        ),
                        span=12, lg=4, cls="mb-4",
                    ),
                    g=4,
                    cls="align-items-stretch mb-5",
                ),
                id="pricing",
                cls="py-5",
            ),
        ),

        # 5. FAQ Section (Full-width soft background #EEF2EB)
        Div(
            Container(
                Div(
                    H2("Frequently asked questions", cls="fw-bold text-center text-dark mb-4", style="letter-spacing: -0.02em;"),
                ),
                Div(
                    *[
                        Div(
                            Div(
                                Strong(q, cls="d-block text-dark fw-bold mb-2 fs-6"),
                                P(a, cls="text-muted small mb-0 lh-base"),
                                cls="p-4",
                            ),
                            cls="bg-white rounded-3 shadow-sm border-0 mb-3",
                            style="border: 1px solid #E2E8DF !important;",
                        )
                        for q, a in [
                            (
                                "Is SkuPhase a school management system?",
                                "No. SkuPhase is focused on one thing: generating and managing high-quality, curriculum-aligned examinations. We complement your existing school portal or report card system.",
                            ),
                            (
                                "Which subjects and curriculum classes does SkuPhase support?",
                                "SkuPhase covers the Nigerian NERDC curriculum from Pre-Nursery through SSS 3, with structured primary, JSS, and SSS learning outcomes.",
                            ),
                            (
                                "Who can approve an exam generation?",
                                "Only school administrators and designated academic directors can approve proposals and finalized exams. Teachers can draft, refine, and submit proposals for approval.",
                            ),
                            (
                                "How are exam papers and marking schemes formatted?",
                                "Exams export cleanly to Microsoft Word (.docx) and printable PDF with standard school headers, instructions, student details, section splits, marks allocation, and separate teacher marking keys.",
                            ),
                            (
                                "Can I export exams to print-ready format?",
                                "Yes. Both .docx and PDF formats are formatted with standard Nigerian exam styling, ready for monochrome or color school duplication and printing.",
                            ),
                        ]
                    ],
                    style="max-width: 800px; margin: 0 auto;",
                ),
                cls="py-5",
            ),
            id="faq",
            style="background-color: #EEF2EB;",
            cls="w-100 my-5",
        ),

        # 6. Bottom Call to Action Banner (Full-width Dark Green #00412E)
        Div(
            Container(
                Div(
                    Div(
                        Icon("mortarboard", cls="bi text-white mb-3", style="font-size: 2.5rem;"),
                        cls="text-center",
                    ),
                    H2("Ready to transform your exam workflow?", cls="fw-bold text-white mb-2 text-center", style="letter-spacing: -0.02em; font-size: clamp(1.8rem, 4vw, 2.5rem);"),
                    P("Join hundreds of Nigerian schools and educators already saving hours on exam preparation.", cls="text-white-50 text-center mb-4", style="font-size: 1.05rem;"),
                    Div(
                        Button("Start Free Today", as_="a", href="/register", variant="light", size="lg", cls="rounded-pill px-4 py-2 fw-bold text-success me-2 mb-2 shadow-sm"),
                        Button("Book a Demo", as_="a", href="/about", variant="outline-light", size="lg", cls="rounded-pill px-4 py-2 fw-semibold mb-2"),
                        cls="d-flex justify-content-center flex-wrap gap-2",
                    ),
                    cls="py-5 text-center",
                ),
            ),
            style="background-color: #00412E;",
            cls="w-100 py-4",
        ),
    )


def how_it_works():
    """How SkuPhase Works page matching prototype screenshot media_1788661527695.png:
    - Soft pale sage background #E6ECE5.
    - Centered headline 'How SkuPhase Works' + subtitle.
    - 6 numbered white cards stacked vertically with exact copy.
    - Centered dark green CTA banner at bottom with dual buttons.
    """
    cards_data = [
        (
            "1. Pick the Curriculum Scope",
            "Choose a class, subject, term and teaching weeks from the built-in NERDC scheme of work. Teachers can browse the curriculum or start directly from the exam wizard.",
        ),
        (
            "2. Set Up the Paper",
            "Define the title, sections, question types, marks and instructions. A teacher can also create a manual paper when questions are already prepared.",
        ),
        (
            "3. Generation Proposals",
            "Teachers and auditors submit generation proposals — structured requests describing what kind of exam they need. These include subject, grade level, number of questions per section, question types (MCQ, theory, essay), and special instructions. Proposals are reviewed by the school admin who can accept, decline, or request changes.",
        ),
        (
            "4. Generate From the Curriculum",
            "SkuPhase drafts questions from the selected NERDC objectives and suitable approved question-bank examples. Generation progress is visible until the paper is ready to review.",
        ),
        (
            "5. Review, Refine & Approve",
            "Teachers and school reviewers inspect questions, add audit comments and refine the paper. School accounts use the configured approval flow; individual teachers control their own workspace.",
        ),
        (
            "6. Preflight & Export",
            "Preflight checks question counts, marks, answer keys and paper structure before export. Approved papers are available as clean printable PDF or Word documents.",
        ),
    ]

    return PublicShell(
        Title("How SkuPhase Works — SkuPhase"),
        Div(
            Container(
                Div(
                    H1(
                        "How SkuPhase Works",
                        cls="fw-bold text-center mb-3",
                        style="color: #00412E; font-size: clamp(2.4rem, 4.5vw, 3.4rem); letter-spacing: -0.025em;",
                    ),
                    P(
                        "A transparent, curriculum-first workflow built for Nigerian primary-school exam preparation.",
                        cls="text-center mb-5",
                        style="color: #475569; max-width: 620px; margin: 0 auto; line-height: 1.6; font-size: 1.05rem;",
                    ),
                    # 6 Stacked Cards
                    Div(
                        *[
                            Card(
                                Strong(title, cls="fs-6 fw-bold text-dark d-block mb-2"),
                                P(body, cls="small mb-0", style="color: #475569; line-height: 1.65;"),
                                cls="bg-white rounded-4 p-4 shadow-sm border-0 mb-4",
                            )
                            for title, body in cards_data
                        ],
                        style="max-width: 820px; margin: 0 auto;",
                    ),
                    # Bottom Call To Action Card
                    Div(
                        Div(
                            H2("Ready to see it in action?", cls="fw-bold text-white mb-2 fs-4"),
                            P(
                                "Set up your school account and generate your first exam in under an hour.",
                                cls="text-white-50 small mb-4",
                            ),
                            Div(
                                Button(
                                    "Start Free",
                                    Span(" →", cls="ms-1 fw-bold"),
                                    as_="a",
                                    href="/register",
                                    variant="light",
                                    cls="btn bg-white rounded-pill px-4 py-2 fw-semibold me-2 text-decoration-none shadow-sm",
                                    style="color: #00412E !important;",
                                ),
                                Button(
                                    "Book Demo",
                                    as_="a",
                                    href="/contact",
                                    variant="outline-light",
                                    cls="btn rounded-3 px-4 py-2 fw-semibold text-white text-decoration-none",
                                    style="border: 1px solid rgba(255, 255, 255, 0.3) !important;",
                                ),
                                cls="d-flex justify-content-center align-items-center gap-2",
                            ),
                            cls="p-5 text-center rounded-4 shadow-lg text-white mb-5",
                            style="background-color: #00412E !important; max-width: 820px; margin: 2rem auto 0;",
                        ),
                    ),
                    cls="py-4",
                ),
            ),
            style="background-color: #E6ECE5; min-height: 85vh; padding-top: 3.5rem; padding-bottom: 5rem;",
            cls="w-100",
        ),
        active="how-it-works",
    )


def contact(flash: str | None = None):
    """Contact page matching prototype screenshot media_1788661527640.png:
    - Soft pale sage background #E6ECE5.
    - Headline 'Get in Touch' + subtitle.
    - Left Card: 'Send us a message' form with First name, Last name, School email, School name,
      topic dropdown, Message textarea, Send Message button.
    - Right Cards: 'Contact information' (email, phone, address) + 'Book a live demo' card.
    """
    return PublicShell(
        Title("Get in Touch — SkuPhase"),
        Div(
            Container(
                Div(
                    *(
                        [Div(Alert(flash, variant="success", cls="mb-4 text-center rounded-3"), style="max-width: 1040px; margin: 0 auto;")]
                        if flash
                        else []
                    ),
                    H1(
                        "Get in Touch",
                        cls="fw-bold text-center mb-3",
                        style="color: #00412E; font-size: clamp(2.4rem, 4vw, 3.2rem); letter-spacing: -0.025em;",
                    ),
                    P(
                        "Have questions about SkuPhase? Want to book a demo for your school? We would love to hear from you.",
                        cls="text-center mb-5",
                        style="color: #475569; max-width: 600px; margin: 0 auto; line-height: 1.6; font-size: 1.05rem;",
                    ),
                    Row(
                        # Left Column: Send us a message
                        Col(
                            Card(
                                H2("Send us a message", cls="fw-bold text-dark fs-5 mb-4"),
                                Form(
                                    Row(
                                        Col(
                                            Div(
                                                Label("First name", cls="form-label text-muted small fw-medium mb-1"),
                                                Input(name="first_name", placeholder="Amaka", cls="form-control rounded-3 py-2 border-0", style="background-color: #EDF2EC;"),
                                                cls="mb-3",
                                            ),
                                            span=6,
                                        ),
                                        Col(
                                            Div(
                                                Label("Last name", cls="form-label text-muted small fw-medium mb-1"),
                                                Input(name="last_name", placeholder="Obi", cls="form-control rounded-3 py-2 border-0", style="background-color: #EDF2EC;"),
                                                cls="mb-3",
                                            ),
                                            span=6,
                                        ),
                                        g=3,
                                    ),
                                    Div(
                                        Label("School email", cls="form-label text-muted small fw-medium mb-1"),
                                        Input(name="email", input_type="email", placeholder="admin@yourschool.edu.ng", cls="form-control rounded-3 py-2 border-0 mb-3", style="background-color: #EDF2EC;"),
                                    ),
                                    Div(
                                        Label("School name", cls="form-label text-muted small fw-medium mb-1"),
                                        Input(name="school_name", placeholder="Greenfield Academy, Lagos", cls="form-control rounded-3 py-2 border-0 mb-3", style="background-color: #EDF2EC;"),
                                    ),
                                    Div(
                                        Label("What can we help you with?", cls="form-label text-muted small fw-medium mb-1"),
                                        Select(
                                            Option("Book a product demo", value="demo", selected=True),
                                            Option("Pricing & school licensing", value="pricing"),
                                            Option("Curriculum & subject coverage", value="curriculum"),
                                            Option("General inquiry", value="general"),
                                            cls="form-select rounded-3 py-2 border-0 mb-3",
                                            style="background-color: #EDF2EC;",
                                            name="topic",
                                        ),
                                    ),
                                    Div(
                                        Label("Message", cls="form-label text-muted small fw-medium mb-1"),
                                        Textarea(
                                            name="message",
                                            placeholder="Tell us about your school and what you need...",
                                            rows=4,
                                            cls="form-control rounded-3 py-2 border-0 mb-4",
                                            style="background-color: #EDF2EC;",
                                        ),
                                    ),
                                    Button(
                                        "Send Message",
                                        type="submit",
                                        variant="success",
                                        cls="btn-brand w-100 rounded-pill py-3 fw-semibold text-white",
                                        style="background-color: #00412E !important; border-color: #00412E !important;",
                                    ),
                                    action="/contact",
                                    method="post",
                                ),
                                cls="bg-white rounded-4 p-4 p-md-5 shadow-sm border-0 h-100",
                            ),
                            span=12, lg=7, cls="mb-4",
                        ),
                        # Right Column: Contact information + Demo info
                        Col(
                            Div(
                                Card(
                                    H3("Contact information", cls="fw-bold text-dark fs-6 mb-4"),
                                    Div(
                                        Div(
                                            Div(
                                                Icon("envelope", cls="bi text-dark fs-5"),
                                                cls="rounded-circle d-flex align-items-center justify-content-center me-3 flex-shrink-0",
                                                style="width: 42px; height: 42px; background-color: #EBF1EA;",
                                            ),
                                            Div(
                                                Span("Email", cls="text-muted small d-block"),
                                                Strong("hello@skuphase.ng", cls="text-dark small"),
                                            ),
                                            cls="d-flex align-items-center mb-3 pb-2",
                                        ),
                                        Div(
                                            Div(
                                                Icon("telephone", cls="bi text-dark fs-5"),
                                                cls="rounded-circle d-flex align-items-center justify-content-center me-3 flex-shrink-0",
                                                style="width: 42px; height: 42px; background-color: #EBF1EA;",
                                            ),
                                            Div(
                                                Span("Phone", cls="text-muted small d-block"),
                                                Strong("+234 801 234 5678", cls="text-dark small"),
                                            ),
                                            cls="d-flex align-items-center mb-3 pb-2",
                                        ),
                                        Div(
                                            Div(
                                                Icon("geo-alt", cls="bi text-dark fs-5"),
                                                cls="rounded-circle d-flex align-items-center justify-content-center me-3 flex-shrink-0",
                                                style="width: 42px; height: 42px; background-color: #EBF1EA;",
                                            ),
                                            Div(
                                                Span("Address", cls="text-muted small d-block"),
                                                Strong("Victoria Island, Lagos, Nigeria", cls="text-dark small"),
                                            ),
                                            cls="d-flex align-items-center",
                                        ),
                                    ),
                                    cls="bg-white rounded-4 p-4 shadow-sm border-0 mb-4",
                                ),
                                Card(
                                    H3("Book a live demo", cls="fw-bold fs-6 mb-2", style="color: #00412E;"),
                                    P(
                                        "We offer free 30-minute demo sessions for school administrators. We will walk you through the complete curriculum-first exam workflow for your school.",
                                        cls="small mb-3",
                                        style="color: #334155; line-height: 1.55;",
                                    ),
                                    P("Response within 24 hours on business days.", cls="small fw-bold mb-0", style="color: #00412E;"),
                                    cls="rounded-4 p-4 shadow-sm",
                                    style="background-color: #D6E2D4; border: 1px solid #CAD7C8;",
                                ),
                            ),
                            span=12, lg=5, cls="mb-4",
                        ),
                        g=4,
                        style="max-width: 1040px; margin: 0 auto;",
                    ),
                    cls="py-4",
                ),
            ),
            style="background-color: #E6ECE5; min-height: 85vh; padding-top: 3.5rem; padding-bottom: 5rem;",
            cls="w-100",
        ),
        active="contact",
    )


def about():
    return PublicShell(
        Title("About — SkuPhase"),
        Container(
            Div(
                H1("About SkuPhase", cls="app-section-title mb-3"),
                P(
                    "SkuPhase exists to cut the cost, delay and typing errors of "
                    "producing exam papers in Nigerian primary schools. Exams can be "
                    "drafted by AI from the official curriculum, or typed in directly "
                    "by teachers — then reviewed, approved and exported as clean PDFs.",
                    cls="app-body-copy",
                ),
                P(
                    "Coverage spans Pre-Nursery through SSS 3. Every exam passes a human review step before it "
                    "is final.",
                    cls="app-body-copy",
                ),
                cls="app-card p-4",
            ),
        ),
        active="about",
    )


def privacy():
    return PublicShell(
        Title("Privacy Policy — SkuPhase"),
        Container(
            Div(
                H1("Privacy Policy", cls="app-section-title mb-3"),
                P(
                    "SkuPhase only uses school and account information to provide the "
                    "exam-generation service, keep workspaces secure, and support approved "
                    "school users. Exam papers remain scoped to their school or personal workspace.",
                    cls="app-body-copy",
                ),
                H2("Our commitment", cls="fs-6 fw-bold mt-4 mb-2"),
                P("We do not sell school data. Access is controlled through authenticated accounts and role permissions. A complete launch privacy policy will be published before public rollout.", cls="app-body-copy mb-0"),
                cls="app-card p-4",
            ),
            cls="py-5",
        ),
        active="privacy",
    )


def terms():
    return PublicShell(
        Title("Terms of Service — SkuPhase"),
        Container(
            Div(
                H1("Terms of Service", cls="app-section-title mb-3"),
                P("SkuPhase helps teachers and schools prepare curriculum-aligned examination papers. Users remain responsible for checking questions, answers, instructions and final printed papers before use.", cls="app-body-copy"),
                H2("Appropriate use", cls="fs-6 fw-bold mt-4 mb-2"),
                P("Use the service only for legitimate educational work and only with authorised school accounts. Do not share passwords, export papers outside your school without permission, or rely on AI output without human review.", cls="app-body-copy mb-0"),
                cls="app-card p-4",
            ),
            cls="py-5",
        ),
        active="terms",
    )


def register_routes(app):
    """Attach public routes to the FastHTML app (handlers for 404/500 are
    passed via ``exception_handlers`` in the constructor — see app.py)."""

    @app.get("/")
    def landing():
        return home()

    @app.get("/how-it-works")
    def how_it_works_page():
        return how_it_works()

    @app.get("/contact")
    def contact_page(req: Request):
        sent = req.query_params.get("sent")
        flash = "The contact form is not connected yet. Please email hello@skuphase.ng directly." if sent == "0" else None
        return contact(flash=flash)

    @app.post("/contact")
    async def contact_submit(req: Request):
        # Do not claim delivery until a support mailbox and durable submission
        # path are configured. This keeps the public page honest in pilot builds.
        return RedirectResponse("/contact?sent=0", status_code=303)

    @app.get("/about")
    def about_page():
        return about()

    @app.get("/privacy")
    def privacy_page():
        return privacy()

    @app.get("/terms")
    def terms_page():
        return terms()


def not_found_handler(req, exc):
    """Branded 404 page (FRONTEND_SPEC §6.10)."""
    return PublicShell(
        Title("Page not found — SkuPhase"),
        Container(
            Div(
                H1("Page not found", cls="app-section-title mb-2"),
                P("The page you are looking for does not exist.", cls="app-body-copy"),
                Button("Back to home", as_="a", href="/", variant="success", cls="btn-brand"),
                cls="app-card p-5 text-center",
            ),
            cls="py-5",
        ),
    )


def server_error_handler(req, exc):
    """Branded 500 page — never reflects error details into the page (§8)."""
    return PublicShell(
        Title("Something went wrong — SkuPhase"),
        Container(
            Div(
                H1("Something went wrong", cls="app-section-title mb-2"),
                P("An unexpected error occurred. Please try again.", cls="app-body-copy"),
                Button("Back to home", as_="a", href="/", variant="success", cls="btn-brand"),
                cls="app-card p-5 text-center",
            ),
        ),
    )
