"""Layout shells for the SkuPhase frontend (FRONTEND_SPEC sec 3.3)."""

from fasthtml.common import A, Div, Footer, Form, H1, H2, Main, Nav, P, Span
from faststrap import Button, Container, Icon, Row

from app.frontend.theme import FONT_FAMILY
from app.frontend.components.feedback import app_toast_container, to_toast


def _brand_mark():
    """Text brand mark (logo.svg swaps in when the asset exists)."""
    return Span("SkuPhase", cls="navbar-brand fw-bold")


def PublicShell(*content, active: str = "", flash=None):
    """Shell for public pages: navbar + content + footer (FRONTEND_SPEC sec 3.3)."""
    links = [
        ("About", "/about", "about"),
        ("Privacy", "/privacy", "privacy"),
    ]
    nav_links = [
        A(
            label,
            href=href,
            cls="nav-link" + (" active fw-semibold" if active == key else ""),
        )
        for label, href, key in links
    ]
    return Div(
        Nav(
            Container(
                Div(
                    A(_brand_mark(), href="/", cls="navbar-brand text-decoration-none"),
                    Button(
                        Span(cls="navbar-toggler-icon"),
                        cls="navbar-toggler",
                        type="button",
                        **{"data-bs-toggle": "collapse", "data-bs-target": "#publicNav"},
                    ),
                    Div(
                        Div(
                            *nav_links,
                            Div(
                                Button(
                                    "Sign in",
                                    as_="a",
                                    href="/login",
                                    variant="outline-light",
                                    size="sm",
                                    cls="me-2",
                                ),
                                Button(
                                    "Get started",
                                    as_="a",
                                    href="/register",
                                    variant="light",
                                    size="sm",
                                ),
                                cls="d-flex align-items-center gap-2 mt-2 mt-md-0",
                            ),
                            cls="navbar-nav d-md-flex flex-md-row gap-md-3 align-items-md-center",
                        ),
                        cls="collapse navbar-collapse",
                        id="publicNav",
                    ),
                    cls="d-flex flex-wrap justify-content-between align-items-center py-2",
                ),
            ),
            cls="app-navbar navbar navbar-expand-md",
        ),
        Main(flash, *content, cls="app-main py-4"),
        Footer(
            Container(
                P(
                    "SkuPhase - curriculum-aligned exams for Nigerian primary schools.",
                    cls="mb-0 small",
                ),
                cls="py-3 text-center",
            ),
            cls="app-footer mt-5",
        ),
        cls="app-shell d-flex flex-column min-vh-100",
        **{"data-font-family": FONT_FAMILY},
    )


def _bottom_nav(active: str = ""):
    """Mobile sticky BottomNav (FRONTEND_SPEC M7): 5 touch items with Menu offcanvas trigger."""
    def _item(label, href, key, icon):
        return A(
            Icon(icon, cls="bi d-block mx-auto mb-1"),
            Span(label),
            href=href,
            cls="app-bottomnav-item" + (" active" if active == key else ""),
        )

    def _menu_button():
        return Button(
            Icon("list", cls="bi d-block mx-auto mb-1 fs-5"),
            Span("Menu"),
            type="button",
            cls="app-bottomnav-item app-bottomnav-btn",
            **{
                "data-bs-toggle": "offcanvas",
                "data-bs-target": "#appSidebar",
                "aria-controls": "appSidebar",
                "aria-label": "Open navigation menu",
            },
        )

    return Nav(
        _item("Dashboard", "/app", "dashboard", "grid-fill"),
        _item("Exams", "/app/exams", "exams", "file-earmark-text"),
        A(
            Icon("plus-lg", cls="bi"),
            Span("Generate"),
            href="/app/exams/new",
            cls="app-bottomnav-gen",
            **{"aria-label": "Generate exam with AI"},
        ),
        _item("Bank", "/app/bank", "bank", "book"),
        _menu_button(),
        cls="app-bottomnav d-lg-none",
    )


