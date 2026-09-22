"""Curriculum and Scheme of Work Explorer (/app/curriculum).

Allows teachers and school admins to browse official NERDC primary school
curricula, search topics/objectives, and trigger exam generation pre-seeded
with selected scheme weeks.
"""

from urllib.parse import quote

from fasthtml.common import (
    A,
    Div,
    Form,
    H1,
    H2,
    Input,
    Label,
    Li,
    P,
    Script,
    Span,
    Strong,
    Ul,
    to_xml,
)
from faststrap import Button, Card, Col, Container, Icon, Row, Select, Spinner
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ALL_CLASSES = [
    "Pre-Nursery", "Nursery 1", "Nursery 2", "Nursery 3",
    "Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6",
]

_DEFAULT_SUBJECTS = [
    "Mathematics", "English Language", "Basic Science", "Social Studies", "National Values",
]


async def _fetch_curriculum_data(req: Request, class_level: str, subject: str, term: str):
    """Fetch classes, subjects, and weeks from the API. Returns (all_classes, subject_names, active_subject, class_level, weeks_list)."""
    cls_resp = await call_api(req, "GET", "/curriculum/classes")
    ok_cls, cls_data = unwrap(cls_resp)
    all_classes = (cls_data.get("classes") or []) if ok_cls else []
    if not all_classes:
        all_classes = _ALL_CLASSES[:]

    if class_level not in all_classes and all_classes:
        class_level = all_classes[0]

    sub_resp = await call_api(req, "GET", "/curriculum/subjects", params={"class_level": class_level})
    ok_sub, sub_data = unwrap(sub_resp)
    subjects_list = (sub_data.get("subjects") or []) if ok_sub else []
    subject_names = [s["subject_name"] for s in subjects_list if isinstance(s, dict)] or _DEFAULT_SUBJECTS[:]

    # Ensure active subject exists in this class level's subjects
    if subject and subject in subject_names:
        active_subject = subject
    else:
        active_subject = subject_names[0] if subject_names else "Mathematics"

    weeks_resp = await call_api(
        req, "GET", "/curriculum/weeks",
        params={"class_level": class_level, "subject": active_subject, "term": term},
    )
    ok_w, w_data = unwrap(weeks_resp)
    weeks_list = (w_data.get("weeks") or []) if (ok_w and isinstance(w_data, dict)) else []

    return all_classes, subject_names, active_subject, class_level, weeks_list


def _build_filter_card(all_classes, subject_names, class_level, active_subject, term):
    """Render the Class / Subject / Term filter card with HTMX wired selects."""
    class_options = [(c, c, c == class_level) for c in all_classes]
    subject_options = [(s, s, s == active_subject) for s in subject_names]

    return Card(
        # Hidden input for active term so HTMX includes current term when class/subject changes
        Input(type="hidden", name="term", value=term, id="curr-term-hidden"),
        Row(
            Col(
                Label("Class / Grade Level", cls="form-label text-muted small fw-medium mb-1"),
                Select(
                    "class_level",
                    *class_options,
                    id="curriculum-class-select",
                    cls="form-select rounded-3 border-0 py-2 px-3 fw-medium",
                    style="background-color: #F4F6F4; font-size: 0.92rem;",
                    hx_get="/ui/curriculum/content",
                    hx_target="#curriculum-content",
                    hx_swap="outerHTML",
                    hx_trigger="change",
                    hx_include="#curriculum-filter-form",
                    hx_indicator="#curr-spinner",
                ),
                span=12,
                md=6,
            ),
            Col(
                Label("Subject", cls="form-label text-muted small fw-medium mb-1"),
                Select(
                    "subject",
                    *subject_options,
                    id="curriculum-subject-select",
                    cls="form-select rounded-3 border-0 py-2 px-3 fw-medium",
                    style="background-color: #F4F6F4; font-size: 0.92rem;",
                    hx_get="/ui/curriculum/content",
                    hx_target="#curriculum-content",
                    hx_swap="outerHTML",
                    hx_trigger="change",
                    hx_include="#curriculum-filter-form",
                    hx_indicator="#curr-spinner",
                ),
                span=12,
                md=6,
            ),
            g=3,
            cls="mb-3",
        ),
        Div(
            Label("Term", cls="form-label text-muted small fw-medium mb-1 d-block"),
            Div(
                *[
                    Button(
                        f"{t.title()} Term",
                        type="button",
                        variant=("dark" if t == term else "light"),
                        cls="rounded-pill px-3 py-1 me-2 border"
                        + (" text-white fw-semibold" if t == term else " text-muted"),
                        # Each term pill does an HTMX swap with the new term value
                        hx_get=f"/ui/curriculum/content?term={t}",
                        hx_target="#curriculum-content",
                        hx_swap="outerHTML",
                        hx_include="#curriculum-filter-form",
                        hx_indicator="#curr-spinner",
                        onclick=f"document.getElementById('curr-term-hidden').value='{t}'",
                        **{"data-term": t},
                    )
                    for t in ["first", "second", "third"]
                ],
                cls="d-flex flex-wrap gap-1",
            ),
        ),
        # Faststrap loading spinner shown while HTMX request is in-flight
        Div(
            Spinner(variant="success", size="sm", cls="me-2"),
            Span("Updating curriculum...", cls="small text-muted"),
            id="curr-spinner",
            cls="htmx-indicator mt-2",
        ),
        id="curriculum-filter-form",
        cls="bg-white rounded-4 border p-4 shadow-sm mb-4",
    )


