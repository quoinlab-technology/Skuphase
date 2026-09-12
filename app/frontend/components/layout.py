"""Layout shells for the SkuPhase frontend (FRONTEND_SPEC sec 3.3)."""

from fasthtml.common import A, Button as HtmlButton, Div, Footer, Form, H1, H2, Main, Nav, P, Script, Span, Strong
from faststrap import Button, Col, Container, Icon, Row

from app.frontend.theme import FONT_FAMILY
from app.frontend.components.feedback import app_toast_container, to_toast


def _brand_mark():
    """Brand mark matching prototype: squircle green icon + SkuPhase."""
    return Span(
        Span(
            Icon("mortarboard-fill", cls="bi text-white"),
            cls="d-inline-flex align-items-center justify-content-center me-2",
            style="width:30px; height:30px; background-color: #00412E; border-radius: 7px; font-size: 0.95rem; vertical-align: -3px;",
        ),
        Span("SkuPhase", cls="fw-bold text-dark fs-5"),
        cls="navbar-brand text-decoration-none d-inline-flex align-items-center mb-0",
    )


def PublicShell(*content, active: str = "", flash=None):
    """Shell for public pages: navbar + content + footer matching prototype."""
    links = [
        ("Features", "/#features", "features"),
        ("Pricing", "/#pricing", "pricing"),
        ("How it works", "/how-it-works", "how-it-works"),
        ("Contact", "/contact", "contact"),
    ]
    nav_links = [
        A(
            label,
            href=href,
            cls="nav-link text-dark fw-medium px-2" + (" active text-success fw-bold" if active == key else ""),
        )
        for label, href, key in links
    ]
    return Div(
        Nav(
            Container(
                Div(
                    A(_brand_mark(), href="/", cls="text-decoration-none"),
                    Button(
                        Span(cls="navbar-toggler-icon"),
                        cls="navbar-toggler border-0 shadow-none",
                        type="button",
                        **{"data-bs-toggle": "collapse", "data-bs-target": "#publicNav"},
                    ),
                    Div(
                        Div(
                            *nav_links,
                            cls="navbar-nav mx-auto d-md-flex flex-md-row gap-md-2 align-items-md-center justify-content-center",
                        ),
                        Div(
                            A(
                                "Sign In",
                                href="/login",
                                cls="text-dark text-decoration-none fw-semibold me-3 small",
                            ),
                            Button(
                                "Start Free",
                                as_="a",
                                href="/register",
                                variant="success",
                                size="sm",
                                cls="btn-brand rounded-pill px-3 py-1 fw-semibold text-white",
                            ),
                            cls="d-flex align-items-center mt-2 mt-md-0",
                        ),
                        cls="collapse navbar-collapse",
                        id="publicNav",
                    ),
                    cls="d-flex flex-wrap justify-content-between align-items-center py-2 w-100",
                ),
            ),
            cls="navbar navbar-expand-md bg-white border-bottom sticky-top shadow-sm",
        ),
        Main(flash, *content, cls="app-main"),
        Footer(
            Container(
                Row(
                    Col(
                        Div(
                            _brand_mark(),
                            P(
                                "Curriculum-aligned exams for Nigerian primary schools.",
                                cls="text-muted small mt-2 mb-0",
                                style="max-width: 280px;",
                            ),
                        ),
                        span=12, md=6, lg=5, cls="mb-4 mb-md-0",
                    ),
                    Col(
                        Div(
                            Strong("Product", cls="d-block small text-dark fw-bold mb-2"),
                            Div(A("Features", href="/#features", cls="text-muted text-decoration-none small d-block mb-1")),
                            Div(A("Pricing", href="/#pricing", cls="text-muted text-decoration-none small d-block mb-1")),
                            Div(A("How It Works", href="/how-it-works", cls="text-muted text-decoration-none small d-block mb-1")),
                        ),
                        span=4, md=2, cls="mb-3 mb-md-0",
                    ),
                    Col(
                        Div(
                            Strong("Company", cls="d-block small text-dark fw-bold mb-2"),
                            Div(A("Contact", href="/contact", cls="text-muted text-decoration-none small d-block mb-1")),
                            Div(A("About", href="/about", cls="text-muted text-decoration-none small d-block mb-1")),
                        ),
                        span=4, md=2, cls="mb-3 mb-md-0",
                    ),
                    Col(
                        Div(
                            Strong("Legal", cls="d-block small text-dark fw-bold mb-2"),
                            Div(A("Privacy", href="/privacy", cls="text-muted text-decoration-none small d-block mb-1")),
                            Div(A("Terms", href="/terms", cls="text-muted text-decoration-none small d-block mb-1")),
                        ),
                        span=4, md=2, cls="mb-3 mb-md-0",
                    ),
                    cls="py-5 border-bottom",
                ),
                Div(
                    P(
                        "© 2026 SkuPhase. Built for Nigerian schools. All rights reserved.",
                        cls="text-muted small text-center mb-0 py-3",
                    ),
                ),
            ),
            cls="bg-white border-top mt-auto",
        ),
        cls="app-shell d-flex flex-column min-vh-100 bg-white",
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
    """Split-screen shell for auth and registration pages matching prototype screenshots."""
    left_brand_panel = Div(
        Div(
            A(
                Icon("mortarboard-fill", cls="bi me-2 fs-4 text-white"),
                Span("SkuPhase", cls="fw-bold fs-4 text-white"),
                href="/",
                cls="text-decoration-none d-flex align-items-center mb-5",
            ),
            Div(
                H1(
                    "Start generating\nbetter exams today.",
                    cls="fw-bold text-white mb-3",
                    style="font-size: clamp(2.1rem, 3.2vw, 2.75rem); font-weight: 800; line-height: 1.15; letter-spacing: -0.025em; white-space: pre-line;",
                ),
                P(
                    "Join 50+ Nigerian schools using AI to create curriculum-aligned, quality-checked examinations in minutes.",
                    cls="text-white-50 mb-5 fs-6",
                    style="color: rgba(255, 255, 255, 0.78) !important; line-height: 1.65; max-width: 440px;",
                ),
                Div(
                    Div(
                        Icon("check-circle", cls="bi text-white opacity-75 me-3 fs-5"),
                        Span("Free plan — no credit card required", cls="text-white small fw-medium"),
                        cls="d-flex align-items-center mb-3",
                    ),
                    Div(
                        Icon("check-circle", cls="bi text-white opacity-75 me-3 fs-5"),
                        Span("NERDC curriculum aligned", cls="text-white small fw-medium"),
                        cls="d-flex align-items-center mb-3",
                    ),
                    Div(
                        Icon("check-circle", cls="bi text-white opacity-75 me-3 fs-5"),
                        Span("Full admin control over AI generation", cls="text-white small fw-medium"),
                        cls="d-flex align-items-center mb-3",
                    ),
                    Div(
                        Icon("check-circle", cls="bi text-white opacity-75 me-3 fs-5"),
                        Span("Ready to print in PDF or Word", cls="text-white small fw-medium"),
                        cls="d-flex align-items-center mb-3",
                    ),
                    cls="pt-2",
                ),
                cls="my-auto",
            ),
            cls="p-4 p-lg-5 d-flex flex-column justify-content-between h-100",
            style="max-width: 500px; margin: 0 auto;",
        ),
        cls="col-12 col-lg-5 d-none d-lg-block min-vh-100",
        style="background-color: #00412E;",
    )

    right_form_panel = Div(
        Div(
            Div(
                A(
                    Icon("mortarboard-fill", cls="bi me-2 fs-4 text-brand"),
                    Span("SkuPhase", cls="fw-bold fs-4 text-dark"),
                    href="/",
                    cls="text-decoration-none d-flex align-items-center justify-content-center mb-4 d-lg-none",
                ),
                Div(*content),
                cls="w-100",
                style="max-width: 520px;",
            ),
            cls="d-flex align-items-center justify-content-center min-vh-100 p-3 p-md-4 py-5",
        ),
        cls="col-12 col-lg-7 min-vh-100",
        style="background-color: #E6ECE5; overflow-y: auto;",
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
    account_type = user.get("account_type") or ""
    role = user.get("role") or ("Teacher" if account_type == "individual_teacher" else "Staff")
    is_individual = account_type == "individual_teacher"
    is_school_admin = (not is_individual) and role == "school_admin"
    is_school_staff = (not is_individual) and (account_type == "school_staff" or role in {"school_admin", "teacher", "auditor"})
    school_name = user.get("school_name") or ("Personal Workspace" if is_individual else "Your School")

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
            Icon(icon, cls="bi app-sidebar-nav-icon"),
            Span(label, cls="app-sidebar-label"),
            href=href,
            cls="app-sidebar-link d-flex align-items-center" + (" active" if active == key else ""),
            title=label,
        )

    sidebar = Div(
        Div(
            A(
                Icon("mortarboard-fill", cls="bi me-2 fs-5 text-success"),
                Span("SkuPhase", cls="app-sidebar-label fw-bold fs-5 text-white"),
                href="/app",
                cls="app-sidebar-brand text-decoration-none d-flex align-items-center",
            ),
            Button(
                type="button",
                cls="btn-close btn-close-white d-lg-none ms-auto",
                **{"data-bs-dismiss": "offcanvas", "data-bs-target": "#appSidebar", "aria-label": "Close navigation menu"},
            ),
            Button(
                Icon("chevron-left", cls="bi text-white-50 small", id="appSidebarCollapseIcon"),
                type="button",
                id="appSidebarCollapse",
                cls="app-sidebar-collapse-btn d-none d-lg-inline-flex ms-auto",
                title="Collapse sidebar",
                **{"aria-label": "Collapse sidebar", "aria-expanded": "true"},
            ),
            cls="px-3 pt-4 pb-3 d-flex align-items-center justify-content-between",
        ),
        Nav(
            *[_nav_link(*item) for item in nav_items],
            cls="flex-column gap-1 px-2",
        ),
        Div(
            Span((role if role != "school_admin" else "SCHOOL ADMIN").upper(), cls="app-sidebar-role app-sidebar-label"),
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
                href="/app/exams" if is_individual else "/app/proposals",
                cls="app-topbar-bell me-3",
                title="My Exams" if is_individual else "Pending proposals & reviews",
            ),
            Div(
                HtmlButton(
                    Span(initials, cls="app-avatar me-2"),
                    Div(
                        Div(name.split()[0] if name else "Account", cls="small fw-semibold lh-1 text-start text-dark"),
                        Div(role.replace("_", " ").title(), cls="text-muted text-start", style="font-size:.68rem"),
                        cls="d-none d-sm-block me-1",
                    ),
                    Icon("chevron-down", cls="bi small text-muted ms-1"),
                    cls="btn app-user-btn text-decoration-none d-flex align-items-center dropdown-toggle shadow-none",
                    type="button",
                    **{"data-bs-toggle": "dropdown", "aria-expanded": "false"},
                ),
                Div(
                    Div(
                        Strong(name, cls="d-block text-truncate"),
                        Span(role.replace("_", " ").title(), cls="text-muted small"),
                        cls="px-3 py-2 border-bottom",
                    ),
                    A(
                        Icon("person-gear", cls="bi me-2 text-muted"),
                        "Account Settings",
                        href="/app/settings",
                        cls="dropdown-item py-2 small d-flex align-items-center",
                    ),
                    Div(cls="dropdown-divider my-1"),
                    Form(
                        HtmlButton(
                            Icon("box-arrow-right", cls="bi me-2 text-danger"),
                            "Sign out",
                            type="submit",
                            cls="dropdown-item py-2 small text-danger d-flex align-items-center border-0 bg-transparent w-100",
                        ),
                        action="/logout",
                        method="post",
                        cls="m-0",
                    ),
                    cls="dropdown-menu dropdown-menu-end shadow-sm border rounded-3 py-1",
                    style="min-width: 200px;",
                ),
                cls="dropdown ms-2",
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
                Main(Container(*content), cls="app-main py-4 pb-5 mb-4 mb-lg-0"),
                cls="app-content flex-grow-1 min-vh-100",
            ),
            cls="d-flex flex-column flex-lg-row",
        ),
        _bottom_nav(active),
        app_toast_container(flash_toast),
        Script("""
          (function () {
            var shell = document.currentScript && document.currentScript.parentElement;
            if (!shell) return;
            var toggle = shell.querySelector('#appSidebarCollapse');
            var icon = shell.querySelector('#appSidebarCollapseIcon');
            var key = 'skuphase.sidebar.collapsed';
            function apply(collapsed) {
              shell.classList.toggle('sidebar-collapsed', collapsed);
              if (toggle) {
                toggle.setAttribute('aria-expanded', String(!collapsed));
                toggle.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
                toggle.setAttribute('title', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
              }
              if (icon) icon.className = 'bi text-white-50 small ' + (collapsed ? 'bi-chevron-right' : 'bi-chevron-left');
            }
            try { apply(window.localStorage.getItem(key) === 'true'); } catch (_) { apply(false); }
            if (toggle) toggle.addEventListener('click', function () {
              var collapsed = !shell.classList.contains('sidebar-collapsed');
              apply(collapsed);
              try { window.localStorage.setItem(key, String(collapsed)); } catch (_) {}
            });
          })();
        """),
        cls="app-shell has-bottomnav",
    )