def AuthShell(*content, title: str = "Sign in"):
    """Split-screen shell for auth pages matching UI_design/Register.png."""
    left_brand_panel = Div(
        Div(
            A(
                Icon("mortarboard-fill", cls="bi me-2 fs-3 text-white"),
                Span("SkuPhase", cls="fw-bold fs-3 text-white"),
                href="/",
                cls="text-decoration-none d-flex align-items-center mb-5",
            ),
            H1(
                "Curriculum-First Primary School Exam Generator",
                cls="fw-bold text-white fs-2 mb-3 lh-sm",
            ),
            P(
                "Stop typing questions manually. Draft high-standard exams in seconds, seeded from the official NERDC scheme of work.",
                cls="text-white-50 mb-4 fs-6",
            ),
            Div(
                Div(
                    Icon("check-circle-fill", cls="bi text-success me-2"),
                    Span("Seeded NERDC scheme of work (Pre-Nursery to Primary 6)", cls="text-white small"),
                    cls="d-flex align-items-center mb-3",
                ),
                Div(
                    Icon("check-circle-fill", cls="bi text-success me-2"),
                    Span("Multi-section objective, theory & comprehension papers", cls="text-white small"),
                    cls="d-flex align-items-center mb-3",
                ),
                Div(
                    Icon("check-circle-fill", cls="bi text-success me-2"),
                    Span("Multi-dimensional quality gate and preflight audits", cls="text-white small"),
                    cls="d-flex align-items-center mb-3",
                ),
                Div(
                    Icon("check-circle-fill", cls="bi text-success me-2"),
                    Span("Instant camera-ready PDF export with answer keys", cls="text-white small"),
                    cls="d-flex align-items-center mb-3",
                ),
                cls="mb-5",
            ),
            Div(
                P(
                    "“SkuPhase gives our teachers back hours of their week while ensuring our school exams strictly meet national standards.”",
                    cls="fst-italic text-white-50 small mb-2",
                ),
                Span("— Head of Academics, Greenfield Academy", cls="fw-semibold text-white small"),
                cls="p-3 rounded-3 mt-auto",
                style="background: rgba(255, 255, 255, 0.08);",
            ),
            cls="p-4 p-lg-5 d-flex flex-column h-100 justify-content-between",
        ),
        cls="col-12 col-lg-5 d-none d-lg-block min-vh-100",
        style="background: #00412E;",
    )

    right_form_panel = Div(
        Div(
            Div(
                A(
                    Icon("mortarboard-fill", cls="bi me-2 fs-4 text-brand"),
                    Span("SkuPhase", cls="fw-bold fs-4 text-dark"),
                    href="/",
                    cls="text-decoration-none d-flex align-items-center justify-content-center mb-3 d-lg-none",
                ),
                H2(title, cls="fw-bold text-dark fs-3 mb-1 text-center text-lg-start"),
                P("Sign in to your workspace or register a new account.", cls="text-muted small mb-4 text-center text-lg-start"),
                Div(*content, cls="app-card p-4 shadow-sm border-0 rounded-4"),
                cls="w-100",
                style="max-width: 480px;",
            ),
            cls="d-flex align-items-center justify-content-center min-vh-100 p-3 p-md-4",
        ),
        cls="col-12 col-lg-7",
    )

    return Div(
        Div(
            Row(
                left_brand_panel,
                right_form_panel,
                g=0,
                cls="min-vh-100",
            ),
            cls="container-fluid p-0",
        ),
        cls="app-auth-shell min-vh-100",
    )


