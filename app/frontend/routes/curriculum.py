"""Curriculum and Scheme of Work Explorer (/app/curriculum).

Allows teachers and school admins to browse official NERDC primary school
curricula, search topics/objectives, and trigger exam generation pre-seeded
with selected scheme weeks.
"""

from fasthtml.common import A, Div, Form, H1, H2, H3, Input, Li, P, Span, Strong, Ul
from faststrap import Button, Card, Col, Container, Icon, Row
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.frontend.api import call_api, unwrap
from app.frontend.components.feedback import push_flash
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login


def curriculum_routes(app):
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

        # 2. Fetch all classes
        cls_resp = await call_api(req, "GET", "/curriculum/classes")
        ok_cls, cls_data = unwrap(cls_resp)
        all_classes = (cls_data.get("classes") or []) if ok_cls else []
        if not all_classes:
            all_classes = [
                "Pre-Nursery", "Nursery 1", "Nursery 2", "Nursery 3",
                "Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6",
            ]

        if class_level not in all_classes and all_classes:
            class_level = all_classes[0]

        # 3. Handle live search
        search_results = []
        if q.strip():
            sr_resp = await call_api(req, "GET", "/curriculum/search", params={"q": q.strip()})
            ok_sr, sr_data = unwrap(sr_resp)
            if ok_sr and isinstance(sr_data, list):
                search_results = sr_data

        # 4. Fetch subjects for active class
        sub_resp = await call_api(req, "GET", "/curriculum/subjects", params={"class_level": class_level})
        ok_sub, sub_data = unwrap(sub_resp)
        subjects_list = (sub_data.get("subjects") or []) if ok_sub else []
        subject_names = [s["subject_name"] for s in subjects_list if isinstance(s, dict)] or [
            "Mathematics", "English Language", "Basic Science", "Social Studies", "National Values",
        ]

        active_subject = subject or (subject_names[0] if subject_names else "Mathematics")

        # 5. Fetch weeks for active subject & term
        weeks_list = []
        if not q.strip():
            weeks_resp = await call_api(
                req,
                "GET",
                "/curriculum/weeks",
                params={"class_level": class_level, "subject": active_subject, "term": term},
            )
            ok_w, w_data = unwrap(weeks_resp)
            if ok_w and isinstance(w_data, dict):
                weeks_list = w_data.get("weeks") or []

        # --- Build UI Components ---
        # Header
        header = Div(
            Div(
                H1("National Curriculum & Scheme of Work", cls="fs-3 fw-bold text-dark mb-1"),
                P(
                    "Official NERDC primary syllabus. Browse weekly topics and learning objectives, or search by topic.",
                    cls="text-muted small mb-0",
                ),
            ),
            cls="mb-4",
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
                    cls="form-control rounded-pill ps-5 py-2 border shadow-sm",
                ),
                Button("Search", type="submit", variant="success", cls="position-absolute end-0 top-0 bottom-0 rounded-pill px-4 m-1"),
                cls="position-relative mb-4",
                style="max-width: 680px;",
            ),
            action="/app/curriculum",
            method="get",
        )

        if q.strip():
            # Display Search Results View
            res_cards = []
            if search_results:
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
                                        "Generate Exam from this Topic",
                                        as_="a",
                                        href=f"/app/exams/new?class_level={c_lvl}&subject={s_name}&term={t_val}&weeks={w_num}",
                                        variant="success",
                                        size="sm",
                                        cls="rounded-pill",
                                    ),
                                    cls="mt-auto",
                                ),
                                cls="p-3 d-flex flex-column h-100",
                            ),
                            cls="h-100 border-0 shadow-sm",
                        )
                    )
            content_view = Div(
                Div(
                    A("← Back to full curriculum", href="/app/curriculum", cls="btn btn-sm btn-outline-secondary rounded-pill mb-3"),
                    H2(f"Search results for “{q}” ({len(search_results)} found)", cls="fs-5 fw-bold text-dark mb-4"),
                ),
                Row(*[Col(card, span=12, md=6, lg=4) for card in res_cards], g=3) if res_cards else Div(
                    Div(
                        Icon("search", cls="bi text-muted fs-1 mb-2 d-block"),
                        P(f"No curriculum entries matched “{q}”. Try a broader topic like “Fractions”, “Living Things”, or “Civic Values”.", cls="text-muted small mb-3"),
                        A("Clear Search", href="/app/curriculum", cls="btn btn-sm btn-outline-success rounded-pill"),
                        cls="p-5 text-center bg-white rounded-3 border shadow-sm",
                    )
                ),
            )
        else:
            # Class selector pills
            class_pills = Div(
                *[
                    A(
                        c,
                        href=f"/app/curriculum?class_level={c}",
                        cls="badge text-decoration-none px-3 py-2 me-2 mb-2 " + (
                            "bg-dark text-white" if c == class_level else "bg-light text-secondary border"
                        ),
                        **({"aria-current": "true"} if c == class_level else {}),
                    )
                    for c in all_classes
                ],
                cls="d-flex flex-wrap mb-3",
            )

            # Subject selector buttons
            subject_pills = Div(
                *[
                    A(
                        s,
                        href=f"/app/curriculum?class_level={class_level}&subject={s}&term={term}",
                        cls="btn btn-sm rounded-pill me-2 mb-2 " + (
                            "btn-success" if s == active_subject else "btn-outline-secondary"
                        ),
                        **({"aria-current": "true"} if s == active_subject else {}),
                    )
                    for s in subject_names
                ],
                cls="d-flex flex-wrap mb-4",
            )

            # Term selector strip
            term_tabs = Div(
                *[
                    A(
                        f"{t.title()} Term",
                        href=f"/app/curriculum?class_level={class_level}&subject={active_subject}&term={t}",
                        cls="btn btn-sm " + ("btn-dark active fw-semibold" if t == term else "btn-light border text-muted"),
                    )
                    for t in ["first", "second", "third"]
                ],
                cls="btn-group mb-4 shadow-sm",
            )

            # Weeks list cards
            week_cards = []
            for w in weeks_list:
                w_num = w.get("week_number", 1)
                topic = w.get("topic", f"Week {w_num} Topics")
                objs = w.get("learning_objectives") or []
                week_cards.append(
                    Col(
                        Card(
                            Div(
                                Div(
                                    Span(f"Week {w_num}", cls="badge bg-success-subtle text-success border border-success-subtle fw-semibold me-2"),
                                    Span(f"{active_subject} · {class_level}", cls="text-muted small"),
                                    cls="d-flex align-items-center mb-2",
                                ),
                                Strong(topic, cls="fs-6 text-dark d-block mb-3"),
                                P("Performance Objectives:", cls="small fw-semibold text-secondary mb-1") if objs else None,
                                Ul(*[Li(str(o), cls="text-muted small") for o in objs], cls="ps-3 mb-3") if objs else None,
                                Div(
                                    Button(
                                        Icon("lightning-charge-fill", cls="bi me-1"),
                                        f"Draft Exam from Week {w_num}",
                                        as_="a",
                                        href=f"/app/exams/new?class_level={class_level}&subject={active_subject}&term={term}&weeks={w_num}",
                                        variant="outline-success",
                                        size="sm",
                                        cls="rounded-pill w-100 mt-2",
                                    ),
                                    cls="mt-auto pt-2 border-top",
                                ),
                                cls="p-3 d-flex flex-column h-100",
                            ),
                            cls="h-100 border-0 shadow-sm",
                        ),
                        span=12, md=6, lg=4,
                    )
                )

            if not week_cards:
                empty_scheme = Div(
                    Div(
                        Icon("journal-bookmark", cls="bi text-muted fs-1 mb-2 d-block"),
                        Strong(f"Scheme of Work for {active_subject} ({class_level})", cls="d-block text-dark mb-1"),
                        P(
                            f"Standard NERDC curriculum topics for {class_level} are fully available for AI exam generation.",
                            cls="text-muted small mb-4",
                        ),
                        Button(
                            Icon("plus-lg", cls="bi me-1"),
                            f"Generate {active_subject} Exam",
                            as_="a",
                            href=f"/app/exams/new?class_level={class_level}&subject={active_subject}&term={term}",
                            variant="success",
                            cls="rounded-pill px-4",
                        ),
                        cls="p-5 text-center bg-white rounded-3 border shadow-sm",
                    )
                )
                weeks_view = empty_scheme
            else:
                weeks_view = Row(*week_cards, g=3)

            content_view = Div(
                class_pills,
                subject_pills,
                term_tabs,
                weeks_view,
            )

        return AppShell(
            Container(
                header,
                search_form,
                content_view,
                cls="py-2",
            ),
            user=user,
            active="curriculum",
            crumbs=[("Curriculum", None)],
        )