def _build_timeline(weeks_list, class_level, active_subject, term):
    """Render the weekly scheme timeline list."""
    week_rows = []
    for w in weeks_list:
        w_num = w.get("week_number", 1)
        topic = w.get("topic", f"Week {w_num} Topics")
        objs = w.get("learning_objectives") or []

        badges = [
            Span(str(obj), cls="badge bg-light text-secondary border fw-normal text-truncate me-1 mb-1",
                 style="max-width: 280px; font-size: 0.78rem;")
            for obj in objs[:3]
        ]

        week_rows.append(
            Div(
                Div(
                    Input(
                        type="checkbox",
                        cls="form-check-input week-select-cb me-3",
                        style="width: 1.25rem; height: 1.25rem; cursor: pointer;",
                        **{
                            "data-week": str(w_num),
                            "data-topic": str(topic),
                            "onchange": "syncWeekSelection()",
                        },
                    ),
                    Span(
                        f"Week {w_num}",
                        cls="badge bg-success-subtle text-success border border-success-subtle fw-semibold me-3",
                        style="font-size: 0.82rem; min-width: 68px; text-align: center;",
                    ),
                    Div(
                        Strong(topic, cls="fs-6 text-dark d-block mb-1"),
                        Div(*badges, cls="d-flex flex-wrap") if badges else P("Standard statutory competencies", cls="small text-muted mb-0"),
                        cls="flex-grow-1 me-3",
                    ),
                    Div(
                        A(
                            Icon("lightning-charge-fill", cls="bi me-1"),
                            "Draft Exam",
                            href=f"/app/exams/new?class_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term)}&weeks={w_num}",
                            cls="btn btn-sm btn-outline-success rounded-pill px-3 me-2",
                        ),
                        A(
                            Icon("send", cls="bi me-1"),
                            "Propose",
                            href=f"/app/proposals/new?grade_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term.title() + ' Term')}&selected_weeks={w_num}&desired_outcomes={quote(topic)}",
                            cls="btn btn-sm btn-outline-secondary rounded-pill px-2",
                            title="Propose this week to school admin",
                        ),
                        cls="d-flex align-items-center mt-2 mt-md-0",
                    ),
                    cls="d-flex flex-column flex-md-row align-items-start align-items-md-center w-100",
                ),
                cls="p-3 bg-white rounded-4 border shadow-xs mb-3 week-item-card transition-all",
            )
        )

    if not week_rows:
        return Div(
            Div(
                Icon("journal-bookmark", cls="bi text-muted fs-1 mb-2 d-block"),
                Strong(f"Scheme of Work for {active_subject} ({class_level})", cls="d-block text-dark mb-1"),
                P(
                    f"Standard NERDC curriculum topics for {class_level} {active_subject} are fully available for AI exam generation.",
                    cls="text-muted small mb-4",
                ),
                Button(
                    Icon("plus-lg", cls="bi me-1"),
                    f"Generate {active_subject} Exam",
                    as_="a",
                    href=f"/app/exams/new?class_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term)}",
                    variant="success",
                    cls="btn-brand rounded-pill px-4",
                ),
                cls="p-5 text-center bg-white rounded-4 border shadow-sm",
            )
        )

    # Batch action bar
    batch_bar = Div(
        Div(
            Div(
                Input(
                    type="checkbox",
                    id="select-all-weeks-cb",
                    cls="form-check-input me-2",
                    style="cursor: pointer;",
                    onchange="toggleSelectAllWeeks(this.checked)",
                ),
                Label("Select All Weeks", for_="select-all-weeks-cb", cls="small fw-semibold text-dark me-3 cursor-pointer mb-0"),
                Span("0 weeks selected", id="selected-weeks-summary", cls="small text-muted"),
                cls="d-flex align-items-center",
            ),
            Div(
                A(
                    Icon("lightning-charge-fill", cls="bi me-1"),
                    "Draft Exam from Selected",
                    id="batch-draft-btn",
                    href="#",
                    cls="btn btn-sm btn-brand text-white rounded-pill px-3 me-2 disabled",
                    style="background-color: #00412E;",
                ),
                A(
                    Icon("send", cls="bi me-1"),
                    "Submit as Proposal",
                    id="batch-propose-btn",
                    href="#",
                    cls="btn btn-sm btn-outline-dark rounded-pill px-3 disabled",
                ),
                cls="d-flex align-items-center mt-2 mt-sm-0",
            ),
            cls="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center p-3",
        ),
        cls="bg-light border rounded-4 shadow-sm mb-4 sticky-top",
        style="top: 1rem; z-index: 10;",
    )

    return Div(
        batch_bar,
        Div(*week_rows, id="curriculum-weeks-list"),
        Script(f"""
        (function() {{
            function syncWeekSelection() {{
                const checked = Array.from(document.querySelectorAll('.week-select-cb:checked'));
                const weeks = checked.map(cb => cb.getAttribute('data-week'));
                const topics = checked.map(cb => cb.getAttribute('data-topic')).filter(Boolean);
                const count = weeks.length;
                const summary = document.getElementById('selected-weeks-summary');
                const draftBtn = document.getElementById('batch-draft-btn');
                const proposeBtn = document.getElementById('batch-propose-btn');
                if (summary) {{
                    summary.textContent = count === 0 ? '0 weeks selected' : count + ' week' + (count > 1 ? 's' : '') + ' selected (Weeks ' + weeks.join(', ') + ')';
                }}
                const baseUrl = '/app/exams/new?class_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term)}&weeks=' + weeks.join(',');
                const propUrl = '/app/proposals/new?grade_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term.title() + " Term")}&selected_weeks=' + weeks.join(',') + '&desired_outcomes=' + encodeURIComponent(topics.join('; '));
                if (draftBtn) {{
                    draftBtn.classList.toggle('disabled', count === 0);
                    draftBtn.href = count > 0 ? baseUrl : '#';
                }}
                if (proposeBtn) {{
                    proposeBtn.classList.toggle('disabled', count === 0);
                    proposeBtn.href = count > 0 ? propUrl : '#';
                }}
            }}
            function toggleSelectAllWeeks(select) {{
                document.querySelectorAll('.week-select-cb').forEach(cb => {{ cb.checked = select; }});
                syncWeekSelection();
            }}
            window.syncWeekSelection = syncWeekSelection;
            window.toggleSelectAllWeeks = toggleSelectAllWeeks;
        }})();
        """),
    )


