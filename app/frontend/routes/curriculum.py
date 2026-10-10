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
    Textarea,
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
from app.services.curriculum_taxonomy import ALL_SUBJECTS, CLASS_LEVELS


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ALL_CLASSES = list(CLASS_LEVELS)
_DEFAULT_SUBJECTS = list(ALL_SUBJECTS)


async def _fetch_curriculum_data(req: Request, class_level: str, subject: str, term: str, board: str = "NERDC"):
    """Fetch classes, subjects, and weeks from the API. Returns (all_classes, subject_names, active_subject, class_level, weeks_list)."""
    term = _normalise_term(term)
    cls_resp = await call_api(req, "GET", "/curriculum/classes", params={"board": board})
    ok_cls, cls_data = unwrap(cls_resp)
    all_classes = (cls_data.get("classes") or []) if ok_cls else []
    if not all_classes:
        all_classes = _ALL_CLASSES[:]

    if class_level not in all_classes and all_classes:
        class_level = all_classes[0]

    sub_resp = await call_api(req, "GET", "/curriculum/subjects", params={"class_level": class_level, "board": board})
    ok_sub, sub_data = unwrap(sub_resp)
    subjects_list = (sub_data.get("subjects") or []) if ok_sub else []
    subject_names = [s["subject_name"] for s in subjects_list if isinstance(s, dict)] or _DEFAULT_SUBJECTS[:]

    # Ensure active subject exists in this class level's subjects
    if subject and subject in subject_names:
        active_subject = subject
    else:
        active_subject = subject_names[0] if subject_names else "Mathematics"

    weeks_resp = await call_api(
        req, "GET", "/curriculum/school/weeks",
        params={"class_level": class_level, "subject": active_subject, "term": term, "board": board},
    )
    ok_w, w_data = unwrap(weeks_resp)
    # Keep the explorer usable for deployments that have not yet migrated the
    # school-overlay endpoint, and for read-only/public curriculum fixtures.
    if not ok_w:
        weeks_resp = await call_api(
            req, "GET", "/curriculum/weeks",
            params={"class_level": class_level, "subject": active_subject, "term": term, "board": board},
        )
        ok_w, w_data = unwrap(weeks_resp)
    weeks_list = (w_data.get("weeks") or []) if (ok_w and isinstance(w_data, dict)) else []

    return all_classes, subject_names, active_subject, class_level, weeks_list


