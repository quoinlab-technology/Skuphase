"""Public pages: landing, about, privacy (FRONTEND_SPEC §6.10)."""

from fasthtml.common import A, Div, H1, H2, Li, P, Span, Strong, Title, Ul

from faststrap import Button, Card, Col, Container, Icon, Row

from app.frontend.components.layout import PublicShell


def home():
    """Landing page matching UI_design/home.png: hero, trust metrics, 4 features, 6-step workflow, and CTA."""
    return PublicShell(
        Title("SkuPhase — Curriculum-Aligned Nigerian Primary School Exam Generator"),
        Container(
            # Hero Section
            Div(
                Div(
                    Span("🌱 Grounded in Official NERDC Curriculum & Scheme of Work", cls="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3 py-2 mb-3 fw-semibold small"),
                    H1(
                        "Curriculum-aligned exams in seconds — built for Nigerian primary schools",
                        cls="fw-bold fs-1 text-dark mb-3 lh-sm",
                        style="max-width: 800px; margin: 0 auto;",
                    ),
                    P(
                        "Stop retyping past question papers. Select your class, subject, and scheme of work weeks "
                        "to draft high-quality exams with automatic Nigerian curriculum alignment and quality audits.",
                        cls="fs-5 text-muted mb-4",
                        style="max-width: 720px; margin: 0 auto;",
                    ),
                    Div(
                        Button(
                            "Get Started Free",
                            as_="a",
                            href="/register",
                            variant="success",
                            size="lg",
                            cls="btn-brand px-4 py-3 fw-bold me-2 mb-2",
                        ),
                        Button(
                            "Sign In to Workspace",
                            as_="a",
                            href="/login",
                            variant="outline-secondary",
                            size="lg",
                            cls="px-4 py-3 mb-2",
                        ),
                        cls="d-flex justify-content-center flex-wrap gap-2",
                    ),
                    cls="text-center py-5",
                ),
            ),

            # Trust & Impact Metrics
            Div(
                Row(
                    Col(
                        Div(
                            Div("100%", cls="fw-bold fs-2 text-brand"),
                            Div("NERDC Scheme Aligned", cls="text-muted small"),
                            cls="text-center p-3",
                        ),
                        span=6, md=3,
                    ),
                    Col(
                        Div(
                            Div("Pre-N to Pri 6", cls="fw-bold fs-2 text-brand"),
                            Div("Primary Focus", cls="text-muted small"),
                            cls="text-center p-3",
                        ),
                        span=6, md=3,
                    ),
                    Col(
                        Div(
                            Div("4x", cls="fw-bold fs-2 text-brand"),
                            Div("Faster Exam Prep", cls="text-muted small"),
                            cls="text-center p-3",
                        ),
                        span=6, md=3,
                    ),
                    Col(
                        Div(
                            Div("0", cls="fw-bold fs-2 text-brand"),
                            Div("Unchecked Errors", cls="text-muted small"),
                            cls="text-center p-3",
                        ),
                        span=6, md=3,
                    ),
                    g=2,
                    cls="align-items-center py-3 border-top border-bottom mb-5",
                ),
            ),

            # 4 Core Features
            Div(
                Div(
                    H2("Engineered for Nigerian Primary Schools", cls="fw-bold text-center text-dark mb-2"),
                    P("Designed specifically for headteachers, academic coordinators, and classroom teachers.", cls="text-muted text-center mb-5"),
                ),
                Row(
                    Col(
                        Card(
                            Div(Icon("journal-bookmark-fill", cls="bi text-success fs-3 mb-3"), cls="app-row-icon ai"),
                            Strong("Official Curriculum Grounded", cls="fs-6 text-dark d-block mb-2"),
                            P("Injected directly from verified Nigerian national scheme of work topics, learning outcomes, and performance objectives.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm",
                        ),
                        span=12, md=6, lg=3,
                    ),
                    Col(
                        Card(
                            Div(Icon("layers-half", cls="bi text-primary fs-3 mb-3"), cls="app-row-icon"),
                            Strong("Multi-Section Exams", cls="fs-6 text-dark d-block mb-2"),
                            P("Combine multiple-choice objectives, theory sub-parts, comprehension passages, and essay questions in a single exam paper.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm",
                        ),
                        span=12, md=6, lg=3,
                    ),
                    Col(
                        Card(
                            Div(Icon("shield-check", cls="bi text-purple fs-3 mb-3"), cls="app-row-icon"),
                            Strong("Automated Quality Preflight", cls="fs-6 text-dark d-block mb-2"),
                            P("Detects missing answer keys, mark arithmetic mismatches, duplicate questions, and Bloom's cognitive imbalance before export.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm",
                        ),
                        span=12, md=6, lg=3,
                    ),
                    Col(
                        Card(
                            Div(Icon("file-earmark-pdf-fill", cls="bi text-danger fs-3 mb-3"), cls="app-row-icon"),
                            Strong("Print-Ready PDF Export", cls="fs-6 text-dark d-block mb-2"),
                            P("Generate camera-ready question papers and separate marking schemes branded with your school details.", cls="text-muted small mb-0"),
                            cls="p-4 h-100 border-0 shadow-sm",
                        ),
                        span=12, md=6, lg=3,
                    ),
                    g=4,
                    cls="mb-5 pb-3",
                ),
            ),

            # How it works: 6-step workflow
            Div(
                Div(
                    H2("How SkuPhase Works", cls="fw-bold text-center text-dark mb-2"),
                    P("From scheme selection to printed question paper in 6 simple steps.", cls="text-muted text-center mb-5"),
                ),
                Row(
                    Col(Div(Div("1", cls="badge bg-success rounded-circle p-2 mb-2"), Strong("Select Class & Subject", cls="d-block small text-dark"), P("Pre-Nursery to Primary 6", cls="text-muted small mb-0"), cls="p-3 text-center bg-light rounded-3 h-100"), span=6, md=4, lg=2),
                    Col(Div(Div("2", cls="badge bg-success rounded-circle p-2 mb-2"), Strong("Choose Term & Weeks", cls="d-block small text-dark"), P("Weeks 1 through 12 scheme", cls="text-muted small mb-0"), cls="p-3 text-center bg-light rounded-3 h-100"), span=6, md=4, lg=2),
                    Col(Div(Div("3", cls="badge bg-success rounded-circle p-2 mb-2"), Strong("Configure Sections", cls="d-block small text-dark"), P("Objectives & Theory counts", cls="text-muted small mb-0"), cls="p-3 text-center bg-light rounded-3 h-100"), span=6, md=4, lg=2),
                    Col(Div(Div("4", cls="badge bg-success rounded-circle p-2 mb-2"), Strong("AI Generation", cls="d-block small text-dark"), P("Curriculum-seeded prompt", cls="text-muted small mb-0"), cls="p-3 text-center bg-light rounded-3 h-100"), span=6, md=4, lg=2),
                    Col(Div(Div("5", cls="badge bg-success rounded-circle p-2 mb-2"), Strong("Preflight Audit", cls="d-block small text-dark"), P("Verify marks & answers", cls="text-muted small mb-0"), cls="p-3 text-center bg-light rounded-3 h-100"), span=6, md=4, lg=2),
                    Col(Div(Div("6", cls="badge bg-success rounded-circle p-2 mb-2"), Strong("Export PDF", cls="d-block small text-dark"), P("Ready for print & exam day", cls="text-muted small mb-0"), cls="p-3 text-center bg-light rounded-3 h-100"), span=6, md=4, lg=2),
                    g=3,
                    cls="mb-5 pb-4",
                ),
            ),

            # Pricing Section (matching UI_design/home2.png)
            Div(
                Div(
                    H2("Simple, Transparent Pricing for Nigerian Schools", cls="fw-bold text-center text-dark mb-2"),
                    P("Choose the plan that fits your classroom or entire school.", cls="text-muted text-center mb-5"),
                ),
                Row(
                    Col(
                        Card(
                            Div(
                                Strong("Starter", cls="fs-5 text-dark d-block mb-1"),
                                Span("For individual teachers and tutors", cls="text-muted small d-block mb-3"),
                                Div(Span("₦15,000", cls="fs-3 fw-bold text-dark"), Span(" / term", cls="text-muted small"), cls="mb-3"),
                            ),
                            Ul(
                                Li("Up to 50 exams per term", cls="mb-2 small text-secondary"),
                                Li("2 teacher seats", cls="mb-2 small text-secondary"),
                                Li("Pre-Nursery to Primary 6 NERDC syllabus", cls="mb-2 small text-secondary"),
                                Li("Standard print-ready PDF export", cls="mb-2 small text-secondary"),
                                cls="list-unstyled mb-4",
                            ),
                            Button("Get Started", as_="a", href="/register?plan=starter", variant="outline-success", cls="w-100 rounded-pill py-2"),
                            cls="p-4 h-100 border rounded-4 shadow-sm",
                        ),
                        span=12, md=4, cls="mb-4",
                    ),
                    Col(
                        Card(
                            Div(
                                Div(Span("MOST POPULAR", cls="badge bg-success text-white rounded-pill px-3 py-1 small fw-bold mb-2")),
                                Strong("Professional", cls="fs-5 text-dark d-block mb-1"),
                                Span("For growing primary schools", cls="text-muted small d-block mb-3"),
                                Div(Span("₦45,000", cls="fs-3 fw-bold text-brand"), Span(" / term", cls="text-muted small"), cls="mb-3"),
                            ),
                            Ul(
                                Li("Unlimited exams & revisions", cls="mb-2 small text-secondary fw-semibold"),
                                Li("15 teacher seats + review governance", cls="mb-2 small text-secondary"),
                                Li("9-point automated quality preflight checks", cls="mb-2 small text-secondary"),
                                Li("School Question Bank repository", cls="mb-2 small text-secondary"),
                                Li("Camera-ready PDF & marking guide", cls="mb-2 small text-secondary"),
                                cls="list-unstyled mb-4",
                            ),
                            Button("Start 14-Day Free Trial", as_="a", href="/register?plan=pro", variant="success", cls="btn-brand w-100 rounded-pill py-2 fw-bold"),
                            cls="p-4 h-100 border border-success border-2 rounded-4 shadow",
                        ),
                        span=12, md=4, cls="mb-4",
                    ),
                    Col(
                        Card(
                            Div(
                                Strong("Enterprise", cls="fs-5 text-dark d-block mb-1"),
                                Span("For multi-campus school networks", cls="text-muted small d-block mb-3"),
                                Div(Span("Custom", cls="fs-3 fw-bold text-dark"), cls="mb-3"),
                            ),
                            Ul(
                                Li("Unlimited teacher and admin accounts", cls="mb-2 small text-secondary"),
                                Li("Multi-campus central governance", cls="mb-2 small text-secondary"),
                                Li("Custom school header & branding", cls="mb-2 small text-secondary"),
                                Li("Bulk question bank migration & ingestion", cls="mb-2 small text-secondary"),
                                Li("Dedicated academic account manager", cls="mb-2 small text-secondary"),
                                cls="list-unstyled mb-4",
                            ),
                            Button("Contact Sales", as_="a", href="/about", variant="outline-dark", cls="w-100 rounded-pill py-2"),
                            cls="p-4 h-100 border rounded-4 shadow-sm",
                        ),
                        span=12, md=4, cls="mb-4",
                    ),
                    g=4,
                    cls="mb-5 pb-4",
                ),
            ),

            # FAQ Accordion (matching UI_design/home2.png)
            Div(
                Div(
                    H2("Frequently Asked Questions", cls="fw-bold text-center text-dark mb-2"),
                    P("Everything you need to know about SkuPhase and our curriculum alignment.", cls="text-muted text-center mb-5"),
                ),
                Div(
                    Div(
                        Div(
                            Button(
                                "Which classes and curricula are supported?",
                                cls="accordion-button fw-semibold text-dark",
                                type="button",
                                **{"data-bs-toggle": "collapse", "data-bs-target": "#faq1"},
                            ),
                            cls="accordion-header",
                        ),
                        Div(
                            Div(
                                P("SkuPhase is built from the ground up for Nigerian primary schools. It is pre-seeded with the official NERDC curriculum and schemes of work spanning Pre-Nursery, Nursery 1-3, and Primary 1 through Primary 6 for Mathematics, English Language, Basic Science, Social Studies, and National Values.", cls="text-muted small mb-0"),
                                cls="accordion-body",
                            ),
                            id="faq1",
                            cls="accordion-collapse collapse show",
                        ),
                        cls="accordion-item border rounded-3 mb-3",
                    ),
                    Div(
                        Div(
                            Button(
                                "Can teachers use SkuPhase independently without school admin setup?",
                                cls="accordion-button collapsed fw-semibold text-dark",
                                type="button",
                                **{"data-bs-toggle": "collapse", "data-bs-target": "#faq2"},
                            ),
                            cls="accordion-header",
                        ),
                        Div(
                            Div(
                                P("Yes! Independent teachers, subject heads, and lesson tutors can sign up for an individual teacher account to draft, edit, and export examination papers without needing a school-wide deployment.", cls="text-muted small mb-0"),
                                cls="accordion-body",
                            ),
                            id="faq2",
                            cls="accordion-collapse collapse",
                        ),
                        cls="accordion-item border rounded-3 mb-3",
                    ),
                    Div(
                        Div(
                            Button(
                                "How does SkuPhase guarantee exam quality and accuracy?",
                                cls="accordion-button collapsed fw-semibold text-dark",
                                type="button",
                                **{"data-bs-toggle": "collapse", "data-bs-target": "#faq3"},
                            ),
                            cls="accordion-header",
                        ),
                        Div(
                            Div(
                                P("Every generated exam undergoes our automated 9-point Preflight Audit. It checks for formula syntax errors, mark total discrepancies, missing answer options, duplicate questions, and curriculum mismatch before any exam can be marked approved or printed.", cls="text-muted small mb-0"),
                                cls="accordion-body",
                            ),
                            id="faq3",
                            cls="accordion-collapse collapse",
                        ),
                        cls="accordion-item border rounded-3 mb-3",
                    ),
                    Div(
                        Div(
                            Button(
                                "Are exported exams camera-ready for direct printing?",
                                cls="accordion-button collapsed fw-semibold text-dark",
                                type="button",
                                **{"data-bs-toggle": "collapse", "data-bs-target": "#faq4"},
                            ),
                            cls="accordion-header",
                        ),
                        Div(
                            Div(
                                P("Yes. SkuPhase generates clean, standard printable PDFs formatted with school headers, exam instructions, candidate name blocks, and structured question numbering ready for school photocopiers or print shops.", cls="text-muted small mb-0"),
                                cls="accordion-body",
                            ),
                            id="faq4",
                            cls="accordion-collapse collapse",
                        ),
                        cls="accordion-item border rounded-3 mb-3",
                    ),
                    cls="accordion mb-5 pb-4",
                    id="faqAccordion",
                    style="max-width: 800px; margin: 0 auto;",
                ),
            ),

            # Bottom CTA Section
            Div(
                Div(
                    H2("Ready to Transform Your School's Examination Process?", cls="fw-bold text-white mb-2"),
                    P("Sign up as an individual teacher or register your school in less than 2 minutes.", cls="text-white-50 mb-4"),
                    Button("Create Free Account", as_="a", href="/register", variant="light", size="lg", cls="px-4 py-2 fw-bold text-dark"),
                    cls="p-5 text-center rounded-4",
                    style="background: #00412E;",
                ),
                cls="mb-5",
            ),
        ),
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
                    "Coverage is currently Pre-Nursery to Primary 6, with secondary "
                    "levels planned. Every exam passes a human review step before it "
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
        Title("Privacy & Terms — SkuPhase"),
        Container(
            Div(
                H1("Privacy & Terms", cls="app-section-title mb-3"),
                P(
                    "Placeholder — full privacy policy and terms of service will be "
                    "published before public launch.",
                    cls="app-body-copy",
                ),
                cls="app-card p-4",
            ),
        ),
        active="privacy",
    )


def register_routes(app):
    """Attach public routes to the FastHTML app (handlers for 404/500 are
    passed via ``exception_handlers`` in the constructor — see app.py)."""

    @app.get("/")
    def landing():
        return home()

    @app.get("/about")
    def about_page():
        return about()

    @app.get("/privacy")
    def privacy_page():
        return privacy()


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