def _build_curriculum_content(all_classes, subject_names, class_level, active_subject, term, weeks_list):
    """Build the full filter card + timeline, wrapped in the HTMX swap target div."""
    filter_card = _build_filter_card(all_classes, subject_names, class_level, active_subject, term)
    timeline = _build_timeline(weeks_list, class_level, active_subject, term)
    return Div(
        filter_card,
        timeline,
        id="curriculum-content",
    )


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def curriculum_routes(app):

    # ------------------------------------------------------------------
    # HTMX partial: returns just the content section (filter + timeline)
    # ------------------------------------------------------------------
    @app.get("/ui/curriculum/content")
    async def curriculum_content_partial(
        req: Request,
        class_level: str = "Primary 4",
        subject: str = "",
        term: str = "first",
    ):
        """HTMX partial — swaps #curriculum-content without a full page reload."""
        guard = ensure_login(req)
        if guard:
            return guard

        all_classes, subject_names, active_subject, class_level, weeks_list = await _fetch_curriculum_data(
            req, class_level, subject, term
        )
        content = _build_curriculum_content(all_classes, subject_names, class_level, active_subject, term, weeks_list)
        push_url = f"/app/curriculum?class_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term)}"
        return HTMLResponse(to_xml(content), headers={"HX-Push-Url": push_url})

    # ------------------------------------------------------------------
    # Full page
    # ------------------------------------------------------------------
    @app.get("/app/curriculum")
    async def curriculum_browser(
        req: Request,
        class_level: str = "Primary 4",
        subject: str = "",
        term: str = "first",
        q: str = "",
    ):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}

        # Hero Header
        header = Div(
            Div(
                Div(Icon("journal-bookmark", cls="bi"), cls="app-curriculum-hero-icon"),
                H1("National Curriculum & Scheme of Work", cls="fs-3 fw-bold text-dark mb-1"),
                P(
                    "Browse the official NERDC syllabus by class, subject, term and week, or search competencies directly.",
                    cls="text-muted small mb-0",
                ),
                cls="app-curriculum-hero-copy",
            ),
            cls="app-curriculum-hero mb-4",
        )

        # Search Bar
        search_form = Form(
            Div(
                Icon("search", cls="bi position-absolute text-muted", style="top:0.75rem; left:1rem; font-size:1rem;"),
                Input(
                    type="text",
                    name="q",
                    value=q,
                    placeholder="Search curriculum topics, learning objectives, or competencies...",
                    cls="form-control rounded-pill ps-5 py-2 border shadow-sm app-curriculum-search-input",
                    style="background:#fff;",
                ),
                Button("Search", type="submit", variant="success", cls="position-absolute end-0 top-0 bottom-0 rounded-pill px-4 m-1 btn-brand"),
                cls="position-relative mb-4 app-curriculum-search",
                style="max-width: 680px;",
            ),
            action="/app/curriculum",
            method="get",
        )

        if q.strip():
            # Search results view
            sr_resp = await call_api(req, "GET", "/curriculum/search", params={"q": q.strip()})
            ok_sr, sr_data = unwrap(sr_resp)
            search_results = sr_data if (ok_sr and isinstance(sr_data, list)) else []

            res_cards = []
            for item in search_results:
                c_lvl = item.get("class_level", "")
                s_name = item.get("subject_name", "")
                t_val = item.get("term", "")
                w_num = item.get("week_number", "")
                topic = item.get("topic", "")
                objs = item.get("learning_objectives") or []
                res_cards.append(
                    Card(
                        Div(
                            Div(
                                Span(f"{c_lvl} · {s_name}", cls="badge bg-light text-dark border me-2"),
                                Span(f"{t_val.title()} Term · Week {w_num}", cls="badge bg-success-subtle text-success border border-success-subtle"),
                                cls="mb-2",
                            ),
                            Strong(topic, cls="fs-6 text-dark d-block mb-2"),
                            Ul(*[Li(str(o), cls="text-muted small") for o in objs[:3]], cls="ps-3 mb-3") if objs else None,
                            Div(
                                Button(
                                    Icon("lightning-charge-fill", cls="bi me-1"),
                                    "Draft Exam",
                                    as_="a",
                                    href=f"/app/exams/new?class_level={quote(c_lvl)}&subject={quote(s_name)}&term={quote(t_val)}&weeks={w_num}",
                                    variant="success",
                                    size="sm",
                                    cls="rounded-pill px-3 me-2 btn-brand",
                                ),
                                Button(
                                    Icon("send", cls="bi me-1"),
                                    "Propose",
                                    as_="a",
                                    href=f"/app/proposals/new?grade_level={quote(c_lvl)}&subject={quote(s_name)}&term={quote(t_val.title() + ' Term')}&selected_weeks={w_num}&desired_outcomes={quote(topic)}",
                                    variant="outline-secondary",
                                    size="sm",
                                    cls="rounded-pill px-3",
                                ),
                                cls="mt-auto d-flex flex-wrap gap-2",
                            ),
                            cls="p-3 d-flex flex-column h-100",
                        ),
                        cls="h-100 border rounded-4 shadow-sm bg-white",
                    )
                )

            content_view = Div(
                Div(
                    A("← Back to full curriculum", href="/app/curriculum", cls="btn btn-sm btn-outline-secondary rounded-pill mb-3"),
                    H2(f"Search results for \"{q}\" ({len(search_results)} found)", cls="fs-5 fw-bold text-dark mb-4"),
                ),
                Row(*[Col(card, span=12, md=6, lg=4) for card in res_cards], g=3) if res_cards else Div(
                    Div(
                        Icon("search", cls="bi text-muted fs-1 mb-2 d-block"),
                        P(f"No curriculum entries matched \"{q}\". Try a broader topic like \"Fractions\", \"Living Things\", or \"Civic Values\".", cls="text-muted small mb-3"),
                        A("Clear Search", href="/app/curriculum", cls="btn btn-sm btn-outline-success rounded-pill"),
                        cls="p-5 text-center bg-white rounded-4 border shadow-sm",
                    )
                ),
            )
        else:
            # Normal browse view
            all_classes, subject_names, active_subject, class_level, weeks_list = await _fetch_curriculum_data(
                req, class_level, subject, term
            )
            content_view = _build_curriculum_content(all_classes, subject_names, class_level, active_subject, term, weeks_list)

        return AppShell(
            Container(
                header,
                search_form,
                content_view,
                cls="py-4 pt-lg-5",
            ),
            user=user,
            active="curriculum",
            crumbs=[("Curriculum", None)],
        )

    @app.get("/app/curriculum/{class_level}")
    async def curriculum_by_class(req: Request, class_level: str):
        """Clean URL: /app/curriculum/Primary%203 -> curriculum_browser."""
        return RedirectResponse(f"/app/curriculum?class_level={class_level}", status_code=302)

    @app.get("/app/curriculum/{class_level}/{term}")
    async def curriculum_by_class_term(req: Request, class_level: str, term: str):
        """Clean URL: /app/curriculum/Primary%203/first -> curriculum_browser."""
        return RedirectResponse(f"/app/curriculum?class_level={class_level}&term={term}", status_code=302)