def _build_filter_card(all_classes, subject_names, class_level, active_subject, term, board="NERDC", boards=None):
    """Render the Class / Subject / Term filter card with HTMX wired selects."""
    class_options = [(c, c, c == class_level) for c in all_classes]
    subject_options = [(s, s, s == active_subject) for s in subject_names]

    return Card(
        # Hidden input for active term so HTMX includes current term when class/subject changes
        Input(type="hidden", name="term", value=term, id="curr-term-hidden"),
        Row(
            Col(
                Label("Curriculum Board", cls="form-label text-muted small fw-medium mb-1"),
                Select("board", *[(b, b, b == board) for b in (boards or ["NERDC"])], id="curriculum-board-select", cls="form-select rounded-3 border-0 py-2 px-3 fw-medium", style="background-color: #F4F6F4; font-size: 0.92rem;", hx_get="/ui/curriculum/content", hx_target="#curriculum-content", hx_swap="outerHTML", hx_trigger="change", hx_include="#curriculum-filter-form", hx_indicator="#curr-spinner"),
                span=12, md=4,
            ),
            Col(
                Label("Class / Grade Level", cls="form-label text-muted small fw-medium mb-1"),
                Select(
                    "class_level",
                    *class_options,
                    id="curriculum-class-select",
                    **{"aria-current": "true"},
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
                md=4,
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
                md=4,
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
                        cls=("btn btn-brand text-white fw-semibold" if t == term else "btn btn-outline-brand")
                        + " rounded-pill px-3 py-1 me-2",
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


def _build_timeline(weeks_list, class_level, active_subject, term, can_edit_local=False):
    """Render the weekly scheme timeline list.

    ``can_edit_local`` adds the per-week authoring affordance; teachers may
    correct local notes/resources, school admins may also correct shared text.
    """
    week_rows = []
    for w in weeks_list:
        w_num = w.get("week_number", 1)
        topic = w.get("topic", f"Week {w_num} Topics")
        objs = w.get("learning_objectives") or []
        week_id = w.get("id")

        badges = [
            Span(str(obj), cls="badge bg-light text-secondary border fw-normal text-truncate me-1 mb-1",
                 style="max-width: 280px; font-size: 0.78rem;")
            for obj in objs[:3]
        ]

        edit_action = (
            Button(
                Icon("pencil-square", cls="bi me-1"),
                "Edit week",
                hx_get=f"/ui/curriculum/week/{week_id}/edit",
                hx_target=f"#week-editor-{week_id}",
                hx_swap="innerHTML",
                cls="btn btn-sm btn-brand rounded-pill px-3 text-white",
                title="Correct imported text or add local notes",
                type="button",
            )
            if (can_edit_local and week_id)
            else None
        )

        week_badge = Span(
            f"Week {w_num}",
            cls="badge bg-success-subtle text-success border border-success-subtle fw-semibold",
            style="font-size: 0.82rem; min-width: 68px; text-align: center;",
        )

        # Surface school-local state on the card itself so corrections and
        # archived weeks are visible without opening the editor.
        state_badges = []
        if w.get("has_override"):
            state_badges.append(
                Span("Corrected", cls="badge bg-warning-subtle text-warning border border-warning-subtle fw-normal",
                     title=f"School-corrected. Seeded text: {w.get('seeded_topic', '')}",
                     style="font-size: 0.72rem;")
            )
        if w.get("is_archived"):
            state_badges.append(
                Span("Archived", cls="badge bg-secondary-subtle text-secondary border border-secondary-subtle fw-normal",
                     title="Archived for this school; excluded from coverage and exam generation.",
                     style="font-size: 0.72rem;")
            )
        if w.get("teacher_notes"):
            state_badges.append(
                Span(Icon("sticky", cls="bi me-1", title="Has local teacher notes"),
                     title="Has local teacher notes",
                     cls="badge bg-info-subtle text-info border border-info-subtle fw-normal",
                     style="font-size: 0.72rem;")
            )
        week_rows.append(
            Div(
                Div(
                    Div(
                        Input(
                            type="checkbox",
                            cls="form-check-input week-select-cb",
                            style="width: 1.25rem; height: 1.25rem; cursor: pointer;",
                            **{
                                "data-week": str(w_num),
                                "data-topic": str(topic),
                                "onchange": "syncWeekSelection()",
                            },
                        ),
                        week_badge,
                        *state_badges,
                        cls="curriculum-week-meta",
                    ),
                    Div(
                        Strong(topic, id=f"week-topic-{week_id}",
                               cls="fs-6 text-dark d-block mb-1"),
                        Div(*badges, cls="d-flex flex-wrap") if badges else P("Standard statutory competencies", cls="small text-muted mb-0"),
                        cls="flex-grow-1 me-3",
                    ),
                    Div(
                        *([edit_action] if edit_action is not None else []),
                        A(
                            Icon("lightning-charge-fill", cls="bi me-1"),
                            "Draft Exam",
                            href=f"/app/exams/new?class_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term)}&weeks={w_num}",
                            cls="btn btn-sm btn-outline-brand rounded-pill px-3 me-2",
                        ),

                        cls="d-flex flex-wrap align-items-center gap-2 mt-2 mt-md-0",
                    ),
                    cls="d-flex flex-column flex-md-row align-items-start align-items-md-center w-100",
                ),
                Div(id=f"week-editor-{week_id}"),
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
                if (summary) {{
                    summary.textContent = count === 0 ? '0 weeks selected' : count + ' week' + (count > 1 ? 's' : '') + ' selected (Weeks ' + weeks.join(', ') + ')';
                }}
                const baseUrl = '/app/exams/new?class_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term)}&weeks=' + weeks.join(',');
                if (draftBtn) {{
                    draftBtn.classList.toggle('disabled', count === 0);
                    draftBtn.href = count > 0 ? baseUrl : '#';
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


def _build_curriculum_content(all_classes, subject_names, class_level, active_subject, term, weeks_list, board="NERDC", boards=None, can_edit_local=False):
    """Build the full filter card + timeline, wrapped in the HTMX swap target div."""
    filter_card = _build_filter_card(all_classes, subject_names, class_level, active_subject, term, board, boards)
    timeline = _build_timeline(weeks_list, class_level, active_subject, term, can_edit_local)
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
        board: str = "NERDC",
    ):
        """HTMX partial — swaps #curriculum-content without a full page reload."""
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}

        all_classes, subject_names, active_subject, class_level, weeks_list = await _fetch_curriculum_data(
            req, class_level, subject, term, board
        )
        board_resp = await call_api(req, "GET", "/curriculum/boards")
        _, board_data = unwrap(board_resp)
        boards = board_data.get("boards", []) if isinstance(board_data, dict) else []
        content = _build_curriculum_content(all_classes, subject_names, class_level, active_subject, term, weeks_list, board, boards, _can_edit_local(user))
        push_url = f"/app/curriculum?class_level={quote(class_level)}&subject={quote(active_subject)}&term={quote(term)}&board={quote(board)}"
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
        board: str = "NERDC",
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
            Input(type="hidden", name="board", value=board),
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
            sr_resp = await call_api(req, "GET", "/curriculum/search", params={"q": q.strip(), "board": board})
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
                                    cls="rounded-pill px-3 me-2 btn-brand text-white",
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
                        A("Clear Search", href="/app/curriculum", cls="btn btn-sm btn-outline-brand rounded-pill"),
                        cls="p-5 text-center bg-white rounded-4 border shadow-sm",
                    )
                ),
            )
        else:
            # Normal browse view
            all_classes, subject_names, active_subject, class_level, weeks_list = await _fetch_curriculum_data(
                req, class_level, subject, term, board
            )
            board_resp = await call_api(req, "GET", "/curriculum/boards")
            _, board_data = unwrap(board_resp)
            boards = board_data.get("boards", []) if isinstance(board_data, dict) else []
            content_view = _build_curriculum_content(all_classes, subject_names, class_level, active_subject, term, weeks_list, board, boards, _can_edit_local(user))

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
# ---------------------------------------------------------------------------
# Curriculum authoring UI
# ---------------------------------------------------------------------------
# Schools repair imported curriculum text and attach local notes without ever
# mutating the shared seeded rows. The API enforces the role split; this panel
# mirrors it so teachers only see the fields they can write.


def _authoring_panel(detail: dict) -> Div:
    """Render the per-week authoring form for one scheme week."""
    week_id = detail.get("id", "")
    can_canonical = bool(detail.get("can_edit_canonical"))
    can_local = bool(detail.get("can_edit_local"))
    week_label = f"Week {detail.get('week_number', '')} · {detail.get('term', '')}"
    corrected = detail.get("topic") != detail.get("seeded_topic")
    subtopics = detail.get("subtopics") or []
    seeded_subtopics = detail.get("seeded_subtopics") or []

    header_bits = [
        Span(week_label, cls="badge bg-primary-subtle text-primary border border-primary-subtle"),
    ]
    if detail.get("has_override"):
        header_bits.append(
            Span("School Customization", cls="badge bg-warning-subtle text-warning border border-warning-subtle ms-2")
        )
    if detail.get("is_archived"):
        header_bits.append(
            Span("Archived", cls="badge bg-secondary-subtle text-secondary border border-secondary-subtle ms-2")
        )

    fields = []
    if can_canonical:
        fields.append(
            Div(
                Label("Topic", cls="form-label small fw-semibold text-muted mb-1"),
                Input(
                    type="text", name="topic", value=detail.get("topic", ""),
                    cls="form-control form-control-sm rounded-3", maxlength=255, required=True,
                ),
                (
                    P(f"Seeded text: {detail.get('seeded_topic', '')}",
                      cls="form-text small text-muted mb-0")
                    if corrected else None
                ),
                cls="col-12 mb-3",
            )
        )
        fields.append(
            Div(
                Label("Subtopics / objectives", cls="form-label small fw-semibold text-muted mb-1"),
                # Textarea renders its value as child content; a `value=` attribute
                # is ignored by browsers and would silently show (then wipe) nothing.
                Textarea("\n".join(subtopics), name="subtopics", rows="6",
                         cls="form-control form-control-sm rounded-3"),
                P(
                    f"Seed had {len(seeded_subtopics)} line(s). One subtopic per line."
                    if len(subtopics) != len(seeded_subtopics)
                    else "One subtopic per line.",
                    cls="form-text small text-muted mb-0",
                ),
                cls="col-12 mb-3",
            )
        )
    else:
        fields.append(
            Div(
                Label("Topic (read-only)", cls="form-label small fw-semibold text-muted mb-1"),
                Input(type="text", value=detail.get("topic", ""),
                      cls="form-control form-control-sm rounded-3", disabled=True),
                P("Only a school administrator can correct shared curriculum text.",
                  cls="form-text small text-muted mb-0"),
                cls="col-12 mb-3",
            )
        )

    if can_local:
        fields.append(
            Div(
                Label("Local teacher notes", cls="form-label small fw-semibold text-muted mb-1"),
                Textarea(detail.get("teacher_notes") or "", name="teacher_notes", rows="3",
                         cls="form-control form-control-sm rounded-3",
                         placeholder="Context for this school — local examples, adjustments, differentiation."),
                cls="col-12 mb-3",
            )
        )
        fields.append(
            Div(
                Label("Instructional resources", cls="form-label small fw-semibold text-muted mb-1"),
                Textarea("\n".join(detail.get("resources") or []), name="resources", rows="3",
                         cls="form-control form-control-sm rounded-3",
                         placeholder="One resource per line (chart, real device, worksheet link...)."),
                cls="col-12 mb-3",
            )
        )

    actions = [
        Button(Icon("check-lg", cls="bi me-1"), "Save corrections", type="submit",
               variant="success", cls="btn-brand rounded-pill px-4")
    ]
    if detail.get("has_override"):
        actions.append(
            Button(Icon("arrow-counterclockwise", cls="bi me-1"),
                   "Revert to official national curriculum", type="button",
                   hx_post=f"/ui/curriculum/week/{week_id}/revert",
                   hx_target=f"#week-editor-{week_id}", hx_swap="innerHTML",
                   cls="btn btn-sm btn-outline-secondary rounded-pill px-3")
        )
        actions.append(
            Button(Icon("x-lg", cls="bi me-1"), "Close", type="button",
                   hx_get=f"/ui/curriculum/week/{week_id}/close",
                   hx_target=f"#week-editor-{week_id}", hx_swap="innerHTML",
                   cls="btn btn-sm btn-link text-muted ms-1")
        )

    archive_toggle = None
    if can_canonical:
        archive_toggle = Label(
            Input(type="checkbox", name="is_archived", value="1",
                  checked=bool(detail.get("is_archived")), cls="form-check-input me-2"),
            "Archive this week for my school",
            cls="form-check-label small text-muted",
        )

    return Div(
        Div(
            Div(*header_bits, cls="d-flex flex-wrap align-items-center"),
            Button(Icon("x-lg"), type="button",
                   hx_get=f"/ui/curriculum/week/{week_id}/close",
                   hx_target=f"#week-editor-{week_id}", hx_swap="innerHTML",
                   cls="btn btn-sm btn-link text-muted ms-auto", aria_label="Close editor"),
            cls="d-flex align-items-center mb-3",
        ),
        Form(
            Div(*fields, cls="row"),
            *([archive_toggle] if archive_toggle is not None else []),
            Div(*actions, cls="d-flex flex-wrap align-items-center gap-2 mt-3"),
            hx_post=f"/ui/curriculum/week/{week_id}/save",
            hx_target=f"#week-editor-{week_id}", hx_swap="innerHTML",
            cls="curriculum-authoring-form",
        ),
        Div(id=f"week-editor-result-{week_id}"),
        cls="curriculum-authoring-panel border rounded-4 bg-white p-3 mt-3 shadow-xs",
    )


def _authoring_error(message: str, tone: str = "danger") -> Div:
    """Inline, screen-reader-announced feedback inside the editor panel."""
    return Div(
        Div(Icon("exclamation-triangle-fill", cls="bi me-2"),
            Span(message, cls="small"),
            cls="d-flex align-items-center"),
        cls=f"alert alert-{tone} d-flex align-items-center py-2 px-3 mt-3 mb-0 small rounded-3",
        role="alert",
    )


#: Query-string term values mapped onto the canonical API term names. The
#: explorer accepts the short ``/app/curriculum?term=first`` form used in links,
#: but the API stores full names, so an unmatched value silently yields the
#: empty-state instead of the scheme of work.
_TERM_ALIASES = {
    "first": "First Term",
    "first term": "First Term",
    "second": "Second Term",
    "second term": "Second Term",
    "third": "Third Term",
    "third term": "Third Term",
}


def _normalise_term(term: str) -> str:
    """Resolve a term query value to a canonical term name."""
    if not term:
        return "First Term"
    return _TERM_ALIASES.get(term.strip().lower(), term.strip())


def _can_edit_local(user: dict) -> bool:
    """True when the user may author curriculum corrections/notes."""
    return (user or {}).get("role") in {"teacher", "school_admin"}


def _lines_to_list(raw: str) -> list[str]:
    """Split a textarea into trimmed, non-empty lines."""
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


def _oob_topic(week_id: str, topic: str):
    """Out-of-band node that refreshes the week card title after a save/revert."""
    return Strong(topic, id=f"week-topic-{week_id}", hx_swap_oob="true",
                  cls="fs-6 text-dark d-block mb-1")


def register_curriculum_authoring_routes(app):
    """School-scoped curriculum authoring endpoints (HTMX partials)."""

    async def _detail(req: Request, week_id: str):
        resp = await call_api(req, "GET", f"/curriculum/weeks/{week_id}")
        return unwrap(resp)

    @app.get("/ui/curriculum/week/{week_id}/edit")
    async def week_editor(req: Request, week_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        ok, detail = await _detail(req, week_id)
        if not ok or not isinstance(detail, dict):
            return _authoring_error(
                (detail or {}).get("message", "This week could not be loaded.")
                if isinstance(detail, dict)
                else "This week could not be loaded."
            )
        if not detail.get("can_edit_local"):
            return _authoring_error("You do not have access to curriculum authoring.")
        return _authoring_panel(detail)

    @app.post("/ui/curriculum/week/{week_id}/save")
    async def week_save(req: Request, week_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        payload: dict = {}
        if "topic" in form:
            payload["topic"] = str(form.get("topic", "")).strip()
        if "subtopics" in form:
            payload["subtopics"] = _lines_to_list(str(form.get("subtopics", "")))
        if "teacher_notes" in form:
            payload["teacher_notes"] = str(form.get("teacher_notes", "")).strip() or None
        if "resources" in form:
            payload["resources"] = _lines_to_list(str(form.get("resources", "")))
        if "is_archived" in form:
            payload["is_archived"] = str(form.get("is_archived")) == "1"

        resp = await call_api(req, "PATCH", f"/curriculum/weeks/{week_id}", json=payload)
        ok, detail = unwrap(resp)
        if not ok:
            message = (detail or {}).get("message", "We could not save your changes.")
            return Div(
                _authoring_error(str(message)),
                Div(
                    Button("Try again", type="button",
                           hx_get=f"/ui/curriculum/week/{week_id}/edit",
                           hx_target=f"#week-editor-{week_id}", hx_swap="innerHTML",
                           cls="btn btn-sm btn-outline-secondary rounded-pill px-3 mt-2"),
                ),
            )
        return Div(
            Div(
                Div(Icon("check-circle-fill", cls="bi me-2"), Span("Saved for your school."),
                    cls="d-flex align-items-center"),
                cls="alert alert-success d-flex align-items-center py-2 px-3 mt-3 mb-0 small rounded-3",
                role="status",
            ),
            _authoring_panel(detail),
            _oob_topic(week_id, detail.get("topic", "")),
        )

    @app.post("/ui/curriculum/week/{week_id}/revert")
    async def week_revert(req: Request, week_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "DELETE", f"/curriculum/weeks/{week_id}")
        ok, detail = unwrap(resp)
        if not ok:
            message = (detail or {}).get("message", "We could not revert this week.") \
                if isinstance(detail, dict) else "We could not revert this week."
            return _authoring_error(str(message))
        return Div(
            Div(
                Div(Icon("check-circle-fill", cls="bi me-2"),
                    Span("Reverted to the seeded curriculum text.", cls="small"),
                    cls="d-flex align-items-center"),
                cls="alert alert-success d-flex align-items-center py-2 px-3 mt-3 mb-0 small rounded-3",
                role="status",
            ),
            _authoring_panel(detail),
            _oob_topic(week_id, detail.get("topic", "")),
        )

    @app.get("/ui/curriculum/week/{week_id}/close")
    async def week_editor_close(req: Request, week_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        return Div()