def AppShell(*content, user: dict | None = None, active: str = "", flash=None, crumbs=None, bell_count: int | None = None):
    """Authenticated app shell — sidebar + topbar per FRONTEND_SPEC sec 3.3/3.5
    (visual reference: ``UI_design/Exams.png``).

    Desktop (>= lg): fixed deep-green sidebar + white topbar with breadcrumbs.
    Mobile (< lg): topbar with hamburger toggling the sidebar (Bootstrap
    ``collapse`` + ``d-lg-flex`` pattern).  ``crumbs`` is an optional list of
    (label, href_or_None) tuples rendered after "Home".
    """
    user = user or {}
    name = user.get("full_name") or user.get("email") or "Account"
    role = user.get("role") or ("Teacher" if user.get("account_type") == "individual_teacher" else "Staff")
    account_type = user.get("account_type") or ""
    is_school_staff = account_type == "school_staff" or role in {"school_admin", "teacher", "auditor"}
    is_school_admin = role == "school_admin"
    school_name = user.get("school_name") or ("Personal Workspace" if account_type == "individual_teacher" else "Greenfield Academy")

    # Role-filtered navigation (FRONTEND_SPEC.md §3.3)
    nav_items = [
        ("Dashboard", "/app", "dashboard", "grid-fill"),
        ("Exams", "/app/exams", "exams", "file-earmark-text"),
        ("Curriculum", "/app/curriculum", "curriculum", "compass"),
    ]
    if is_school_staff:
        nav_items.append(("Generation Proposals", "/app/proposals", "proposals", "lightbulb"))

    nav_items.append(("Question Bank", "/app/bank", "bank", "book"))

    if is_school_admin:
        nav_items.append(("Users", "/app/staff", "staff", "people"))
        nav_items.append(("School Settings", "/app/settings", "settings", "gear"))
        nav_items.append(("Operations", "/app/ops", "ops", "activity"))

    def _nav_link(label, href, key, icon):
        return A(
            Icon(icon, cls="bi me-2"),
            label,
            href=href,
            # Audit: on mobile the sidebar is an offcanvas; tapping a link
            # navigated but left the menu open over the new page.
            **{
                "data-bs-dismiss": "offcanvas",
                "data-bs-target": "#appSidebar",
            },
            cls="app-sidebar-link d-flex align-items-center" + (" active" if active == key else ""),
        )

    sidebar = Div(
        Div(
            A(
                Icon("mortarboard-fill", cls="bi me-2 fs-5 text-success"),
                Span("SkuPhase", cls="fw-bold fs-5 text-white"),
                href="/app",
                cls="app-sidebar-brand text-decoration-none d-flex align-items-center",
            ),
            Button(
                type="button",
                cls="btn-close btn-close-white d-lg-none ms-auto",
                **{"data-bs-dismiss": "offcanvas", "data-bs-target": "#appSidebar", "aria-label": "Close navigation menu"},
            ),
            Span(Icon("chevron-left", cls="bi text-white-50 small"), cls="ms-auto d-none d-lg-inline-block"),
            cls="px-3 pt-4 pb-3 d-flex align-items-center justify-content-between",
        ),
        Nav(
            *[_nav_link(*item) for item in nav_items],
            cls="flex-column gap-1 px-2",
        ),
        Div(
            Span((role if role != "school_admin" else "SCHOOL ADMIN").upper(), cls="app-sidebar-role"),
            cls="mt-auto px-3 pb-3",
        ),
        cls="app-sidebar offcanvas-lg offcanvas-start d-lg-flex flex-column",
        style="background-color: #00412E !important;",
        id="appSidebar",
        tabindex="-1",
        **{"aria-label": "Navigation Sidebar"},
    )

    crumb_parts = [A("Home", href="/app", cls="app-crumb-link")]
    for label, href in (crumbs or []):
        if href:
            crumb_parts.append(Span(">", cls="app-crumb-sep px-1"))
            crumb_parts.append(A(label, href=href, cls="app-crumb-link"))
        else:
            crumb_parts.append(Span(">", cls="app-crumb-sep px-1"))
            crumb_parts.append(Span(label, cls="app-crumb-current fw-semibold"))

    initials = "".join(w[0] for w in name.split()[:2]).upper() or "U"
    topbar = Div(
        Button(
            Span(cls="navbar-toggler-icon"),
            cls="navbar-toggler d-lg-none me-2 p-1",
            type="button",
            **{"data-bs-toggle": "offcanvas", "data-bs-target": "#appSidebar", "aria-controls": "appSidebar", "aria-label": "Toggle navigation"},
        ),
        Div(*crumb_parts, cls="d-flex align-items-center gap-1 small"),
        Div(
            A(
                Icon("mortarboard", cls="bi me-1 text-muted"),
                role.replace("_", " ").title(),
                Icon("chevron-down", cls="bi ms-1 small text-muted"),
                href="/app/settings",
                cls="app-topbar-chip d-none d-md-inline-flex me-2",
                title="Account settings",
            ),
            A(
                school_name,
                Icon("chevron-down", cls="bi ms-1 small text-muted"),
                href="/app/settings",
                cls="app-topbar-chip d-none d-lg-inline-flex me-3",
                title="School settings",
            ),
            A(
                Icon("bell", cls="bi fs-5"),
                # Audit: badge count was hardcoded "3". Pages that know the
                # live count pass bell_count; hide the badge when zero/unknown.
                *(
                    [Span(str(bell_count), cls="app-bell-badge")]
                    if bell_count
                    else []
                ),
                href="/app/proposals",
                cls="app-topbar-bell me-3",
                title="Pending proposals & reviews",
            ),
            Span(initials, cls="app-avatar me-2"),
            Div(
                Div(name.split()[0] if name else "Account", cls="small fw-bold lh-1"),
                Div(role.replace("_", " ").title(), cls="text-muted", style="font-size:.68rem"),
                cls="d-none d-sm-block me-2",
            ),
            Form(
                Button("Log out", variant="outline-secondary", size="sm", cls="rounded-pill"),
                action="/logout",
                method="post",
                cls="d-inline",
            ),
            cls="d-flex align-items-center ms-auto",
        ),
        cls="app-topbar d-flex align-items-center px-3 px-lg-4 py-2",
    )

    flash_toast = to_toast(flash) if flash is not None else None

    return Div(
        # Mobile: sidebar collapses under the topbar; desktop: always visible.
        Div(
            sidebar,
            Div(
                topbar,
                Main(Container(*content), cls="app-main py-4"),
                cls="app-content flex-grow-1 min-vh-100",
            ),
            cls="d-flex flex-column flex-lg-row",
        ),
        _bottom_nav(active),
        app_toast_container(flash_toast),
        cls="app-shell has-bottomnav",
    )
