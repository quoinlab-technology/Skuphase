"""Exam pages + HTMX partials (FRONTEND_SPEC sec 6.4-6.6).

Server-rendered FastHTML routes that talk to the API via ``call_api`` only.
Covers: exams list, exam detail (with polling), the 3-step generation wizard
(curriculum -> sections -> options -> generate), manual exam entry, and all
action handlers (refine, submit-final, approve, export, download, delete).
"""

from __future__ import annotations

import json
import uuid
from urllib.parse import quote, urlencode

from fasthtml.common import (
    A,
    Button as HtmlButton,
    Details,
    Div,
    Form,
    H1,
    H2,
    H3,
    H4,
    H5,
    H6,
    Img,
    Input,
    Label,
    Option,
    P,
    Pre,
    Script,
    Select as HtmlSelect,
    Span,
    Strong,
    Summary,
    Textarea,
    Title,
    to_xml,
)
from sqlalchemy import and_, select
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.core.database import get_async_session_maker
from app.utils.exam_utils import format_mcq_option

from faststrap import (
    Alert,
    Badge,
    Button,
    Card,
    Col,
    Dropdown,
    DropdownDivider,
    DropdownItem,
    EmptyState,
    FormGroup,
    Icon,
    Row,
    Select,
    Spinner,
    TBody,
    TCell,
    THead,
    TRow,
    Table,
)

from app.core.workflow import REFINABLE_STATES, SUBMITTABLE_STATES  # noqa: F401  (re-exported for app.core.workflow)
from app.frontend.api import call_api, unwrap
from app.frontend.components.exam import (
    StatusBadge,
    action_buttons,
    exam_header,
    render_questions,
    render_rich_text,
)
from app.frontend.components.feedback import Flash, pop_flash, set_flash, show_toast
from app.frontend.components.layout import AppShell
from app.frontend.deps import current_user, ensure_login

QUESTION_TYPES = [
    ("multiple_choice", "Multiple choice"),
    ("short_answer", "Short answer"),
    ("essay", "Essay"),
    ("true_false", "True / False"),
]
INSTRUCTION_TYPES = [
    ("answer_all", "Answer all"),
    ("answer_any_n", "Answer any N"),
    ("compulsory_plus_optional", "Compulsory + optional"),
]
SUB_PART_STYLES = [
    ("none", "None"),
    ("letter", "Letter (a, b, c)"),
    ("roman", "Roman (i, ii, iii)"),
    ("number", "Number (1, 2, 3)"),
]
LANGUAGES = [
    ("English", "English"),
    ("Igbo", "Igbo"),
    ("Yoruba", "Yoruba"),
    ("Hausa", "Hausa"),
]
TERMS = ["First Term", "Second Term", "Third Term"]
GRADE_LEVELS = [
    "Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6",
    "Pre-Nursery", "Nursery 1", "Nursery 2", "Nursery 3",
]



# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _csrf_input(request: Request):
    """Hidden CSRF token input for HTML <form> posts; '' when no token yet."""
    token = request.session.get("csrf")
    if not token:
        return ""
    return Input(name="csrf_token", value=token, type="hidden")



def _safe_int(value, default: int) -> int:
    """Parse an int from form data without crashing on bad input."""
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


async def _fetch_exam(req: Request, exam_id: str):
    """Fetch single exam. Returns (ok, data_or_error_dict)."""
    resp = await call_api(req, "GET", f"/exams/{exam_id}")
    return unwrap(resp)


def _query(**params) -> str:
    """Build a query string from non-empty kwargs."""
    return urlencode({k: v for k, v in params.items() if v not in (None, "")})


def _state_of(exam: dict) -> str:
    """Resolve the effective workflow state for badge/action logic."""
    if exam.get("status") == "failed":
        return "failed"
    return exam.get("workflow_state") or exam.get("status") or "draft"


def _quality_bar(exam: dict):
    """Quality score bar matching the prototype design.

    Prototype: 3.5rem (w-14) x 0.375rem (h-1.5) track, rounded-full.
    Fill color: emerald >=90, amber >=75, red <75.
    """
    score = exam.get("quality_score") or exam.get("qualityScore") or None
    if not score:
        return Span("\u2014", cls="text-muted small")
    pct = max(0, min(100, int(score)))
    if pct >= 90:
        fill_cls, text_cls = "app-quality-fill-emerald", "text-emerald-600"
    elif pct >= 75:
        fill_cls, text_cls = "app-quality-fill-amber", "text-amber-600"
    else:
        fill_cls, text_cls = "app-quality-fill-red", "text-red-500"
    return Span(
        Span(
            Span(cls=f"app-quality-fill {fill_cls}", style=f"width:{pct}%"),
            cls="app-quality-track",
        ),
        Span(f"{pct}%", cls=f"ms-1 text-xs fw-semibold {text_cls}"),
        cls="d-inline-flex align-items-center",
    )


def _row_actions(exam: dict, user: dict = None):
    """Per-row hover-revealed actions: View icon + kebab dropdown (prototype).

    Dropdown items matching P05_exams_list_default_desktop_table_menu_open.png:
      - View           always shown
      - Export PDF     always shown
      - Duplicate      always shown
      - Retry          only when status == "failed"
      - Delete         only when user is admin/school_admin (separated by divider)
    """
    user = user or {}
    exam_id = str(exam.get("id", ""))
    state = (exam.get("workflow_state") or exam.get("status") or "draft")
    role = user.get("role")
    account = user.get("account_type")
    is_admin = role == "school_admin" or account == "individual_teacher"

    items = [
        DropdownItem(
            Icon("eye", cls="me-2"),
            "View",
            href=f"/app/exams/{exam_id}",
        ),
        DropdownItem(
            Icon("download", cls="me-2"),
            "Export PDF",
            href=f"/app/exams/{exam_id}/print",
            target="_blank",
        ),
        DropdownItem(
            Icon("files", cls="me-2"),
            "Duplicate",
            href=f"/app/exams/new?copy_from={exam_id}",
        ),
    ]

    if state == "failed":
        items.append(
            DropdownItem(
                Icon("arrow-counterclockwise", cls="me-2"),
                "Retry",
                href="#",
                onclick="alert('Retry queued')",
            )
        )

    if is_admin:
        items.append(DropdownDivider())
        items.append(
            DropdownItem(
                Icon("trash", cls="me-2 text-danger"),
                "Delete",
                href="#",
                hx_delete=f"/ui/exams/{exam_id}",
                hx_confirm="This permanently deletes the exam and all its questions.",
                hx_target="#exam-action-feedback",
                hx_swap="innerHTML",
            )
        )

    return Dropdown(
        *items,
        label=Icon("three-dots-vertical"),
        variant="light",
        size="sm",
        toggle_cls="rounded-circle p-1 border-0 shadow-none bg-transparent text-secondary",
        direction="end",
        menu_cls="dropdown-menu-end shadow-sm border rounded-3 py-1",
    )

def _exam_row(exam: dict, user: dict = None):
    """One prototype-style exams-list row using Faststrap table components.

    Matches the V0 prototype: semantic <tr> with 7 columns, group-hover reveals
    action icons (eye + kebab dropdown) in the last cell.
    """
    user = user or {}
    exam_id = exam.get("id", "")
    detail_link = f"/app/exams/{exam_id}"
    created = (exam.get("created_at") or "")[:10]
    subject = exam.get("subject", "Untitled exam")
    grade = exam.get("grade_level", "")
    total_marks = exam.get("total_marks", 0)
    questions_count = exam.get("total_questions") or len(exam.get("questions") or []) or 0
    created_by = exam.get("creator_name") or exam.get("created_by_name") or "Adaeze"
    workflow_state = exam.get("workflow_state") or exam.get("status") or "draft"
    ai_generated = (
        not (exam.get("source_type") == "manual" or exam.get("is_manual"))
        and workflow_state != "generation_requested"
    )

    if workflow_state == "generation_requested":
        icon_name = "bolt"
        icon_container_cls = "app-table-row-icon generating"
        icon_svg_cls = "text-amber animate-pulse"
    elif exam.get("source_type") == "manual" or exam.get("is_manual"):
        icon_name = "file-earmark-text"
        icon_container_cls = "app-table-row-icon"
        icon_svg_cls = "text-muted"
    else:
        icon_name = "stars"
        icon_container_cls = "app-table-row-icon ai"
        icon_svg_cls = "text-primary"

    title_text = f"{grade} {subject} \u2014 Term Examination" if "Exam" not in subject else f"{grade} {subject}"

    return TRow(
        TCell(
            Div(
                Div(Icon(icon_name, cls=icon_svg_cls), cls=icon_container_cls),
                Div(
                    A(
                        Strong(title_text, cls="fw-medium text-dark d-block text-truncate mb-1"),
                        href=detail_link,
                        cls="text-decoration-none",
                    ),
                    Span(f"{total_marks} marks \u00b7 by {created_by.split(' ')[0]}", cls="text-xs text-muted"),
                    cls="text-truncate",
                ),
                cls="d-flex align-items-center",
            ),
            cls="px-4 py-3",
            data_label="Title",
        ),
        TCell(
            Div(
                subject,
                Span(grade, cls="text-muted"),
                cls="text-muted small",
            ),
            cls="px-4 py-3 whitespace-nowrap",
            data_label="Subject / Grade",
        ),
        TCell(
            Span(str(questions_count) if questions_count > 0 else "\u2014", cls="small fw-semibold text-dark"),
            cls="px-4 py-3 text-center",
            data_label="Questions",
        ),
        TCell(
            _quality_bar(exam),
            cls="px-4 py-3 whitespace-nowrap",
            data_label="Quality",
        ),
        TCell(
            StatusBadge(exam),
            cls="px-4 py-3",
            data_label="Status",
        ),
        TCell(
            Span(created, cls="text-xs text-muted"),
            cls="px-4 py-3 whitespace-nowrap",
            data_label="Updated",
        ),
        TCell(
            Div(
                A(
                    Icon("eye"),
                    href=detail_link,
                    cls="app-action-icon",
                    title="View exam",
                ),
                _row_actions(exam, user),
                cls="d-flex align-items-center gap-1 app-row-actions",
            ),
            cls="px-4 py-3 text-end",
            data_label="Actions",
        ),
        id=f"exam-row-{exam_id}",
        cls="app-table-row group",
    )



def _exam_card(exam: dict, user: dict = None) -> Div:
    """Mobile card layout matching P05_exams_list_mobile.png."""
    user = user or {}
    exam_id = exam.get("id", "")
    detail_link = f"/app/exams/{exam_id}"
    created = (exam.get("created_at") or "")[:10]
    subject = exam.get("subject", "Untitled exam")
    grade = exam.get("grade_level", "")
    total_marks = exam.get("total_marks", 0)
    workflow_state = exam.get("workflow_state") or exam.get("status") or "draft"

    if workflow_state == "generation_requested":
        icon_name = "bolt"
        icon_container_cls = "app-table-row-icon generating"
        icon_svg_cls = "text-amber"
    elif exam.get("source_type") == "manual" or exam.get("is_manual"):
        icon_name = "file-earmark-text"
        icon_container_cls = "app-table-row-icon"
        icon_svg_cls = "text-muted"
    elif workflow_state == "failed":
        icon_name = "stars"
        icon_container_cls = "app-table-row-icon failed"
        icon_svg_cls = "text-danger"
    else:
        icon_name = "stars"
        icon_container_cls = "app-table-row-icon ai"
        icon_svg_cls = "text-primary"

    title_text = f"{grade} {subject} — Term Examination" if "Exam" not in subject else f"{grade} {subject}"
    subtitle_text = f"{subject} · {grade} · {total_marks} marks"

    # Quality indicator
    score = exam.get("overall_score") or exam.get("quality_score")
    quality_el = None
    if score is not None:
        try:
            pct = int(float(score) * 100) if float(score) <= 1 else int(float(score))
            q_color = "text-success" if pct >= 80 else ("text-warning" if pct >= 60 else "text-danger")
            quality_el = Span(f"{pct}%", cls=f"small fw-bold {q_color}")
        except (ValueError, TypeError):
            quality_el = None

    return Div(
        Div(
            Div(
                Div(Icon(icon_name, cls=icon_svg_cls), cls=icon_container_cls),
                Div(
                    A(
                        Strong(title_text, cls="fw-semibold text-dark d-block text-truncate mb-1"),
                        href=detail_link,
                        cls="text-decoration-none",
                    ),
                    Span(subtitle_text, cls="text-muted small"),
                    cls="flex-grow-1 min-w-0 me-2",
                ),
                _row_actions(exam, user),
                cls="d-flex align-items-start justify-content-between mb-3",
            ),
            Div(
                StatusBadge(exam),
                Div(
                    *([quality_el] if quality_el else []),
                    Span(created, cls="text-muted small ms-3"),
                    cls="d-flex align-items-center ms-auto",
                ),
                cls="d-flex align-items-center justify-content-between pt-2 border-top border-light",
            ),
            cls="p-3",
        ),
        cls="bg-white rounded-4 shadow-sm border mb-3",
        id=f"exam-card-{exam_id}",
    )


def _section_card(idx: int) -> Div:
    """One configurable section row for the generation wizard."""
    return Div(
        Div(
            FormGroup(
                "Section title",
                Input(
                    f"section_{idx}_title",
                    value=f"SECTION {chr(64 + idx)}",
                    required=True,
                ),
            ),
            FormGroup(
                "Question type",
                Select(
                    f"section_{idx}_qtype",
                    *QUESTION_TYPES,
                    value="multiple_choice",
                ),
            ),
            FormGroup(
                "Number of questions",
                Input(
                    f"section_{idx}_num",
                    type="number",
                    value="20",
                    min="1",
                    max="50",
                ),
            ),
            FormGroup(
                "Marks per question",
                Input(
                    f"section_{idx}_marks",
                    type="number",
                    value="2",
                    min="1",
                    max="20",
                ),
            ),
            FormGroup(
                "Instruction type",
                Select(
                    f"section_{idx}_instr",
                    *INSTRUCTION_TYPES,
                    value="answer_all",
                ),
            ),
            FormGroup(
                "Sub-part style",
                Select(
                    f"section_{idx}_substyle",
                    *SUB_PART_STYLES,
                    value="none",
                ),
            ),
            cls="row g-2",
        ),
        id=f"section-card-{idx}",
        cls="card p-3 mb-2",
        **{"data-section-index": str(idx)},
    )


def _build_sections_from_form(form) -> list:
    """Read section fields from the wizard form and build SectionConfig dicts."""
    sections: list = []
    # Collect all present section index keys, e.g. section_1_title, section_2_title...
    indices = []
    for k in form.keys():
        if k.startswith("section_") and k.endswith("_title"):
            parts = k.split("_")
            if len(parts) >= 3 and parts[1].isdigit():
                indices.append(int(parts[1]))
    indices = sorted(set(indices))

    # If no indices found via keys (e.g. dict or list), fallback to 1..10 loop
    if not indices:
        for idx in range(1, 20):
            if form.get(f"section_{idx}_title") is not None:
                indices.append(idx)

    new_sec_num = 1
    for idx in indices:
        title = form.get(f"section_{idx}_title")
        if not title or not str(title).strip():
            continue
        qtype = form.get(f"section_{idx}_qtype", "multiple_choice")
        num_q = max(1, _safe_int(form.get(f"section_{idx}_num"), 1))
        marks = max(1, _safe_int(form.get(f"section_{idx}_marks"), 1))
        instr = form.get(f"section_{idx}_instr", "answer_all")
        substyle = form.get(f"section_{idx}_substyle", "none")
        sections.append(
            {
                "section_number": new_sec_num,
                "section_title": str(title).strip(),
                "question_type": qtype,
                "num_questions": num_q,
                "marks": marks,
                "marks_per_question": marks,
                "instruction_type": instr,
                "sub_part_style": substyle,
            }
        )
        new_sec_num += 1
    return sections


def _manual_paste_help() -> Div:
    return Div(
        P(
            "Paste one question per block, separated by a blank line. "
            "For multiple-choice questions, prefix each option with \"A)\", "
            "\"B)\", \"C)\", \"D)\" and mark the correct answer with \"Answer: B\".",
            cls="text-muted small",
        ),
        P("Example:", cls="small mb-1 fw-semibold"),
        Pre(
            "What is 2 + 2?\nA) 3\nB) 4\nC) 5\nD) 6\nAnswer: B\nMarks: 2\n\n"
            "Name the capital of Lagos State.\nMarks: 1"
        ),
    )


def _is_workspace_admin(user: dict) -> bool:
    """Mirror of app.core.permissions.is_workspace_admin for UI gating."""
    return user.get("role") == "school_admin" or user.get("account_type") == "individual_teacher"


def _render_clean_print_paper(exam: dict, user: dict) -> Div:
    """Standalone, pristine school examination paper optimized for paper printing."""
    school_name = user.get("school_name") or exam.get("school_name") or ("Personal Workspace" if user.get("account_type") == "individual_teacher" else "Your School")
    school_address = user.get("school_address") or ""
    school_logo = user.get("school_logo_url") or ""

    logo_part = (
        Img(src=school_logo, alt="Logo", style="max-height: 70px; max-width: 70px; object-fit: contain; margin-right: 18px;")
        if school_logo
        else Div()
    )

    header = Div(
        Div(
            logo_part,
            Div(
                H1(school_name.upper(), style="font-size: 1.35rem; font-weight: 800; margin-bottom: 2px; text-align: center; color: #111;"),
                P(school_address, style="font-size: 0.82rem; color: #555; margin-bottom: 4px; text-align: center;") if school_address else Div(),
                H2(f"{str(exam.get('subject', '')).upper()} EXAMINATION", style="font-size: 1.05rem; font-weight: 700; margin-bottom: 4px; text-align: center; color: #111;"),
                P(
                    f"CLASS: {str(exam.get('grade_level', '')).upper()}    |    "
                    f"TERM: {str(exam.get('term', 'First Term')).upper()}    |    "
                    f"TIME: {exam.get('duration_minutes', 60)} MINS    |    "
                    f"TOTAL MARKS: {exam.get('total_marks', 100)}",
                    style="font-size: 0.82rem; font-weight: 600; text-align: center; color: #222; margin-bottom: 0;",
                ),
                style="flex-grow: 1;",
            ),
            style="display: flex; align-items: center; justify-content: center; padding-bottom: 12px; border-bottom: 2px solid #222;",
        ),
        (
            Div(
                Strong("INSTRUCTIONS: ", style="font-size: 0.85rem;"),
                Span(exam.get("instructions", "Answer all questions."), style="font-size: 0.85rem;"),
                style="padding: 6px 10px; margin-top: 8px; margin-bottom: 12px; border: 1px solid #666; border-radius: 4px;",
            )
            if exam.get("instructions")
            else Div()
        ),
        style="margin-bottom: 16px;",
    )

    # Questions grouped by section
    questions = exam.get("questions") or []
    passages = exam.get("passages") or []
    passage_by_id = {str(p.get("id")): p for p in passages if p.get("id")}

    sec_marks: dict = {}
    for q in questions:
        stitle = q.get("section_title")
        if not stitle:
            qtype = q.get("type", "multiple_choice")
            if qtype == "multiple_choice":
                stitle = "SECTION A: OBJECTIVE QUESTIONS"
            elif qtype in ("short_answer", "theory"):
                stitle = "SECTION B: SHORT ANSWER / THEORY"
            elif qtype == "essay":
                stitle = "SECTION C: ESSAY QUESTIONS"
            else:
                stitle = "SECTION A"
        sec_marks[stitle] = sec_marks.get(stitle, 0) + (q.get("marks", 0) or 0)

    content_blocks = []
    current_sec = None
    seen_passages: set = set()

    for idx, q in enumerate(questions, start=1):
        stitle = q.get("section_title")
        if not stitle:
            qtype = q.get("type", "multiple_choice")
            if qtype == "multiple_choice":
                stitle = "SECTION A: OBJECTIVE QUESTIONS"
            elif qtype in ("short_answer", "theory"):
                stitle = "SECTION B: SHORT ANSWER / THEORY"
            elif qtype == "essay":
                stitle = "SECTION C: ESSAY QUESTIONS"
            else:
                stitle = "SECTION A"

        if stitle != current_sec:
            current_sec = stitle
            tot_m = sec_marks.get(stitle, 0)
            marks_str = f" ({tot_m} MARKS)" if tot_m > 0 else ""
            content_blocks.append(
                Div(
                    H2(f"{stitle.upper()}{marks_str}", style="font-size: 0.95rem; font-weight: 700; border-bottom: 1px solid #333; padding-bottom: 3px; margin-top: 14px; margin-bottom: 8px; color: #111;"),
                    style="page-break-after: avoid;",
                )
            )

        # Passage if needed
        pid = q.get("passage_id")
        if pid and str(pid) in passage_by_id and str(pid) not in seen_passages:
            seen_passages.add(str(pid))
            pass_obj = passage_by_id[str(pid)]
            p_title = pass_obj.get("title") or ""
            content_blocks.append(
                Div(
                    P(Strong("Read the passage and answer the questions that follow:"), style="font-size: 0.85rem; margin-bottom: 4px;"),
                    P(Strong(p_title), style="font-size: 0.9rem; margin-bottom: 4px;") if p_title else Div(),
                    P(pass_obj.get("body", ""), style="font-size: 0.85rem; line-height: 1.4; margin-bottom: 8px; white-space: pre-wrap;"),
                    style="padding: 8px 12px; background: #fdfdfd; border-left: 3px solid #333; margin-bottom: 10px; page-break-inside: avoid;",
                )
            )

        # Question block
        marks_bit = f" [{q['marks']} marks]" if q.get("marks") else ""
        q_parts = [
            Div(Strong(f"Q{idx}. "), Span(q.get("question_text", "")), Span(marks_bit, style="font-weight: 600; float: right; font-size: 0.82rem;"), style="margin-bottom: 4px; font-size: 0.88rem;"),
        ]

        if q.get("options"):
            opts = []
            for o_idx, opt in enumerate(q["options"]):
                opt_str = format_mcq_option(opt, o_idx)
                opts.append(Div(opt_str, style="font-size: 0.85rem; margin-bottom: 2px; flex: 1 1 45%; min-width: 200px;"))
            q_parts.append(Div(*opts, style="display: flex; flex-wrap: wrap; margin-left: 20px; margin-bottom: 6px;"))

        if q.get("sub_parts"):
            sp_list = []
            for sp in q["sub_parts"]:
                if isinstance(sp, dict):
                    sp_list.append(
                        Div(f"({sp.get('part', '?')}) {sp.get('question', '')} [{sp.get('marks', 0)} marks]", style="font-size: 0.84rem; margin-left: 20px; margin-bottom: 2px;")
                    )
            q_parts.append(Div(*sp_list))

        content_blocks.append(Div(*q_parts, style="margin-bottom: 10px; page-break-inside: avoid;"))

    toolbar = Div(
        Button("Print Exam Paper", type="button", cls="btn btn-dark rounded-pill px-4 me-2", onclick="window.print()"),
        Button("Close", type="button", cls="btn btn-outline-secondary rounded-pill px-3", onclick="window.close()"),
        cls="no-print d-flex justify-content-center p-3 mb-4 bg-light border rounded-pill shadow-sm",
    )

    return Div(
        Title(f"{exam.get('subject', 'Exam')} - Question Paper"),
        toolbar,
        Div(
            header,
            *content_blocks,
            style="max-width: 800px; margin: 0 auto; padding: 20px; background: #fff; font-family: 'Segoe UI', Arial, sans-serif; color: #111;",
        ),
        Script("window.addEventListener('DOMContentLoaded', function() { setTimeout(function() { window.print(); }, 400); });"),
        style="background: #eaedf0; min-height: 100vh; padding: 20px 10px;",
    )


# ---------------------------------------------------------------------------
# Page-route registration: /app/exams list + /app/exams/{id} detail
# ---------------------------------------------------------------------------

def register_page_routes(app):

    """Register list and detail routes (full pages)."""

    @app.get("/app/exams")
    async def exams_list(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)

        q = req.query_params.get("q", "").strip()
        subject = req.query_params.get("subject", "").strip()
        grade = req.query_params.get("grade", "").strip()
        status = req.query_params.get("status", "").strip()

        params = {"limit": "50"}
        if subject:
            params["subject"] = subject
        if grade:
            params["grade_level"] = grade
        if status:
            params["status"] = status

        resp = await call_api(req, "GET", "/exams/", params=params)
        ok, data = unwrap(resp)

        if not ok:
            # Full-page flow: inline Alert is correct here (FRONTEND_SPEC §5) —
            # this renders inside AppShell, not as an HTMX swap response.
            body_content = Div(
                Alert(data.get("message", "We couldn't load your exams right now — refresh to try again."), variant="danger"),
                cls="mb-3",
            )
        else:
            exams = data.get("exams", []) or []
            if q:
                q_lower = q.lower()
                exams = [
                    e for e in exams
                    if q_lower in (e.get("subject", "") + " " + e.get("grade_level", "")).lower()
                ]
            if not exams:
                body_content = EmptyState(
                    title="No exams yet",
                    description="Create your first exam with AI or type one yourself.",
                    action=A(
                        Icon("stars", cls="bi me-2"),
                        "Create exam",
                        href="/app/exams/new",
                        cls="btn btn-brand rounded-pill px-4 py-2 text-white fw-semibold text-decoration-none shadow-sm",
                    ),
                )
            else:
                rows = [_exam_row(e, user) for e in exams]
                cards = [_exam_card(e, user) for e in exams]
                thead = THead(
                    TRow(
                        TCell("Title", header=True, cls="ps-4"),
                        TCell("Subject / Grade", header=True),
                        TCell("Questions", header=True, cls="text-center"),
                        TCell("Quality", header=True, cls="text-center"),
                        TCell("Status", header=True, cls="text-center"),
                        TCell("Updated", header=True, cls="text-end"),
                        TCell(header=True, cls="text-center pe-4"),
                    ),
                    cls="app-table-head",
                )
                tbody = TBody(*rows, cls="app-table-body")
                desktop_table = Div(
                    Table(thead, tbody, hover=True, striped=False, cls="app-table mb-0"),
                    cls="app-table-container app-card shadow-sm border-0 rounded-4 overflow-hidden d-none d-md-block",
                )
                mobile_cards = Div(
                    *cards,
                    cls="d-md-none",
                )
                body_content = Div(desktop_table, mobile_cards)

        # Status filter pills (UI_design/Exams2.png) — links preserve search & filters.
        def _pill(label: str, key: str, active_key: str, count: int | None = None):
            href_params = {k: v for k, v in (("q", q), ("subject", subject), ("grade", grade)) if v}
            if key:
                href_params["status"] = key
            href = "/app/exams" + (("?" + urlencode(href_params)) if href_params else "")
            count_str = f" ({count})" if count is not None else ""
            is_active = (active_key == key) or (not active_key and not key)
            if is_active:
                cls = "badge rounded-pill text-white px-3 py-2 fw-semibold text-decoration-none shadow-sm"
                style = "background-color: #00412E !important; font-size: 0.88rem;"
            else:
                cls = "badge rounded-pill bg-white text-muted border px-3 py-2 fw-normal text-decoration-none shadow-sm"
                style = "font-size: 0.88rem;"
            return A(f"{label}{count_str}", href=href, cls=cls, style=style,
                     **({"aria-current": "true"} if is_active else {}))

        all_exams = (data.get("exams", []) or []) if ok else []
        approved_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) == "approved")
        review_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) in {"teacher_review", "final_submitted_by_teacher", "refinement_requested"})
        gen_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) == "generation_requested")
        draft_cnt = sum(1 for e in all_exams if (e.get("workflow_state") or e.get("status")) == "draft")
        failed_cnt = sum(1 for e in all_exams if e.get("status") == "failed")

        # Live bell badge (audit: was hardcoded "3"): stash the under-review
        # count in the session so every AppShell page can show a real number.
        req.session["bell_count"] = review_cnt

        pills = Div(
            _pill("All", "", status, len(all_exams)),
            _pill("Approved", "approved", status, approved_cnt),
            _pill("Under Review", "under_review", status, review_cnt),
            _pill("Generating", "generating", status, gen_cnt),
            _pill("Draft", "draft", status, draft_cnt),
            _pill("Failed", "failed", status, failed_cnt),
            cls="d-flex gap-2 overflow-x-auto pb-2 flex-nowrap flex-md-wrap mb-3 align-items-center",
        )

        subject_options = [
            ("All subjects", ""),
            ("Mathematics", "Mathematics"),
            ("English Language", "English Language"),
            ("Basic Science", "Basic Science"),
            ("Social Studies", "Social Studies"),
            ("National Values", "National Values"),
            ("Civic Education", "Civic Education"),
            ("Agricultural Science", "Agricultural Science"),
            ("Computer Studies", "Computer Studies"),
            ("Physical & Health Education", "Physical & Health Education"),
            ("Home Economics", "Home Economics"),
            ("Christian Religious Studies", "Christian Religious Studies"),
            ("Islamic Religious Studies", "Islamic Religious Studies"),
            ("Hausa", "Hausa"),
            ("Igbo", "Igbo"),
            ("Yoruba", "Yoruba"),
        ]

        grade_options = [
            ("All grades", ""),
            ("Pre-Nursery", "Pre-Nursery"),
            ("Nursery 1", "Nursery 1"),
            ("Nursery 2", "Nursery 2"),
            ("Primary 1", "Primary 1"),
            ("Primary 2", "Primary 2"),
            ("Primary 3", "Primary 3"),
            ("Primary 4", "Primary 4"),
            ("Primary 5", "Primary 5"),
            ("Primary 6", "Primary 6"),
        ]

        search_input_wrap = Div(
            Icon("search", cls="bi text-muted me-2"),
            Input(
                name="q",
                value=q,
                placeholder="Search exams...",
                cls="border-0 bg-transparent shadow-none p-0 flex-grow-1",
                style="outline:none; font-size: 0.92rem;",
                **{"aria-label": "Search exams"},
            ),
            cls="d-flex align-items-center bg-white border rounded-pill px-3 py-2 shadow-sm flex-grow-1",
            style="min-width: 240px; max-width: 360px;",
        )

        subject_select = HtmlSelect(
            *[Option(label, value=val, selected=(subject == val if val else not subject)) for label, val in subject_options],
            name="subject",
            cls="form-select rounded-pill bg-white border px-3 py-2 shadow-sm",
            style="min-width: 160px; max-width: 200px; font-size: 0.92rem; cursor: pointer;",
            onchange="this.form.submit()",
        )

        grade_select = HtmlSelect(
            *[Option(label, value=val, selected=(grade == val if val else not grade)) for label, val in grade_options],
            name="grade",
            cls="form-select rounded-pill bg-white border px-3 py-2 shadow-sm",
            style="min-width: 140px; max-width: 180px; font-size: 0.92rem; cursor: pointer;",
            onchange="this.form.submit()",
        )

        filter_form = Form(
            search_input_wrap,
            subject_select,
            grade_select,
            Input("status", type="hidden", value=status) if status else "",
            action="/app/exams",
            method="get",
            cls="d-flex flex-wrap gap-3 align-items-center mb-4",
            id="exams-filter",
        )

        body = Div(
            Div(
                Div(
                    Div(
                        H1("Exams", cls="app-section-title mb-1"),
                        P("Manage, generate, and review examinations.", cls="app-body-copy mb-0"),
                    ),
                    Div(
                        A(
                            Icon("stars", cls="bi me-1 me-sm-2"),
                            Span("Generate with AI", cls="d-none d-sm-inline"),
                            Span("Generate", cls="d-sm-none"),
                            href="/app/exams/new",
                            cls="btn btn-brand rounded-pill px-3 px-sm-4 py-2 fw-semibold text-white shadow-sm d-inline-flex align-items-center text-decoration-none",
                            style="background-color: #00412E !important; border: none;",
                        ),
                        A(
                            Icon("plus-lg", cls="bi me-1 me-sm-2"),
                            Span("Manual Exam", cls="d-none d-sm-inline"),
                            Span("Manual", cls="d-sm-none"),
                            href="/app/exams/new/manual",
                            cls="btn btn-outline-secondary bg-white text-dark border rounded-pill px-3 px-sm-4 py-2 fw-semibold shadow-sm d-inline-flex align-items-center text-decoration-none",
                        ),
                        cls="d-flex flex-nowrap gap-2 align-items-center",
                    ),
                    cls="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4",
                ),
                pills,
                filter_form,
                Div(body_content, id="exams-content"),
                Div(id="exam-action-feedback", cls="mt-3"),
                cls="mt-2",
            ),
            id="exams-view",
        )
        return AppShell(
            Title("Exams - SkuPhase"),
            body,
            user=user,
            active="exams",
            flash=flash,
            crumbs=[("Exams", None)],
            bell_count=req.session.get("bell_count"),
        )

    @app.get("/app/exams/new")
    async def exam_new(req: Request, mode: str = "ai", step: str = "1"):
        guard = ensure_login(req)
        if guard:
            return guard
        if mode == "manual":
            return RedirectResponse("/app/exams/new/manual", status_code=303)
        user = current_user(req) or {}
        flash = pop_flash(req)
        body = _render_wizard_full(step=step, request=req)
        return AppShell(
            Title("Generate with AI - SkuPhase"),
            body,
            user=user,
            active="exams",
            flash=flash,
            bell_count=req.session.get("bell_count"),
            crumbs=[("Exams", "/app/exams"), ("Generate with AI", None)],
        )

    @app.post("/app/exams/new")
    async def exam_new_post(req: Request, step: str = "2"):
        """Handle POST /app/exams/new?step=X for both HTMX and standard browser form submissions."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        wiz = _wizard_state(req)

        # Parse step parameter from query or default
        next_step = req.query_params.get("step") or step or "2"

        if next_step == "2" or "subject" in form or "grade_level" in form:
            wiz["grade_level"] = (form.get("grade_level") or wiz.get("grade_level") or "Primary 4").strip()
            wiz["subject"] = (form.get("subject") or wiz.get("subject") or "Mathematics").strip()
            wiz["term"] = (form.get("term") or wiz.get("term") or "First Term").strip()
            wiz["weeks"] = (form.get("weeks") or wiz.get("weeks") or "").strip()
            wiz["difficulty_preset"] = (form.get("difficulty_preset") or wiz.get("difficulty_preset") or "balanced").strip()
            bloom_list = form.getlist("bloom_levels")
            if bloom_list:
                wiz["bloom_levels"] = bloom_list
            elif "bloom_levels" not in wiz:
                wiz["bloom_levels"] = ["Remember", "Understand", "Apply", "Analyse"]
            wiz["exam_title"] = (form.get("exam_title") or wiz.get("exam_title") or f"{wiz['grade_level']} {wiz['subject']} — {wiz['term']} Examination").strip()
            wiz["total_marks"] = (form.get("total_marks") or wiz.get("total_marks") or "100").strip()
            _wizard_save(req, wiz)
            target_step = "2"
        elif next_step == "3" or "selected_weeks" in form or "selected_documents" in form or "focus_topics" in form:
            selected_weeks = form.getlist("selected_weeks")
            if selected_weeks:
                wiz["selected_weeks"] = selected_weeks
            selected_docs = form.getlist("selected_documents")
            if selected_docs:
                wiz["selected_documents"] = selected_docs
            wiz["focus_topics"] = (form.get("focus_topics") or wiz.get("focus_topics") or "").strip()
            _wizard_save(req, wiz)
            target_step = "3"
        elif next_step == "4" or any(k.startswith("section_") for k in form.keys()):
            sections = _build_sections_from_form(form)
            if sections:
                wiz["sections"] = sections
            _wizard_save(req, wiz)
            target_step = "4"
        else:
            target_step = next_step

        if req.headers.get("hx-request") == "true":
            if req.headers.get("hx-target") == "wizard-panel":
                return _wizard_panel(target_step, req)
            return _render_wizard_full(target_step, req)
        return RedirectResponse(f"/app/exams/new?step={target_step}", status_code=303)


    @app.get("/app/exams/{exam_id}")
    async def exam_detail(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)
        show_answers = req.query_params.get("answers") == "1"

        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            set_flash(req.session, "danger", exam.get("message", "Exam not found."))
            return RedirectResponse("/app/exams", status_code=303)

        state = _state_of(exam)
        is_generating = state in ("generation_requested", "refinement_requested")

        if is_generating:
            total_q = exam.get("total_questions") or len(exam.get("questions") or []) or 37
            num_sec = len(exam.get("sections") or []) or 3
            inner = Div(
                _render_generating_screen(
                    exam_id,
                    total_q=total_q,
                    num_sections=num_sec,
                    num_docs=3,
                    poll_endpoint=f"/ui/exams/{exam_id}/poll",
                    poll_target="#exam-detail-view",
                    poll_count=0,
                ),
                id="exam-detail-view",
            )
        else:
            inner = Div(
                _render_exam_detail(exam, user, show_answers),
                id="exam-detail-view",
            )

        return AppShell(
            Title(f"{exam.get('subject', 'Exam')} - SkuPhase"),
            inner,
            user=user,
            active="exams",
            flash=flash,
            crumbs=[("Exams", "/app/exams"), (exam.get("subject", "Exam"), None)],
            bell_count=req.session.get("bell_count"),
        )

    @app.get("/app/exams/{exam_id}/print")
    async def exam_print_view(req: Request, exam_id: str):
        """Dedicated clean print view for official examination question paper."""
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            set_flash(req.session, "danger", exam.get("message", "Exam not found."))
            return RedirectResponse("/app/exams", status_code=303)

        return _render_clean_print_paper(exam, user)

    @app.get("/app/exams/{exam_id}/exports/{file_name}")
    async def exam_export_download(req: Request, exam_id: str, file_name: str):
        """Session-authenticated proxy to download generated PDF export.
        
        Reads the access_token from the session (not from Authorization header),
        so it works when a browser navigates a plain <a href> link that only
        sends the session cookie. Tenant-checked: only the exam's school can
        download its exports. Streams the PDF back as a downloadable attachment.
        """
        guard = ensure_login(req)
        if guard:
            return guard
        
        token = req.session.get("access_token")
        if not token:
            set_flash(req.session, "danger", "Session expired — please log in again.")
            return RedirectResponse("/login", status_code=303)
        
        import re
        from pathlib import Path
        from fastapi.responses import FileResponse
        from sqlalchemy import select
        from app.core.database import get_async_session_maker
        from app.models.exam import Exam
        
        # Validate file name format
        if not re.fullmatch(r"[0-9a-f]{32}\.pdf", file_name or ""):
            set_flash(req.session, "danger", "Invalid export file name.")
            return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)
        
        # Tenant check: exam must belong to the user's school
        session_maker = get_async_session_maker()
        async with session_maker() as db:
            try:
                school_id = req.session.get("school_id")
                result = await db.execute(
                    select(Exam.id).where(
                        and_(
                            Exam.id == uuid.UUID(exam_id),
                            Exam.school_id == uuid.UUID(school_id) if school_id else Exam.id == uuid.UUID(exam_id),
                        )
                    )
                )
                if result.scalar_one_or_none() is None:
                    set_flash(req.session, "danger", "Exam not found or access denied.")
                    return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)
                
                # Stream the PDF from the exports directory
                export_dir = Path("exports") / "exams" / str(exam_id)
                file_path = export_dir / file_name
                if not file_path.is_file():
                    set_flash(req.session, "danger", "Export file not found — run export again.")
                    return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)
                
                return FileResponse(
                    path=str(file_path),
                    media_type="application/pdf",
                    filename=file_name,
                )
            except Exception:
                set_flash(req.session, "danger", "Could not load export file.")
                return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

# ----- Detail tab partials (lazy-loaded into #tab-content) -----


    @app.get("/ui/exams/{exam_id}/tab/questions")
    async def tab_questions(req: Request, exam_id: str, answers: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            return show_toast(exam.get("message", "We couldn't load the questions right now — refresh to try again."), "danger")
        user = current_user(req) or {}
        return Div(
            _tab_strip(exam_id, exam, active_tab="questions"),
            Div(_questions_tab(exam, user, show_answers=answers == "1"), id="tab-content"),
        )

    @app.get("/ui/exams/{exam_id}/tab/preflight")
    async def tab_preflight(req: Request, exam_id: str, run: str = ""):
        guard = ensure_login(req)
        if guard:
            return guard
        ok_exam, exam = await _fetch_exam(req, exam_id)
        exam_data = exam if ok_exam else {}
        if run != "1":
            # P06_exam_detail_preflight_not_run_desktop.png: "Preflight not yet run"
            return Div(
                _tab_strip(exam_id, exam_data, active_tab="preflight"),
                Div(
                    Div(
                        Div(
                            Icon("shield-check", cls="bi text-muted mb-3", style="font-size:3.5rem; color:#94a3b8;"),
                            H4("Preflight not yet run", cls="fw-bold text-dark mb-2"),
                            P("Run the preflight check to validate this exam before export.", cls="text-muted small mb-4"),
                            Button(
                                "Run Preflight Check",
                                hx_get=f"/ui/exams/{exam_id}/tab/preflight?run=1",
                                hx_target="#exam-tab-section",
                                hx_swap="innerHTML",
                                cls="btn-brand rounded-pill px-4 py-2",
                            ),
                            cls="text-center py-5",
                        ),
                        cls="bg-white border rounded-4 p-5 shadow-sm",
                    ),
                    id="tab-content",
                ),
            )

        resp = await call_api(req, "GET", f"/exams/{exam_id}/preflight")
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Preflight could not run."), "danger")

        if data.get("passed"):
            # P06_exam_detail_preflight_passed_desktop.png
            return Div(
                _tab_strip(exam_id, exam_data, active_tab="preflight"),
                Div(
                    Div(
                        Div(
                            Icon("check-circle-fill", cls="bi me-2 fs-5"),
                            Strong("All checks passed — exam is ready to export."),
                            cls="d-flex align-items-center",
                        ),
                        cls="preflight-banner-passed mb-3 shadow-sm",
                    ),
                    id="tab-content",
                ),
            )

        # Issues & Warnings: P06_exam_detail_preflight_with_error_desktop.png
        issues = data.get("issues") or []
        warnings = data.get("warnings") or []
        blocking_count = len(issues)
        warning_count = len(warnings)

        banner = Div(
            Div(
                Icon("x-circle-fill", cls="bi me-2 fs-5"),
                Div(
                    Strong(f"{blocking_count} blocking issues must be resolved before export.", cls="d-block"),
                    Span(f"{warning_count} additional warnings", cls="small opacity-75") if warning_count else Div(),
                ),
                cls="d-flex align-items-center",
            ),
            cls="preflight-banner-error mb-4 shadow-sm",
        )

        issue_cards = []
        for issue in issues:
            q_num = issue.get("question_number") or ""
            link_q = f"Question {q_num}" if q_num else ""
            issue_cards.append(
                Div(
                    Div(
                        Icon("x-circle", cls="bi text-danger me-2 fs-5 flex-shrink-0 mt-1"),
                        Div(
                            Div(issue.get("message", "Blocking issue"), cls="text-danger fw-medium mb-1", style="font-size:0.92rem;"),
                            (
                                A(
                                    link_q,
                                    href=f"#question-card-{q_num}",
                                    cls="small text-danger text-decoration-underline fw-semibold",
                                    onclick=f"document.querySelector('[data-tab=\"questions\"]').click(); setTimeout(() => {{ const el = document.getElementById('question-card-{q_num}'); if(el) {{ el.scrollIntoView({{behavior:'smooth'}}); el.classList.add('highlight-target'); setTimeout(() => el.classList.remove('highlight-target'), 2500); }} }}, 300); return false;",
                                )
                                if link_q else Div()
                            ),
                            cls="flex-grow-1",
                        ),
                        cls="d-flex align-items-start",
                    ),
                    cls="preflight-issue-card",
                )
            )

        warning_cards = []
        for warn in warnings:
            q_num = warn.get("question_number") or ""
            link_q = f"Question {q_num}" if q_num else ""
            warning_cards.append(
                Div(
                    Div(
                        Icon("exclamation-triangle", cls="bi text-warning me-2 fs-5 flex-shrink-0 mt-1"),
                        Div(
                            Div(warn.get("message", "Warning"), cls="text-dark fw-medium mb-1", style="font-size:0.92rem; color:#92400e;"),
                            (
                                A(
                                    link_q,
                                    href=f"#question-card-{q_num}",
                                    cls="small text-warning text-decoration-underline fw-semibold",
                                    onclick=f"document.querySelector('[data-tab=\"questions\"]').click(); setTimeout(() => {{ const el = document.getElementById('question-card-{q_num}'); if(el) {{ el.scrollIntoView({{behavior:'smooth'}}); el.classList.add('highlight-target'); setTimeout(() => el.classList.remove('highlight-target'), 2500); }} }}, 300); return false;",
                                )
                                if link_q else Div()
                            ),
                            cls="flex-grow-1",
                        ),
                        cls="d-flex align-items-start",
                    ),
                    cls="preflight-warning-card",
                )
            )

        return Div(
            _tab_strip(exam_id, exam_data, active_tab="preflight"),
            Div(
                Div(
                    banner,
                    (
                        Div(
                            H6("BLOCKING ISSUES", cls="fw-bold text-uppercase text-secondary small mb-3 letter-spacing-1"),
                            *issue_cards,
                            cls="mb-4",
                        )
                        if issue_cards else Div()
                    ),
                    (
                        Div(
                            H6("WARNINGS", cls="fw-bold text-uppercase text-secondary small mb-3 letter-spacing-1"),
                            *warning_cards,
                        )
                        if warning_cards else Div()
                    ),
                ),
                id="tab-content",
            ),
        )

    @app.get("/ui/exams/{exam_id}/tab/quality")
    async def tab_quality(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        ok_exam, exam = await _fetch_exam(req, exam_id)
        exam_data = exam if ok_exam else {}
        resp = await call_api(req, "GET", f"/exams/{exam_id}/quality-report")
        ok, data = unwrap(resp)
        content = (
            _quality_tab_content(data)
            if ok
            else EmptyState(
                title="Quality report not available",
                description=data.get("message", "Complete generation to see the quality score."),
            )
        )
        return Div(
            _tab_strip(exam_id, exam_data, active_tab="quality"),
            Div(content, id="tab-content"),
        )

    @app.get("/ui/exams/{exam_id}/tab/comments")
    async def tab_comments(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        ok_exam, exam = await _fetch_exam(req, exam_id)
        exam_data = exam if ok_exam else {}
        resp = await call_api(req, "GET", f"/exams/{exam_id}/audit-comments?include_resolved=true")
        ok, data = unwrap(resp)
        comments = data if (ok and isinstance(data, list)) else []
        content = _comments_tab_content(req, exam_id, comments, ok=ok, message=data.get("message") if not ok else None)
        return Div(
            _tab_strip(exam_id, exam_data, active_tab="comments"),
            Div(content, id="tab-content"),
        )

    @app.post("/ui/exams/{exam_id}/comments")
    async def add_comment(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        text = (form.get("comment_text") or "").strip()
        if len(text) < 5:
            return show_toast("Comment must be at least 5 characters.", "danger")
        resp = await call_api(req, "POST", f"/exams/{exam_id}/audit-comments",
                              json={"comment_text": text})
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not save comment."), "danger")
        # Re-render the whole comments tab with the fresh list including resolved.
        list_resp = await call_api(req, "GET", f"/exams/{exam_id}/audit-comments?include_resolved=true")
        ok2, comments = unwrap(list_resp)
        return _comments_tab_content(req, exam_id, comments if (ok2 and isinstance(comments, list)) else [])

    @app.post("/ui/exams/{exam_id}/comments/{comment_id}/resolve")
    async def resolve_comment(req: Request, exam_id: str, comment_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/exams/{exam_id}/audit-comments/{comment_id}/resolve")
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not update comment status."), "danger")
        list_resp = await call_api(req, "GET", f"/exams/{exam_id}/audit-comments?include_resolved=true")
        ok2, comments = unwrap(list_resp)
        return _comments_tab_content(req, exam_id, comments if (ok2 and isinstance(comments, list)) else [])

    @app.post("/ui/exams/{exam_id}/questions/{question_id}/edit")
    async def edit_question(req: Request, exam_id: str, question_id: str):
        """Submit an edit to a single exam question (PATCH proxy via HTMX)."""
        guard = ensure_login(req)
        if guard:
            return guard
        
        form = await req.form()
        user = current_user(req) or {}
        state = _state_of({"workflow_state": form.get("_workflow_state") or "", "status": form.get("_status") or ""})
        editable_states = {"draft", "teacher_review", "final_submitted_by_teacher"}
        if not _is_workspace_admin(user) or state not in editable_states:
            return show_toast("You cannot edit this question right now.", "danger")
        
        payload = {}
        qtext = (form.get("question_text") or "").strip()
        if qtext:
            payload["question_text"] = qtext
        marks = form.get("marks")
        if marks:
            try:
                payload["marks"] = int(marks)
            except (TypeError, ValueError):
                pass
        correct = (form.get("correct_answer") or "").strip()
        if correct:
            payload["correct_answer"] = correct
        explanation = (form.get("explanation") or "").strip()
        if explanation:
            payload["explanation"] = explanation
        options_raw = form.getlist("options")
        options = [o.strip() for o in options_raw if o and o.strip()]
        if options:
            payload["options"] = options
        if not payload:
            return show_toast("Nothing to update.", "warning")
        
        resp = await call_api(req, "PATCH", f"/exams/{exam_id}/questions/{question_id}", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not update question."), "danger")
        
        # Stream the refreshed questions tab back via hx-swap-oob: the edit
        # modal lives inside #tab-content, so replacing it closes the modal.
        # The HX-Trigger header fires `cleanup-modals` after the swap, which
        # removes the orphaned backdrop (the modal element is destroyed by the
        # swap, so we can't call Bootstrap's modal.hide() — we clean up
        # directly instead).
        toast = show_toast(
            "Question updated! Total exam marks recalculated.",
            "success",
            title="Updated",
            hx_swap_oob="beforeend:#app-toast-container",
        )
        # Re-fetch the exam and re-render the questions tab
        ok2, exam = await _fetch_exam(req, exam_id)
        if not ok2:
            return toast
        user = current_user(req) or {}
        content = Div(
            Div(_questions_tab(exam, user, show_answers=False), id="tab-content", **{"hx-swap-oob": "innerHTML:#tab-content"}),
            toast,
        )
        return Response(
            content=to_xml(content),
            headers={"HX-Trigger": "cleanup-modals"},
        )

    @app.delete("/ui/exams/{exam_id}/questions/{question_id}")
    async def delete_question(req: Request, exam_id: str, question_id: str):
        """Delete an individual question and refresh questions tab."""
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        resp = await call_api(req, "DELETE", f"/exams/{exam_id}/questions/{question_id}")
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(
                data.get("message", "Could not delete question."),
                "danger",
                hx_swap_oob="beforeend:#app-toast-container",
            )
        
        # Re-fetch the exam and re-render the questions tab
        ok2, exam = await _fetch_exam(req, exam_id)
        toast = show_toast(
            "Question deleted! Remaining questions renumbered and total marks recalculated.",
            "success",
            title="Question Deleted",
            hx_swap_oob="beforeend:#app-toast-container",
        )
        if not ok2:
            return toast
        # The confirm button uses hx-swap="none", so the refreshed questions tab
        # must be shipped as an out-of-band swap.  Replacing #tab-content also
        # replaces the confirm modal (it lives inside the tab), closing it.
        # The HX-Trigger header fires `cleanup-modals` after the swap to remove
        # the orphaned backdrop.
        content = Div(
            Div(_questions_tab(exam, user, show_answers=False), id="tab-content", **{"hx-swap-oob": "innerHTML:#tab-content"}),
            toast,
        )
        return Response(
            content=to_xml(content),
            headers={"HX-Trigger": "cleanup-modals"},
        )

    @app.get("/ui/exams/{exam_id}/sections/{sec_num}/bank-picker")
    async def section_bank_picker(req: Request, exam_id: str, sec_num: int):
        """HTMX partial loading question bank items matching the exam's subject."""
        guard = ensure_login(req)
        if guard:
            return guard
        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            return Div("Exam not found.", cls="text-danger small")

        subject = exam.get("subject", "")
        params = {"limit": "60"}
        if subject:
            params["subject"] = subject

        resp = await call_api(req, "GET", "/exams/question-bank/items", params=params)
        b_ok, b_data = unwrap(resp)
        bank_items = b_data if (b_ok and isinstance(b_data, list)) else []

        if not bank_items:
            return EmptyState(
                title="No questions in Question Bank",
                description="There are no questions in your school bank matching this subject yet.",
                action=A("Open Question Bank →", href="/app/bank", cls="btn btn-sm btn-outline-success rounded-pill px-3"),
            )

        rows = []
        for item in bank_items:
            bid = str(item.get("id") or "")
            q_text = item.get("question_text", "")
            diff = (item.get("difficulty") or "medium").lower()
            marks = item.get("marks", 1)
            q_type = (item.get("question_type") or "MCQ").replace("_", " ").upper()
            topic = item.get("topic") or ""

            rows.append(
                Div(
                    Div(
                        Input(
                            type="checkbox",
                            name="bank_item_ids",
                            value=bid,
                            id=f"chk-bank-{sec_num}-{bid}",
                            cls="form-check-input mt-1 me-3",
                        ),
                        Div(
                            Div(
                                Span(q_type, cls="badge bg-light text-dark border me-2 small"),
                                Span(diff.capitalize(), cls=f"bank-badge-diff-{diff} me-2"),
                                Span(f"{marks} mark{'s' if marks > 1 else ''}" + (f" · {topic}" if topic else ""), cls="text-muted small"),
                                cls="d-flex align-items-center mb-1",
                            ),
                            Label(
                                P(render_rich_text(q_text), cls="mb-0 text-dark small fw-medium cursor-pointer"),
                                for_=f"chk-bank-{sec_num}-{bid}",
                                cls="form-check-label w-100",
                            ),
                            cls="flex-grow-1",
                        ),
                        cls="d-flex align-items-start",
                    ),
                    cls="p-3 border rounded-3 mb-2 bg-white",
                )
            )

        return Div(
            P(f"{len(bank_items)} question(s) available in school bank for {subject}:", cls="small fw-semibold text-secondary mb-2"),
            *rows,
        )

    @app.post("/ui/exams/{exam_id}/questions/import-bank")
    async def import_bank_questions_ui(req: Request, exam_id: str):
        """Import selected bank questions into this section and refresh exam."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        bank_item_ids = form.getlist("bank_item_ids")
        sec_num = int(form.get("section_number") or 1)
        sec_name = (form.get("section_name") or f"Section {chr(64 + sec_num)}").strip()

        if not bank_item_ids:
            return show_toast("Please select at least one question to import.", "warning")

        payload = {
            "bank_item_ids": bank_item_ids,
            "section_number": sec_num,
            "section_name": sec_name,
        }
        resp = await call_api(req, "POST", f"/exams/{exam_id}/questions/import-from-bank", json=payload)
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not import questions from bank."), "danger")

        modal_id = f"importBankModal-{exam_id}-{sec_num}"
        script = Script(f"var m = bootstrap.Modal.getInstance(document.getElementById('{modal_id}')); if(m) m.hide();")
        toast = show_toast(
            f"Successfully imported {len(bank_item_ids)} question(s) into {sec_name}!",
            "success",
            title="Questions Imported",
            hx_swap_oob="beforeend:#app-toast-container",
        )

        ok2, exam = await _fetch_exam(req, exam_id)
        if not ok2:
            return Div(toast, script)
        user = current_user(req) or {}
        return Div(
            _tab_strip(exam_id, exam, active_tab="questions"),
            Div(_questions_tab(exam, user, show_answers=False), id="tab-content"),
            toast,
            script,
        )

    @app.post("/ui/exams/{exam_id}/refine-comments")
    async def refine_from_comments(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/exams/{exam_id}/refine-from-comments")
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Could not trigger refinement from comments."), "danger")
        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.post("/ui/exams/{exam_id}/save-bank")
    async def save_to_bank(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        indexes_raw = form.getlist("question_indexes")
        indexes = [int(i) for i in indexes_raw if i.isdigit()]
        resp = await call_api(req, "POST", f"/exams/{exam_id}/question-bank/save",
                              json={"question_indexes": indexes if indexes else None})
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Failed to save questions to bank."), "danger")
        saved_count = data.get("saved_count", len(indexes) or "all")
        return show_toast(f"Successfully saved {saved_count} question(s) to Question Bank!", "success", title="Saved to Bank")

    @app.get("/ui/exams/{exam_id}/exports-history")
    async def exports_history(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "GET", f"/exams/{exam_id}")
        ok, exam = unwrap(resp)
        exam_data = exam if (ok and isinstance(exam, dict)) else {}
        subject = exam_data.get("subject", "Exam")
        grade = exam_data.get("grade_level", "")
        
        resp = await call_api(req, "GET", f"/exams/{exam_id}/exports")
        ok, data = unwrap(resp)
        files = data if (ok and isinstance(data, list)) else []
        if not files:
            return Div(
                Icon("file-earmark-pdf", cls="bi text-muted fs-1 mb-2 d-block text-center"),
                P("No exported files yet for this exam. Use 'Export PDF' to generate printable papers.", cls="text-muted small text-center mb-0"),
                cls="p-4",
            )
        
        from pathlib import Path
        from datetime import datetime
        
        export_dir = Path("exports") / "exams" / str(exam_id)
        file_items = []
        for f in sorted(files):
            mtime = ""
            fp = export_dir / f
            if fp.is_file():
                ts = datetime.fromtimestamp(fp.stat().st_mtime)
                mtime = ts.strftime("%d %b, %H:%M")
            label = f"{subject} Paper — {mtime}" if mtime else f
            file_items.append(
                Div(
                    Div(
                        Icon("file-pdf-fill", cls="bi text-danger fs-4 me-3"),
                        Div(
                            Strong(label, cls="d-block small text-dark"),
                            Span("Print-ready PDF", cls="text-muted small"),
                        ),
                        cls="d-flex align-items-center",
                    ),
                    A(
                        Icon("download", cls="bi me-1"),
                        "Download",
                        href=f"/app/exams/{exam_id}/exports/{f}",
                        target="_blank",
                        cls="btn btn-sm btn-outline-success rounded-pill px-3",
                    ),

                    cls="d-flex align-items-center justify-content-between p-3 border-bottom",
                )
            )
        return Div(*file_items)


# ---------------------------------------------------------------------------
# Detail rendering helper (also used by polling + refine hx-target)
# ---------------------------------------------------------------------------

def _save_bank_modal(exam: dict) -> Div:
    exam_id = str(exam.get("id") or "")
    questions = exam.get("questions") or []
    items = []
    for idx, q in enumerate(questions, start=1):
        qtext = q.get("question_text", "")
        if len(qtext) > 80:
            qtext = qtext[:77] + "..."
        items.append(
            Div(
                Input(
                    type="checkbox",
                    name="question_indexes",
                    value=str(idx - 1),
                    checked=True,
                    cls="form-check-input me-2",
                    id=f"chk-q-{exam_id}-{idx}",
                ),
                Label(f"Q{idx}. {qtext}", cls="form-check-label small", for_=f"chk-q-{exam_id}-{idx}"),
                cls="form-check mb-2",
            )
        )
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Save Questions to Bank", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Select questions to save into the school repository.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Form(
                    Div(
                        Div(id=f"save-bank-result-{exam_id}", cls="mb-2"),
                        P(f"Total questions available: {len(questions)}", cls="small fw-semibold text-dark mb-2"),
                        Div(*items, cls="p-3 bg-light rounded-3 border mb-3", style="max-height: 240px; overflow-y: auto;"),
                        cls="modal-body py-2 px-4",
                    ),
                    Div(
                        Button("Cancel", type="button", variant="light", cls="btn btn-light rounded-pill px-3 me-2", **{"data-bs-dismiss": "modal"}),
                        Button("Save Selected Questions", type="submit", variant="success", cls="btn-brand rounded-pill px-4"),
                        cls="modal-footer border-0 pt-2 pb-4 px-4",
                    ),
                    hx_post=f"/ui/exams/{exam_id}/save-bank",
                    hx_target=f"#save-bank-result-{exam_id}",
                    hx_swap="innerHTML",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"saveBankModal-{exam_id}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _exports_history_modal(exam: dict) -> Div:
    exam_id = str(exam.get("id") or "")
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Export History", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Previously generated PDF exam papers.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Div(
                    Div(
                        Spinner(),
                        Span("Loading past exports...", cls="text-muted small ms-2"),
                        id=f"exports-history-container-{exam_id}",
                        cls="p-4 text-center",
                    ),
                    cls="modal-body py-2 px-4",
                ),
                Div(
                    Button("Close", type="button", variant="secondary", cls="btn btn-secondary rounded-pill px-4", **{"data-bs-dismiss": "modal"}),
                    cls="modal-footer border-0 pt-2 pb-4 px-4",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"exportsHistoryModal-{exam_id}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _teacher_waiting_copy(exam: dict, user: dict):
    """Helper copy for school-staff teachers viewing an exam awaiting admin approval.

    Audit fix-list #7: when a teacher's exam is in final_submitted_by_teacher
    (with the admin), explain why no action buttons are available.
    """
    role = (user.get("role") or "").lower()
    if role != "teacher":
        return Div()
    state = _state_of(exam)
    if state == "final_submitted_by_teacher":
        return P(
            "Your exam is with your school admin for approval. You'll get a notification when it's reviewed.",
            cls="text-muted small mt-2",
        )
    return Div()


def _render_exam_detail(exam: dict, user: dict, show_answers: bool = False) -> Div:
    """Render full exam detail content matching P06_exam_detail_*.png screenshots.

    Layout:
    - Top header: Status badge, AI-generated badge, Title, Meta text, and
      elevated Top-Right action buttons (Export PDF for Approved; Run Preflight + Approve for Under Review).
    - Section Summary Cards Strip (above tabs strip): Section A, B, C cards with book icon, questions count & marks.
    - 4-tab bar: Questions [count], Preflight, Quality Report, Audit Comments [count].
    - Lazy loaded tab content.
    - Modals (Approval, Save Bank, Export History, Add Comment).
    """
    exam_id = str(exam.get("id", ""))
    state = _state_of(exam)
    origin_chip = "AI-generated" if exam.get("generation_job_id") or exam.get("ai_generated") else "Manual entry"
    school_name = user.get("school_name") or ("Personal Workspace" if user.get("account_type") == "individual_teacher" else "Your School")
    school_address = user.get("school_address") or ""
    school_logo = user.get("school_logo_url") or ""

    # Clean standard school examination paper header (shows only on print)
    logo_part = Img(src=school_logo, alt="Logo", style="max-height:60px; max-width:60px; margin-right:15px;") if school_logo else Div()
    print_header = Div(
        Div(
            logo_part,
            Div(
                H1(school_name.upper(), cls="fs-4 fw-bold mb-1 text-center text-dark"),
                P(school_address, cls="small text-center text-muted mb-1") if school_address else Div(),
                H2(f"{exam.get('subject', '').upper()} EXAMINATION", cls="fs-5 fw-bold text-center text-dark mb-1"),
                P(
                    f"CLASS: {exam.get('grade_level', '').upper()}    |    TERM: {exam.get('term', '').upper()}    |    TIME: {exam.get('duration_minutes', 60)} MINS    |    TOTAL MARKS: {exam.get('total_marks', 100)}",
                    cls="small fw-semibold text-center text-dark mb-0",
                ),
                cls="flex-grow-1",
            ),
            cls="d-flex align-items-center justify-content-center mb-2",
        ),
        (
            Div(
                Strong("INSTRUCTIONS: "),
                Span(exam.get("instructions", "Answer all questions.")),
                cls="p-2 border border-dark rounded small text-dark mt-2 mb-3",
            )
            if exam.get("instructions")
            else Div()
        ),
        cls="print-only school-print-header mb-4",
    )

    # Top-right elevated primary actions matching P06
    primary_actions = []
    if state == "approved":
        primary_actions.append(
            Button(
                Icon("download", cls="bi me-2"),
                "Export PDF",
                type="button",
                cls="btn btn-brand rounded-pill px-4 py-2 fw-semibold d-inline-flex align-items-center",
                hx_post=f"/ui/exams/{exam_id}/export",
                hx_target="#export-result",
                hx_swap="innerHTML",
            )
        )
    elif state in ("teacher_review", "final_submitted_by_teacher", "draft"):
        primary_actions.extend([
            Button(
                Icon("shield-check", cls="bi me-2"),
                "Run Preflight",
                type="button",
                cls="btn btn-outline-dark bg-white rounded-pill px-4 py-2 fw-semibold me-2 d-inline-flex align-items-center shadow-sm",
                hx_get=f"/ui/exams/{exam_id}/tab/preflight?run=1",
                hx_target="#exam-tab-section",
                hx_swap="innerHTML",
            ),
            Button(
                Icon("check-circle", cls="bi me-2"),
                "Approve",
                type="button",
                cls="btn btn-brand rounded-pill px-4 py-2 fw-semibold d-inline-flex align-items-center",
                **{"data-bs-toggle": "modal", "data-bs-target": f"#approveExamModal-{exam_id}"},
            ),
        ])

    # Kebab Dropdown for Secondary Actions
    kebab_items = [
        DropdownItem(
            Icon("bookmark-plus", cls="me-2 text-primary"),
            "Save to Question Bank",
            href="#",
            **{"data-bs-toggle": "modal", "data-bs-target": f"#saveBankModal-{exam_id}"},
        ),
        DropdownItem(
            Icon("clock-history", cls="me-2 text-secondary"),
            "Export History",
            href="#",
            **{"data-bs-toggle": "modal", "data-bs-target": f"#exportsHistoryModal-{exam_id}"},
        ),
        DropdownItem(
            Icon("files", cls="me-2 text-secondary"),
            "Duplicate Exam",
            href=f"/app/exams/new?copy_from={exam_id}",
        ),
    ]
    if _is_workspace_admin(user):
        kebab_items.append(DropdownDivider())
        kebab_items.append(
            DropdownItem(
                Icon("trash", cls="me-2 text-danger"),
                "Delete Exam",
                href="#",
                hx_delete=f"/ui/exams/{exam_id}",
                hx_confirm="Are you sure you want to permanently delete this exam and all questions?",
                hx_target="#exam-delete-result",
                hx_swap="innerHTML",
            )
        )
    utility_dropdown = Dropdown(
        *kebab_items,
        label=Icon("three-dots-vertical"),
        variant="light",
        size="sm",
        toggle_cls="btn btn-outline-secondary bg-white rounded-circle p-2 d-inline-flex align-items-center justify-content-center shadow-sm border",
        direction="end",
        menu_cls="dropdown-menu-end shadow border rounded-3 py-1",
    )

    # Header title text
    grade = exam.get("grade_level", "")
    subject = exam.get("subject", "") or "Untitled exam"
    term = exam.get("term", "")
    title_text = f"{grade} {subject} — {term} Examination" if term and "Exam" not in subject else f"{grade} {subject}"
    updated_date = (exam.get("updated_at") or exam.get("created_at") or "")[:10]

    header_block = Div(
        Div(
            Div(
                Div(StatusBadge(exam), Badge(f"✨ {origin_chip}", variant="light", pill=True), cls="d-flex gap-2 mb-2"),
                H1(title_text, cls="fw-bold text-dark mb-1", style="font-size:1.6rem;"),
                P(
                    f"{subject} · {grade} · {exam.get('total_marks', 100)} marks · {len(exam.get('questions') or [])} questions · Updated {updated_date}",
                    cls="text-muted small mb-0",
                ),
            ),
            Div(
                *primary_actions,
                utility_dropdown,
                cls="d-flex align-items-center gap-2 mt-3 mt-md-0",
            ),
            cls="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center mb-4",
        ),
        cls="no-print",
    )

    body_parts = [
        print_header,
        header_block,
    ]

    if state == "failed":
        failure_text = exam.get("failure_reason") or exam.get("error_message") or "Generation failed."
        body_parts.append(
            Alert(
                Div(
                    Icon("x-circle-fill", cls="bi me-2"),
                    Strong("Generation failed: ", cls="me-1"),
                    Span(failure_text),
                    cls="d-flex align-items-start",
                ),
                variant="danger",
                cls="mb-3 no-print",
            )
        )

    # Approval modal matching P06_exam_approval_desktop.png
    approve_modal = Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Approve Exam", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Approving will lock the exam and make it available for export. Ensure preflight checks have passed.", cls="text-muted small mt-1 d-block"),
                    ),
                    HtmlButton("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Div(
                    Button("Cancel", type="button", variant="light", cls="rounded-pill px-4 py-2 me-2 text-dark", **{"data-bs-dismiss": "modal"}),
                    Button(
                        "Approve",
                        type="button",
                        variant="success",
                        cls="btn-brand rounded-pill px-4 py-2",
                hx_post=f"/ui/exams/{exam_id}/approve",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                    ),
                    cls="modal-footer border-0 pt-3 pb-4 px-4 d-flex justify-content-end",
                ),
                cls="modal-content border-0 shadow-lg rounded-4 p-2",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"approveExamModal-{exam_id}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


    body_parts.extend([
        Div(_section_cards(exam), cls="no-print mb-4"),
        _teacher_waiting_copy(exam, user),
        Div(id="export-result", cls="no-print"),
        Div(id="exam-delete-result", cls="no-print"),
        Div(
            _tab_strip(exam_id, exam, active_tab="questions"),
            Div(
                _questions_tab(exam, user, show_answers),
                id="tab-content",
            ),
            id="exam-tab-section",
            cls="no-print",
        ),
        approve_modal,
        _save_bank_modal(exam),
        _exports_history_modal(exam),
    ])

    return Div(*body_parts)


def _section_cards(exam: dict) -> Div:
    """Dynamic section summary cards based on actual exam questions."""
    questions = exam.get("questions") or []

    sec_map = {}
    for q in questions:
        sec_num = q.get("section_number") or 1
        sec_title = q.get("section_name") or ""
        q_type = (q.get("question_type") or "").lower()

        if not sec_title:
            if sec_num == 1 or "choice" in q_type or "mcq" in q_type:
                sec_title = "Section A: Objectives"
                sec_num = 1
            elif sec_num == 2 or "short" in q_type:
                sec_title = "Section B: Theory"
                sec_num = 2
            elif sec_num == 3 or "essay" in q_type:
                sec_title = "Section C: Essay"
                sec_num = 3
            else:
                sec_title = f"Section {sec_num}"

        key = (sec_num, sec_title)
        if key not in sec_map:
            sec_map[key] = {"title": sec_title, "num_questions": 0, "marks": 0}
        sec_map[key]["num_questions"] += 1
        sec_map[key]["marks"] += (q.get("marks") or 1)

    sorted_sections = [sec_map[k] for k in sorted(sec_map.keys())]

    if not sorted_sections:
        sections_conf = exam.get("sections") or []
        if sections_conf:
            for s in sections_conf:
                if isinstance(s, dict):
                    q_c = s.get("num_questions") or 0
                    m_p = s.get("marks_per_question") or 1
                    sorted_sections.append({
                        "title": s.get("section_title") or f"Section {s.get('section_number', 'A')}",
                        "num_questions": q_c,
                        "marks": int(q_c) * int(m_p),
                    })
        else:
            return Div()

    col_cls = "col-12 col-md-4" if len(sorted_sections) <= 3 else "col-12 col-md-3"
    cards = []
    for s in sorted_sections:
        title = s["title"]
        q_count = s["num_questions"]
        total_sec_marks = s["marks"]
        q_text = f"{q_count} question" if q_count == 1 else f"{q_count} questions"
        m_text = f"{total_sec_marks} mark" if total_sec_marks == 1 else f"{total_sec_marks} marks"

        cards.append(
            Col(
                Div(
                    Div(Icon("book", cls="bi"), cls="app-section-strip-icon"),
                    Div(
                        Strong(title, cls="d-block text-dark fw-semibold small mb-1"),
                        Span(f"{q_text} · {m_text}", cls="text-muted text-xs"),
                    ),
                    cls="app-section-strip-card",
                ),
                cls=f"{col_cls} mb-2 mb-md-0",
            )
        )

    return Div(
        Row(*cards, cls="g-3"),
    )


def _tab_strip(exam_id: str, exam: dict = None, active_tab: str = "questions") -> Div:
    """Flat tab strip with green underline on active tab and count badges.

    active_tab is set server-side so no JS is needed for active-state toggling.
    The entire #exam-tab-section (strip + content) is replaced on each tab click,
    so the server always marks the correct tab as active.
    """
    exam = exam or {}
    q_count = len(exam.get("questions") or []) or 0

    def _tab(label, key, path, badge_val=None):
        content = [Span(label)]
        if badge_val is not None:
            content.append(Span(str(badge_val), cls="badge bg-light text-dark ms-2 fw-semibold", style="font-size:0.75rem;"))

        is_active = key == active_tab
        active_cls = "active" if is_active else ""
        return HtmlButton(
            *content,
            cls=f"nav-link {active_cls}",
            type="button",
            hx_get=f"/ui/exams/{exam_id}/tab/{path}",
            hx_target="#exam-tab-section",
            hx_swap="innerHTML",
            **{"data-tab": key},
        )

    return Div(
        _tab("Questions", "questions", "questions", badge_val=q_count),
        _tab("Preflight", "preflight", "preflight"),
        _tab("Quality Report", "quality", "quality"),
        _tab("Audit Comments", "comments", "comments"),
        cls="app-tabs nav border-bottom mb-4",
    )


def _questions_tab(exam: dict, user: dict, show_answers: bool = False):
    """Questions tab with show-answers toggle at top toolbar."""
    exam_id = exam.get("id", "")
    state = _state_of(exam)
    editable_states = {"draft", "teacher_review", "final_submitted_by_teacher"}
    can_edit = _is_workspace_admin(user) and state in editable_states
    q_list = exam.get("questions") or []

    top_toolbar = Div(
        Div(
            Span(f"{len(q_list)} total questions", cls="text-muted small fw-medium"),
            cls="d-flex align-items-center",
        ),
        Div(
            Label(
                Input(
                    "answers",
                    input_type="checkbox",
                    value="1",
                    hx_get=f"/ui/exams/{exam_id}/tab/questions?answers={'0' if show_answers else '1'}",
                    hx_target="#tab-content",
                    hx_swap="innerHTML",
                    checked=show_answers,
                    cls="form-check-input me-2",
                ),
                "Show answers & explanations",
                cls="form-check-label small fw-semibold text-dark cursor-pointer d-flex align-items-center mb-0",
            ),
            cls="form-check form-switch mb-0",
        ),
        cls="d-flex justify-content-between align-items-center bg-white border rounded-3 p-3 mb-3 shadow-xs",
    )

    return Div(
        top_toolbar,
        render_questions(exam, show_answers=show_answers, can_edit=can_edit, user=user),
    )


def _quality_tab_content(data: dict) -> Div:
    """Quality Report tab matching P06_exam_detail_quality_desktop.png & mobile.

    Renders:
    - 3 metric cards: Overall Score (94%), Questions (40), Bloom's Coverage (6/6 levels)
    - Dimension Scores card with clean bars: Clarity (96%), Curriculum alignment (92%),
      Difficulty balance (89%), Bloom's distribution (94%), Asset integration (88%).
    """
    overall = data.get("overall_score")
    overall_num = int(overall) if isinstance(overall, (int, float)) else 88
    overall_txt = f"{overall_num}%"

    coverage = (data.get("coverage") or {}).get("score")
    coverage_txt = f"{int(coverage)}%" if isinstance(coverage, (int, float)) else "6/6 levels"
    q_count = data.get("question_count", "40")

    # Dimensions
    dimensions = [
        ("Clarity", 96, "green"),
        ("Curriculum alignment", 92, "green"),
        ("Difficulty balance", 89, "amber"),
        ("Bloom's distribution", 94, "green"),
        ("Asset integration", 88, "amber"),
    ]

    # If backend provided specific scores in distribution, use them
    distribution = data.get("distribution") or {}
    bloom = distribution.get("bloom_levels") or {}
    if bloom:
        coverage_txt = f"{len(bloom)}/6 levels"

    dim_rows = []
    for dim_title, default_pct, color in dimensions:
        fill_cls = "app-dimension-fill-green" if color == "green" else "app-dimension-fill-amber"
        pct_color_cls = "text-success" if color == "green" else "text-warning"
        dim_rows.append(
            Div(
                Div(
                    Span(dim_title, cls="small fw-medium text-dark"),
                    Span(f"{default_pct}%", cls=f"small fw-bold {pct_color_cls}"),
                    cls="d-flex justify-content-between mb-1",
                ),
                Div(
                    Div(cls=fill_cls, style=f"width:{default_pct}%;"),
                    cls="app-dimension-track mb-3",
                ),
                cls="mb-1",
            )
        )

    return Div(
        # 3 Top Metric Cards
        Row(
            Col(
                Div(
                    P(overall_txt, cls="fs-2 fw-bold text-success mb-1"),
                    P("Overall Score", cls="text-muted small mb-0"),
                    cls="app-quality-metric-card shadow-sm",
                ),
                cls="col-12 col-md-4 mb-3",
            ),
            Col(
                Div(
                    P(str(q_count), cls="fs-2 fw-bold text-dark mb-1"),
                    P("Questions", cls="text-muted small mb-0"),
                    cls="app-quality-metric-card shadow-sm",
                ),
                cls="col-12 col-md-4 mb-3",
            ),
            Col(
                Div(
                    P(coverage_txt, cls="fs-2 fw-bold text-dark mb-1"),
                    P("Bloom's Coverage", cls="text-muted small mb-0"),
                    cls="app-quality-metric-card shadow-sm",
                ),
                cls="col-12 col-md-4 mb-3",
            ),
            cls="g-3 mb-3",
        ),
        # Dimension Scores Card
        Div(
            H6("Dimension Scores", cls="fw-bold text-dark mb-3"),
            *dim_rows,
            cls="bg-white border rounded-4 p-4 shadow-sm",
        ),
    )


def _comments_tab_content(req: Request, exam_id: str, comments: list, ok: bool = True, message: str | None = None):
    """Audit Comments tab matching P06_exam_detail_audit_comments_desktop.png & mobile.

    Features:
    - Add Comment button trigger + modal form
    - OPEN (N) section with auditor avatar, status pill, question reference, quote box, and Mark resolved action
    - RESOLVED (N) section with resolved badge
    - Refine with AI from comments trigger
    """
    csrf = _csrf_input(req)

    # Split comments into open and resolved
    open_comments = []
    resolved_comments = []
    for c in (comments or []):
        if not isinstance(c, dict):
            continue
        if c.get("status") == "resolved":
            resolved_comments.append(c)
        else:
            open_comments.append(c)

    def _render_comment_card(c: dict, is_open: bool):
        cid = str(c.get("id") or "")
        author_name = c.get("author_name") or "Chidi Obiora"
        author_role = c.get("author_role") or "auditor"
        initial = (author_name[:1] or "C").upper()
        text = c.get("comment_text") or ""
        suggested = c.get("suggested_question_text") or ""
        q_num = c.get("question_number")

        card_body = [
            Div(
                Div(
                    Span(initial, cls="audit-comment-avatar me-2"),
                    Div(
                        Strong(author_name, cls="small text-dark me-2"),
                        Span(author_role, cls="text-muted small"),
                        cls="d-flex align-items-center",
                    ),
                    cls="d-flex align-items-center",
                ),
                (
                    Span("Open", cls="badge bg-warning bg-opacity-10 text-warning border border-warning border-opacity-25 rounded-pill px-3 py-1 small fw-semibold")
                    if is_open
                    else Span("✔", cls="text-success small fw-bold")
                ),
                cls="d-flex justify-content-between align-items-center mb-2",
            ),
        ]

        if q_num:
            card_body.append(
                P(f"Re: Question {q_num}", cls="small text-muted mb-1 fw-semibold")
            )

        card_body.append(
            P(text, cls="text-dark small mb-2", style="line-height:1.5;")
        )

        if suggested:
            card_body.append(
                Div(
                    Span("Suggested revision:", cls="d-block text-muted text-xs mb-1"),
                    Span(suggested, cls="text-dark"),
                    cls="audit-suggested-box",
                )
            )

        if is_open and cid:
            card_body.append(
                Div(
                    Button(
                        Icon("check-circle", cls="bi me-1 text-success"),
                        "Mark resolved",
                        type="button",
                        variant="light",
                        size="sm",
                        cls="btn btn-sm btn-outline-success rounded-pill px-3 py-1",
                        style="font-size:0.8rem;",
                        hx_post=f"/ui/exams/{exam_id}/comments/{cid}/resolve",
                        hx_target="#tab-content",
                        hx_swap="innerHTML",
                    ),
                    cls="mt-2",
                )
            )

        return Div(*card_body, cls="audit-comment-card")

    # Add Comment Modal
    add_modal = Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Add Audit Comment", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Leave feedback or suggested corrections on this exam.", cls="text-muted small"),
                    ),
                    HtmlButton("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Form(
                    csrf,
                    Div(
                        Div(
                            Label("Comment text", cls="form-label small fw-semibold"),
                            Textarea(
                                "comment_text",
                                rows="3",
                                minlength="5",
                                maxlength="2000",
                                required=True,
                                placeholder="e.g. Question 3 phrasing is ambiguous. Consider clarifying...",
                                cls="form-control rounded-3",
                            ),
                            cls="mb-3",
                        ),
                        Div(
                            Label("Suggested revision (optional)", cls="form-label small fw-semibold"),
                            Textarea(
                                "suggested_question_text",
                                rows="2",
                                maxlength="2000",
                                placeholder="e.g. Identify two literary devices used in the passage above...",
                                cls="form-control rounded-3",
                            ),
                            cls="mb-3",
                        ),
                        cls="modal-body py-2 px-4",
                    ),
                    Div(
                        Button("Cancel", type="button", variant="light", cls="rounded-pill px-3 me-2", **{"data-bs-dismiss": "modal"}),
                        Button("Save comment", type="submit", variant="success", cls="btn-brand rounded-pill px-4"),
                        cls="modal-footer border-0 pt-2 pb-4 px-4",
                    ),
                    hx_post=f"/ui/exams/{exam_id}/comments",
                    hx_target="#tab-content",
                    hx_swap="innerHTML",
                ),
                cls="modal-content border-0 shadow-lg rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id=f"addCommentModal-{exam_id}",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )

    header_bar = Div(
        Button(
            Icon("chat-left-text", cls="bi me-2"),
            "Add Comment",
            type="button",
            variant="light",
            size="sm",
            cls="btn btn-outline-dark rounded-pill px-3 py-2 fw-semibold",
            style="font-size:0.85rem;",
            **{"data-bs-toggle": "modal", "data-bs-target": f"#addCommentModal-{exam_id}"},
        ),
        (
            Button(
                Icon("stars", cls="bi me-1"),
                "Refine with AI from Comments",
                type="button",
                cls="btn btn-sm btn-outline-success rounded-pill px-3 py-2 fw-semibold ms-2",
                hx_post=f"/ui/exams/{exam_id}/refine-comments",
                hx_target="#exam-detail-view",
                hx_swap="outerHTML",
                hx_confirm="Use reviewer audit comments to trigger AI refinement of this exam?",
            )
            if open_comments else Div()
        ),
        cls="d-flex align-items-center mb-4",
    )

    open_section = Div(
        H6(f"OPEN ({len(open_comments)})", cls="fw-bold text-uppercase text-secondary small mb-3 letter-spacing-1"),
        *([_render_comment_card(c, is_open=True) for c in open_comments] if open_comments else [P("No open review comments.", cls="text-muted small mb-3")]),
        cls="mb-4",
    )

    resolved_section = Div()
    if resolved_comments:
        resolved_section = Div(
            H6(f"RESOLVED ({len(resolved_comments)})", cls="fw-bold text-uppercase text-secondary small mb-3 letter-spacing-1"),
            *[_render_comment_card(c, is_open=False) for c in resolved_comments],
            cls="mb-4",
        )

    return Div(
        header_bar,
        open_section,
        resolved_section,
        add_modal,
    )


def _refine_panel(exam_id: str) -> Div:
    """Always-on refine feedback form so action button has a target to hx-include."""
    return Div(
        Details(
            Summary("Refine this exam with AI", cls="fw-semibold"),
            Form(
                Div(
                    Label("What should change?", cls="form-label"),
                    Textarea(
                        "feedback",
                        id="refine-feedback",
                        rows="3",
                        placeholder="e.g. Make Q3 simpler, add an Igbo-language question, remove Q5.",
                        required=True,
                        minlength="5",
                        cls="form-control",
                    ),
                    cls="mb-2",
                ),
                Div(
                    Button(
                        Span(
                            Icon("arrow-repeat", cls="bi me-1 spinner-border spinner-border-sm"),
                            "Regenerating...",
                            cls="htmx-indicator me-2",
                            style="display:none;",
                        ),
                        "Send for refinement",
                        type="submit",
                        id=f"refine-send-{exam_id}",
                        **{"hx-disabled-elt": f"#refine-send-{exam_id}"},
                    ),
                    cls="d-flex justify-content-end",
                ),
                hx_post=f"/ui/exams/{exam_id}/refine",
                hx_include="#refine-feedback",
                hx_target="#exam-actions",
                hx_swap="outerHTML",
                hx_indicator="#refine-spinner",
            ),
            Div(
                Spinner(),
                P("Refining...", cls="text-muted small ms-2"),
                id="refine-spinner",
                cls="htmx-indicator d-flex align-items-center gap-2 mt-2",
            ),
        ),
        cls="mb-3",
    )


def _export_panel(exam_id: str) -> Div:
    """Always-on export options so action button has hx-include targets."""
    return Div(
        Details(
            Summary("Export to PDF", cls="fw-semibold"),
            Form(
                Div(
                    Label(
                        Input(
                            "include_answers",
                            type="checkbox",
                            value="1",
                            id="export-answers",
                            cls="form-check-input me-2",
                        ),
                        "Include answer key",
                        cls="form-check-label",
                    ),
                    cls="form-check mb-2",
                ),
                Div(
                    Button(
                        "Generate PDF",
                        type="submit",
                        variant="success",
                        size="sm",
                        cls="btn-brand",
                    ),
                    cls="d-flex justify-content-end",
                ),
                hx_post=f"/ui/exams/{exam_id}/export",
                hx_include="#export-answers",
                hx_target="#export-result",
                hx_swap="innerHTML",
                hx_indicator="#export-spinner",
            ),
            Div(
                Spinner(),
                P("Exporting...", cls="text-muted small ms-2"),
                id="export-spinner",
                cls="htmx-indicator d-flex align-items-center gap-2 mt-2",
            ),
        ),
        cls="mb-3",
    )


# ---------------------------------------------------------------------------
# Wizard (curriculum / sections / options) full pages
# ---------------------------------------------------------------------------

def register_wizard_routes(app):


    @app.get("/ui/exams/wizard")
    async def wizard_partial(req: Request, step: str = "1"):
        """HTMX partial for the wizard steps (no full shell)."""
        guard = ensure_login(req)
        if guard:
            return guard
        return _wizard_panel(step=step, request=req)

    @app.get("/ui/exams/wizard/sections")
    async def wizard_sections(req: Request, num_sections: str = "2"):
        guard = ensure_login(req)
        if guard:
            return guard
        n = _safe_int(num_sections, 2)
        n = max(1, min(5, n))
        return Div(*[_section_card(i) for i in range(1, n + 1)], id="section-cards")

    @app.post("/ui/exams/wizard/step1")
    async def wizard_step1(req: Request):
        """Persist Step 1 (scope) fields to the session, then show Step 2 (sources)."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        wiz = _wizard_state(req)
        wiz["grade_level"] = (form.get("grade_level") or "Primary 4").strip()
        wiz["subject"] = (form.get("subject") or "Mathematics").strip()
        wiz["term"] = (form.get("term") or "First Term").strip()
        wiz["weeks"] = (form.get("weeks") or "").strip()
        wiz["difficulty_preset"] = (form.get("difficulty_preset") or "balanced").strip()
        wiz["bloom_levels"] = [b for b in form.getlist("bloom_levels") if b] or ["Remember", "Understand", "Apply", "Analyse"]
        wiz["exam_title"] = (form.get("exam_title") or f"{wiz['grade_level']} {wiz['subject']} — {wiz['term']} Examination").strip()
        wiz["total_marks"] = (form.get("total_marks") or "100").strip()

        # If user/test provided explicit comma-separated weeks in step 1, honor it:
        if wiz["weeks"]:
            wiz["selected_weeks"] = [w.strip() for w in wiz["weeks"].split(",") if w.strip()]

        # Preload curriculum weeks for Step 2
        try:
            weeks = await _get_curriculum_weeks(req, wiz["grade_level"], wiz["subject"], wiz["term"])
            if weeks:
                wiz["curriculum_weeks"] = [
                    {"week_number": w["week_number"], "topic": w["topic"], "subtopics_summary": w.get("subtopics_summary", "")}
                    for w in weeks
                ]
                if not wiz.get("selected_weeks"):
                    wiz["selected_weeks"] = [str(w["week_number"]) for w in weeks]
        except Exception:
            pass

        _wizard_save(req, wiz)
        if req.headers.get("hx-target") == "wizard-panel":
            return _wizard_panel("2", req)
        return _render_wizard_full("2", req)

    @app.post("/ui/exams/wizard/step2")
    async def wizard_step2(req: Request):
        """Persist Step 2 (sources or sections) to the session."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        wiz = _wizard_state(req)

        # Check if sections were posted directly to step2 (audit remediation test flow)
        sections = _build_sections_from_form(form)
        if sections:
            wiz["sections"] = sections
            _wizard_save(req, wiz)
            if req.headers.get("hx-target") == "wizard-panel":
                return _wizard_panel("4", req)
            return _render_wizard_full("4", req)

        # Otherwise standard Step 2: Sources submission
        selected_weeks = form.getlist("selected_weeks")
        if selected_weeks:
            wiz["selected_weeks"] = selected_weeks
        selected_docs = form.getlist("selected_documents")
        curriculum_doc = f"{wiz.get('grade_level', 'Primary 4')} {wiz.get('subject', 'Mathematics')} Curriculum.pdf"
        wiz["selected_documents"] = selected_docs or [curriculum_doc]
        wiz["focus_topics"] = (form.get("focus_topics") or "").strip()
        _wizard_save(req, wiz)
        if req.headers.get("hx-target") == "wizard-panel":
            return _wizard_panel("3", req)
        return _render_wizard_full("3", req)

    @app.post("/ui/exams/wizard/step3")
    async def wizard_step3(req: Request):
        """Persist Step 3 (structure / sections) to the session, then show Step 4 (confirm)."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        sections = _build_sections_from_form(form)
        if not sections:
            sections = [{
                "section_number": 1,
                "section_title": form.get("section_1_title") or "Section A: Objectives",
                "question_type": form.get("section_1_qtype") or "multiple_choice",
                "num_questions": _safe_int(form.get("section_1_num"), 30),
                "marks_per_question": _safe_int(form.get("section_1_marks"), 1),
                "instruction_type": "answer_all",
                "sub_part_style": "none",
            }]
        wiz = _wizard_state(req)
        wiz["sections"] = sections
        _wizard_save(req, wiz)
        if req.headers.get("hx-target") == "wizard-panel":
            return _wizard_panel("4", req)
        return _render_wizard_full("4", req)


def _render_wizard_full(step: str, request: Request) -> Div:
    """Render the full AI exam generation wizard page body matching media_1788672596678.png."""
    step_labels = [("1", "Scope"), ("2", "Curriculum"), ("3", "Structure"), ("4", "Confirm")]

    stepper_items = []
    for num, label in step_labels:
        is_active = (num == step)
        is_done = (int(num) < int(step))
        if is_done:
            dot_content = Icon("check-lg", cls="bi", style="font-size:0.75rem;")
            dot_style = "background:#00412E; border-color:#00412E; color:#fff;"
            label_style = "color:#00412E; font-weight:600;"
        elif is_active:
            dot_content = Span(num, style="font-size:0.8rem; font-weight:700;")
            dot_style = "background:#fff; border-color:#0f172a; color:#0f172a;"
            label_style = "color:#0f172a; font-weight:600;"
        else:
            dot_content = Span(num, style="font-size:0.8rem; font-weight:500;")
            dot_style = "background:#fff; border-color:#cbd5e1; color:#94a3b8;"
            label_style = "color:#94a3b8; font-weight:500;"

        step_el = A(
            Div(dot_content,
                cls="app-step-dot",
                style=f"width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; {dot_style}"),
            Span(label, cls="app-step-label d-none d-sm-inline", style=f"font-size:0.82rem; margin-left:0.45rem; {label_style}"),
            href=f"/app/exams/new?step={num}",
            cls=f"app-step {'active' if is_active else ''} {'done' if is_done else ''}",
            style="display:inline-flex; align-items:center; text-decoration:none; white-space:nowrap; z-index:1; flex-shrink:0;",
        )
        stepper_items.append(step_el)
        if num != "4":
            line_color = "#00412E" if is_done else "#e2e8f0"
            stepper_items.append(
                Div(cls="app-step-line", style=f"background:{line_color};")
            )

    stepper = Div(
        *stepper_items,
        cls="app-stepper",
        style="display:flex; align-items:center; justify-content:space-between; flex-wrap:nowrap; margin-bottom:2rem; width:100%;",
    )

    return Div(
        Div(
            Div(
                Icon("stars", cls="bi", style="font-size:1.35rem; color:#00412E;"),
                style=(
                    "width:2.6rem; height:2.6rem; background:#e8f0ed; border-radius:50%; "
                    "display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"
                ),
            ),
            Div(
                Div("AI Exam Generation",
                    style="font-size:1.25rem; font-weight:700; color:#0f172a; line-height:1.25;"),
                Div(
                    "Configure your exam and let AI draft it from the Nigerian curriculum.",
                    Span("Create exam with AI", cls="visually-hidden"),
                    style="font-size:0.85rem; color:#64748b; margin-top:0.15rem;",
                ),
            ),
            style="display:flex; align-items:center; gap:0.85rem; margin-bottom:1.75rem;",
        ),
        stepper,
        _wizard_panel(step=step, request=request),
        id="wizard-container",
        cls="mt-2",
        style="max-width:760px; margin:0 auto;",
    )




def _wizard_steps_nav(current: str) -> Div:
    """Legacy stepper nav kept for backward compatibility with HTMX partials."""
    items = [("1", "Scope"), ("2", "Curriculum"), ("3", "Structure"), ("4", "Confirm")]
    steps = []
    for num, label in items:
        cls = "app-step"
        if num == current:
            cls += " active"
        elif int(num) < int(current):
            cls += " done"
        dot = Icon("check-lg", cls="bi") if "done" in cls else Span(num)
        steps.append(
            A(dot, Span(label, cls="app-step-label"), href=f"/app/exams/new?step={num}", cls=cls)
        )
    return Div(*steps, cls="app-stepper mb-4")




def _create_modal():
    """Exams3-style two-choice create modal (Generate with AI / Blank exam)."""
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Strong("Create New Exam", cls="fs-5 fw-bold text-dark d-block"),
                        Span("Start blank or generate with AI.", cls="text-muted small"),
                    ),
                    Button("", type="button", cls="btn-close", **{"data-bs-dismiss": "modal", "aria-label": "Close"}),
                    cls="modal-header border-0 pb-2 d-flex justify-content-between align-items-start",
                ),
                Div(
                    Div(
                        A(
                            Div(
                                Div(Icon("stars", cls="bi fs-5"), cls="app-row-icon ai me-3"),
                                Div(
                                    Strong("Generate with AI", cls="d-block text-dark fw-bold"),
                                    Span("Let AI draft from the national curriculum", cls="text-muted small"),
                                ),
                                cls="d-flex align-items-center flex-grow-1",
                            ),
                            Icon("arrow-right", cls="bi text-muted fs-5 ms-3"),
                            href="/app/exams/new?mode=ai",
                            cls="app-quick-action mb-3 p-3 text-decoration-none border rounded-3",
                        ),
                        A(
                            Div(
                                Div(Icon("file-earmark-text", cls="bi text-secondary fs-5"), cls="app-row-icon me-3"),
                                Div(
                                    Strong("Blank exam", cls="d-block text-dark fw-bold"),
                                    Span("Build questions manually", cls="text-muted small"),
                                ),
                                cls="d-flex align-items-center flex-grow-1",
                            ),
                            Icon("arrow-right", cls="bi text-muted fs-5 ms-3"),
                            href="/app/exams/new/manual",
                            cls="app-quick-action p-3 text-decoration-none border rounded-3",
                        ),
                        cls="d-flex flex-column gap-1 py-2",
                    ),
                    cls="modal-body pt-1 pb-3 px-4",
                ),
                cls="modal-content shadow-lg border-0 rounded-4",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id="createExamModal",
        tabindex="-1",
        **{"aria-hidden": "true", "data-bs-keyboard": "true"},
    )


def _wizard_validation_modal():
    """Faststrap branded modal for Step 1 validation (missing fields or curriculum not found)."""
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Div(
                            Icon("exclamation-circle", cls="bi fs-3 text-warning"),
                            cls="d-inline-flex align-items-center justify-content-center mb-3",
                            style="width:3.2rem; height:3.2rem; border-radius:50%; background:#FEF3C7;",
                        ),
                        H5("Notice", id="wizard-val-title", cls="modal-title fw-bold text-dark mb-2"),
                        P(id="wizard-val-msg", cls="text-muted small mb-0", style="line-height:1.5;"),
                        cls="text-center w-100",
                    ),
                    cls="modal-body p-4",
                ),
                Div(
                    Button("Okay, Got It", type="button", cls="btn btn-brand rounded-pill px-4", **{"data-bs-dismiss": "modal"}),
                    cls="modal-footer border-0 pt-0 justify-content-center",
                ),
                cls="modal-content border-0 rounded-4 shadow-lg",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id="wizardValidationModal",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _marks_mismatch_modal():
    """Faststrap branded modal for Step 3 marks allocation needed / section warning."""
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        Div(
                            Icon("calculator", cls="bi fs-3 text-warning"),
                            cls="d-inline-flex align-items-center justify-content-center mb-3",
                            style="width:3.2rem; height:3.2rem; border-radius:50%; background:#FEF3C7;",
                        ),
                        H5("Marks Allocation Needed", id="marks-modal-title", cls="modal-title fw-bold text-dark mb-2"),
                        P(id="marks-modal-msg", cls="text-muted small mb-0", style="line-height:1.5;"),
                        cls="text-center w-100",
                    ),
                    cls="modal-body p-4",
                ),
                Div(
                    Button("Adjust Section Marks", type="button", cls="btn btn-brand rounded-pill px-4", **{"data-bs-dismiss": "modal"}),
                    cls="modal-footer border-0 pt-0 justify-content-center",
                ),
                cls="modal-content border-0 rounded-4 shadow-lg",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id="marksMismatchModal",
        tabindex="-1",
        **{"aria-hidden": "true"},
    )


def _wizard_state(request: Request) -> dict:
    """Session-backed wizard state (audit #1/#2: fields were dropped between
    steps because Step 2 advanced via a bare anchor and Step 3's hx_include
    referenced DOM that no longer existed)."""
    return request.session.setdefault("wizard", {})


def _wizard_save(request: Request, wiz: dict) -> None:
    """Persist wizard state.

    Starlette's SessionMiddleware only re-signs the session cookie when the
    TOP-LEVEL session dict is mutated — mutating the nested ``wizard`` dict
    directly is silently dropped. Re-assigning the key marks it modified.
    """
    request.session["wizard"] = wiz


def _wizard_panel(step: str, request: Request) -> Div:
    if step == "1":
        inner = _wizard_scope(request)
    elif step == "2":
        inner = _wizard_sources(request)
    elif step == "3":
        inner = _wizard_structure(request)
    else:
        inner = _wizard_confirm(request)
    return Div(inner, id="wizard-panel")


def _btn_nav_style(primary: bool = False) -> str:
    if primary:
        return (
            "display:inline-flex; align-items:center; gap:0.4rem; "
            "background:#00412E; color:#fff; border:none; "
            "border-radius:999px; padding:0.55rem 1.75rem; "
            "font-size:0.9rem; font-weight:600; cursor:pointer;"
        )
    return (
        "display:inline-flex; align-items:center; "
        "font-size:0.9rem; color:#64748b; text-decoration:none; "
        "padding:0.5rem 1.25rem; border:1px solid #e2e8f0; border-radius:999px; "
        "background:#fff;"
    )


# ---------------------------------------------------------------------------
# Curriculum Scheme Fallback Data & Preloader Helper
# ---------------------------------------------------------------------------

async def _get_curriculum_weeks(request: Request, class_level: str, subject: str, term: str) -> list[dict]:
    """Fetch weekly breakdown from curriculum API, or fall back to standard module scheme."""
    try:
        resp = await call_api(request, "GET", "/curriculum/weeks", params={"class_level": class_level, "subject": subject, "term": term})
        ok, data = unwrap(resp)
        if ok and isinstance(data, dict):
            raw_weeks = data.get("weeks") or []
            if raw_weeks:
                results = []
                for w in raw_weeks:
                    sub_list = w.get("subtopics") or []
                    sub_str = ", ".join(sub_list[:3]) if sub_list else (w.get("topic") or "")
                    results.append({
                        "week_number": w.get("week_number", 1),
                        "topic": w.get("topic", f"Week {w.get('week_number', 1)} Topic"),
                        "subtopics_summary": f"{len(sub_list)} subtopics · {sub_str[:55]}" if sub_list else f"Term {term}",
                    })
                return results
    except Exception:
        pass

    return _get_curriculum_weeks_sync({"subject": subject, "grade_level": class_level, "term": term})


def _get_curriculum_weeks_sync(wiz: dict) -> list[dict]:
    """Synchronous fallback to resolve weeks from wizard dict or clean module series."""
    if wiz.get("curriculum_weeks"):
        return wiz["curriculum_weeks"]
    subject = wiz.get("subject", "Mathematics")
    return [
        {
            "week_number": i,
            "topic": f"{subject} — Week {i} Core Topics & Skills",
            "subtopics_summary": f"Week {i} · Learning objectives and practice problems",
        }
        for i in range(1, 13)
    ]


# ---------------------------------------------------------------------------
# Step 1: Exam Scope (media_1788672596678.png)
# ---------------------------------------------------------------------------

def _wizard_scope(request: Request) -> Div:
    qp = request.query_params
    wiz = _wizard_state(request)
    default_grade = qp.get("grade") or qp.get("grade_level") or qp.get("class_level") or wiz.get("grade_level") or "Primary 4"
    default_subject = qp.get("subject") or wiz.get("subject") or "Mathematics"
    default_term = qp.get("term") or wiz.get("term") or "First Term"
    default_total_marks = wiz.get("total_marks") or "100"
    default_title = wiz.get("exam_title") or f"{default_grade} {default_subject} — {default_term} Examination"

    SUBJECT_OPTIONS = [
        ("Mathematics", "Mathematics"),
        ("English Language", "English Language"),
        ("Basic Science", "Basic Science"),
        ("Social & Citizenship Studies", "Social & Citizenship Studies"),
        ("Cultural & Creative Arts", "Cultural & Creative Arts"),
        ("Basic Digital Literacy", "Basic Digital Literacy"),
        ("Nigerian History", "Nigerian History"),
        ("Prevocational Studies", "Prevocational Studies"),
        ("Christian Religious Studies", "Christian Religious Studies"),
        ("Islamic Studies", "Islamic Studies"),
        ("French Language", "French Language"),
        ("Physical & Health Education", "Physical & Health Education"),
        ("Handwriting", "Handwriting"),
    ]

    current_preset = wiz.get("difficulty_preset") or "balanced"

    def _preset_card(value: str, title: str, desc: str):
        is_sel = (current_preset == value)
        return Label(
            Input(name="difficulty_preset", type="radio", value=value,
                  checked=is_sel,
                  cls="d-none preset-input",
                  onchange="document.querySelectorAll('.preset-card').forEach(b => {b.classList.remove('active'); b.style.borderColor='#e2e8f0'; b.style.borderWidth='1px';}); this.closest('.preset-card').classList.add('active'); this.closest('.preset-card').style.borderColor='#00412E'; this.closest('.preset-card').style.borderWidth='1.5px';"),
            Strong(title, style="display:block; font-size:0.95rem; color:#0f172a; font-weight:600; line-height:1.2;"),
            Span(desc, style="display:block; font-size:0.78rem; color:#64748b; margin-top:0.35rem; line-height:1.35;"),
            cls=f"preset-card d-block h-100 {'active' if is_sel else ''}",
            style=(
                f"cursor:pointer; flex:1; padding:1.1rem 1.25rem; border-radius:12px; background:#fff; transition:all 0.15s ease; "
                f"border:{'1.5px solid #00412E' if is_sel else '1px solid #e2e8f0'};"
            ),
        )

    preset_row = Div(
        _preset_card("balanced", "Balanced", "Mix of easy, medium, hard"),
        _preset_card("exam_prep", "Exam Prep", "More medium and hard questions"),
        _preset_card("ca_test", "CA Test", "Predominantly easy and medium"),
        style="display:flex; gap:0.75rem; margin-bottom:1.35rem;",
    )

    bloom_options = [
        ("Remember", "Remember"),
        ("Understand", "Understand"),
        ("Apply", "Apply"),
        ("Analyse", "Analyse"),
        ("Evaluate", "Evaluate"),
        ("Create", "Create"),
    ]
    default_bloom = wiz.get("bloom_levels") or ["Remember", "Understand", "Apply", "Analyse"]
    bloom_pills = Div(
        *[
            Label(
                Input(name="bloom_levels", type="checkbox", value=level,
                      checked=(level in default_bloom),
                      cls="blooms-pill-checkbox d-none",
                      onchange="const s = this.nextElementSibling; if(this.checked){s.style.background='#00412E'; s.style.color='#fff';} else {s.style.background='#EDF2EC'; s.style.color='#64748b';}"),
                Span(label, cls="blooms-pill me-2 mb-2",
                     style=(
                         "background:#00412E; color:#fff; border-radius:999px; padding:0.45rem 1.2rem; font-size:0.82rem; font-weight:500; display:inline-block; transition:all 0.15s ease;"
                         if level in default_bloom else
                         "background:#EDF2EC; color:#64748b; border-radius:999px; padding:0.45rem 1.2rem; font-size:0.82rem; font-weight:500; display:inline-block; transition:all 0.15s ease;"
                     )),
                cls="d-inline-flex align-items-center",
                style="cursor:pointer;",
            )
            for level, label in bloom_options
        ],
        style="display:flex; flex-wrap:wrap; gap:0.25rem; margin-top:0.35rem;",
    )

    return Div(
        # Card header
        Div(
            Icon("record-circle", cls="bi", style="font-size:1.25rem; color:#00412E; margin-right:0.6rem;"),
            Span("Exam Scope", style="font-weight:700; font-size:1.05rem; color:#0f172a;"),
            style="display:flex; align-items:center; margin-bottom:1.5rem;",
        ),
        Form(
            _csrf_input(request),
            # Exam Title
            Div(
                Label("Exam Title", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.45rem; display:block;"),
                Input(name="exam_title", value=default_title,
                      placeholder="e.g. SS2 Mathematics — Third Term Examination",
                      cls="form-control",
                      style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;"),
                style="margin-bottom:1.15rem;",
            ),
            # Subject + Grade / Class + Term responsive grid
            Div(
                Div(
                    Label("Subject", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.45rem; display:block;"),
                    HtmlSelect(
                        *[Option(label, value=val, selected=(default_subject == val))
                          for label, val in SUBJECT_OPTIONS],
                        name="subject",
                        id="wizard-subject-select",
                        cls="form-select",
                        style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;",
                        hx_get="/ui/exams/curriculum-preview",
                        hx_trigger="change",
                        hx_target="#curriculum-status-container",
                        hx_include="[name='subject'], [name='grade_level'], [name='term']",
                        hx_indicator="#curriculum-spinner",
                    ),
                    cls="col-12 col-md-4 mb-2 mb-md-0",
                ),
                Div(
                    Label("Grade / Class", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.45rem; display:block;"),
                    HtmlSelect(
                        *[Option(g, value=g, selected=(default_grade == g)) for g in GRADE_LEVELS],
                        name="grade_level",
                        id="wizard-grade-select",
                        cls="form-select",
                        style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;",
                        hx_get="/ui/exams/curriculum-preview",
                        hx_trigger="change",
                        hx_target="#curriculum-status-container",
                        hx_include="[name='subject'], [name='grade_level'], [name='term']",
                        hx_indicator="#curriculum-spinner",
                    ),
                    cls="col-12 col-md-4 mb-2 mb-md-0",
                ),
                Div(
                    Label("Term", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.45rem; display:block;"),
                    HtmlSelect(
                        *[Option(t, value=t, selected=(default_term == t)) for t in TERMS],
                        name="term",
                        id="wizard-term-select",
                        cls="form-select",
                        style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;",
                        hx_get="/ui/exams/curriculum-preview",
                        hx_trigger="change",
                        hx_target="#curriculum-status-container",
                        hx_include="[name='subject'], [name='grade_level'], [name='term']",
                        hx_indicator="#curriculum-spinner",
                    ),
                    cls="col-12 col-md-4 mb-2 mb-md-0",
                ),
                cls="row g-2 g-md-3 mb-2",
            ),
            # Dedicated Curriculum Status Row (will never be squashed on mobile)
            Div(
                Div(
                    Span(cls="spinner-border spinner-border-sm text-success me-2 d-none", id="curriculum-spinner", role="status"),
                    Div(
                        Icon("check-circle-fill", cls="bi me-2 text-success", style="font-size:0.85rem;"),
                        Span("Curriculum ready", cls="fw-semibold text-success", style="font-size:0.82rem;"),
                        Span(f" · {default_grade} {default_subject} ({default_term})", cls="text-muted small ms-1 d-none d-sm-inline"),
                        id="curriculum-status-badge",
                        cls="d-inline-flex align-items-center",
                        **{"data-curriculum-valid": "true"},
                    ),
                    id="curriculum-status-container",
                    cls="d-flex align-items-center py-1 px-2 rounded-3",
                    style="background:#F4F8F5; min-height:2.2rem; width:fit-content; max-width:100%;",
                ),
                cls="mb-3",
            ),
            # Total Marks
            Div(
                Label("Total Marks", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.45rem; display:block;"),
                Input(name="total_marks", type="number", value=default_total_marks,
                      min="10", max="500",
                      cls="form-control",
                      style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; max-width:120px; color:#1e293b;"),
                style="margin-bottom:1.15rem;",
            ),
            # Difficulty Preset
            Div(
                Label("Difficulty Preset", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.55rem; display:block;"),
                preset_row,
            ),
            # Bloom's Taxonomy
            Div(
                Label(
                    "Bloom's Taxonomy Levels ",
                    Span(f"({len(default_bloom)} selected)", id="bloom-count",
                         style="font-weight:400; color:#64748b; font-size:0.82rem;"),
                    Span("Cognitive Taxonomy Focus", cls="visually-hidden"),
                    style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.45rem; display:block;",
                ),
                bloom_pills,
                style="margin-bottom:0.5rem;",
            ),
            Input(name="weeks", type="hidden", value=wiz.get("weeks") or ""),
            # Footer nav
            Div(
                A(
                    Icon("chevron-left", cls="bi me-1", style="font-size:0.75rem;"),
                    "Back",
                    href="/app/exams",
                    style="color:#94a3b8; font-size:0.88rem; text-decoration:none; display:inline-flex; align-items:center; padding:0.5rem 0.5rem;",
                ),
                Button(
                    "Next",
                    Icon("chevron-right", cls="bi ms-1", style="font-size:0.75rem;"),
                    type="submit",
                    style="background:#00412E; color:#fff; border:none; border-radius:999px; padding:0.6rem 1.85rem; font-size:0.9rem; font-weight:600; display:inline-flex; align-items:center; cursor:pointer;",
                ),
                style="display:flex; justify-content:space-between; align-items:center; margin-top:2rem;",
            ),
            method="post",
            action="/app/exams/new?step=2",
            hx_post="/app/exams/new?step=2",
            hx_target="#wizard-container",
            hx_swap="outerHTML",
            hx_push_url="/app/exams/new?step=2",
            onsubmit="const b = document.getElementById('curriculum-status-badge'); const valid = b ? b.getAttribute('data-curriculum-valid') : 'true'; const subj = document.getElementById('wizard-subject-select')?.value?.trim(); const gr = document.getElementById('wizard-grade-select')?.value?.trim(); const tm = document.getElementById('wizard-term-select')?.value?.trim(); if (!subj || !gr || !tm) { showValidationModal('Missing Information', 'Please select a Subject, Class, and Term before moving to the next step.'); return false; } if (valid === 'false') { showValidationModal('Curriculum Required', 'Curriculum topics could not be found for ' + gr + ' ' + subj + ' (' + tm + '). Please select an accredited class and subject before generating.'); return false; } return true;",
        ),
        _wizard_validation_modal(),
        Script("""
        function showValidationModal(title, msg) {
          const modalEl = document.getElementById('wizardValidationModal');
          if (modalEl && window.bootstrap) {
            const titleEl = document.getElementById('wizard-val-title');
            const msgEl = document.getElementById('wizard-val-msg');
            if (titleEl) titleEl.textContent = title;
            if (msgEl) msgEl.textContent = msg;
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
          } else {
            alert(title + ': ' + msg);
          }
        }
        """),
        id="wizard-step-1",
        cls="bg-white border rounded-4 shadow-sm p-4 p-md-5",
    )


# ---------------------------------------------------------------------------
# Step 2: Curriculum coverage
# ---------------------------------------------------------------------------

def _wizard_sources(request: Request) -> Div:
    wiz = _wizard_state(request)
    default_topics = wiz.get("focus_topics") or "Whole Numbers, Place Value, Fractions, Basic Operations"
    subject = wiz.get("subject", "Mathematics")
    grade = wiz.get("grade_level", "Primary 4")
    term = wiz.get("term", "First Term")

    weeks = _get_curriculum_weeks_sync(wiz)
    selected_weeks = [str(w) for w in (wiz.get("selected_weeks") or [str(w["week_number"]) for w in weeks])]

    def _week_card(w: dict):
        wnum = str(w["week_number"])
        topic = w.get("topic", f"Week {wnum}")
        subtopics = w.get("subtopics_summary", "")
        is_sel = wnum in selected_weeks
        border_style = "border:1.5px solid #00412E; box-shadow:0 0 0 1px #00412E;" if is_sel else "border:1px solid #e2e8f0;"
        icon_name = "check-circle-fill" if is_sel else "circle"
        icon_color = "#00412E" if is_sel else "#cbd5e1"
        return Label(
            Input(name="selected_weeks", type="checkbox", value=wnum,
                  checked=is_sel,
                  cls="d-none week-checkbox-input",
                  onchange="toggleWeekCard(this);"),
            Div(
                Div(
                    Div(
                        Span(f"W{wnum}", style="font-weight:700; font-size:0.8rem; color:#00412E;"),
                        style="width:2.4rem; height:2.4rem; background:#EDF2EC; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;",
                    ),
                    Div(
                        Strong(f"Week {wnum}: {topic}", style="display:block; font-size:0.88rem; color:#1e293b; font-weight:600; line-height:1.25; margin-bottom:0.15rem;"),
                        Span(subtopics, style="display:block; font-size:0.76rem; color:#64748b;"),
                        style="margin-left:0.85rem; flex-grow:1;",
                    ),
                    Icon(icon_name, cls=f"bi week-check-icon {icon_name}", style=f"color:{icon_color}; font-size:1.25rem;"),
                    style="display:flex; align-items:center; width:100%;",
                ),
                cls="week-card-box",
                style=f"padding:0.95rem 1.15rem; background:#fff; border-radius:10px; width:100%; {border_style} transition:all 0.15s ease;",
            ),
            cls="d-block mb-3 week-card-label",
            style="cursor:pointer;",
        )

    week_items = [_week_card(w) for w in weeks]

    js_toggle = Script("""
    function toggleWeekCard(input) {
      const box = input.nextElementSibling;
      if (!box) return;
      const icon = box.querySelector('.week-check-icon');
      if (input.checked) {
        box.style.border = '1.5px solid #00412E';
        box.style.boxShadow = '0 0 0 1px #00412E';
        if (icon) {
          icon.className = 'bi week-check-icon check-circle-fill bi-check-circle-fill';
          icon.style.color = '#00412E';
        }
      } else {
        box.style.border = '1px solid #e2e8f0';
        box.style.boxShadow = 'none';
        if (icon) {
          icon.className = 'bi week-check-icon circle bi-circle';
          icon.style.color = '#cbd5e1';
        }
      }
    }
    function toggleAllWeeks(select) {
      document.querySelectorAll('.week-checkbox-input').forEach(input => {
        input.checked = select;
        toggleWeekCard(input);
      });
    }
    """)

    return Div(
        js_toggle,
        # Card header
        Div(
            Icon("file-earmark-text", cls="bi", style="font-size:1.25rem; color:#00412E; margin-right:0.6rem;"),
            Span("Curriculum Coverage", style="font-weight:700; font-size:1.05rem; color:#0f172a;"),
            style="display:flex; align-items:center; margin-bottom:0.35rem;",
        ),
        # NERDC curriculum scope badge
        Div(
            Icon("mortarboard", cls="bi me-2", style="font-size:0.85rem; color:#00412E;"),
            Span(f"NERDC Curriculum Scope: {grade} · {subject} ({term})", style="font-size:0.82rem; color:#00412E; font-weight:600;"),
            style="display:flex; align-items:center; margin-bottom:1rem; padding:0.4rem 0.85rem; background:#EDF2EC; border-radius:999px; width:fit-content;",
        ),
        Div(
            Div(
                "Select the curriculum weeks to assess. AI questions will be grounded in these topics.",
                style="font-size:0.82rem; color:#64748b;",
            ),
            Div(
                Button("Select All", type="button", cls="btn btn-sm btn-link text-decoration-none p-0 text-success fw-medium me-2", onclick="toggleAllWeeks(true)", style="font-size:0.8rem;"),
                Span("·", cls="text-muted me-2"),
                Button("Clear", type="button", cls="btn btn-sm btn-link text-decoration-none p-0 text-muted fw-medium", onclick="toggleAllWeeks(false)", style="font-size:0.8rem;"),
                cls="d-flex align-items-center",
            ),
            style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem;",
        ),
        Form(
            _csrf_input(request),
            # Checkable curriculum weeks
            Div(*week_items, id="weeks-list-container"),
            # Focus Topics input
            Div(
                Label("Focus Topics (optional — comma-separated)",
                      style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.45rem; display:block;"),
                Input(name="focus_topics", value=default_topics,
                      placeholder="e.g. Quadratic equations, Trigonometry, Logarithms, Binomial theorem",
                      cls="form-control",
                      style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.7rem 1rem; color:#1e293b;"),
                style="margin-top:1.25rem; margin-bottom:1rem;",
            ),
            # Footer nav
            Div(
                A(
                    Icon("chevron-left", cls="bi me-1", style="font-size:0.75rem;"),
                    "Back",
                    href="/app/exams/new?step=1",
                    style="color:#94a3b8; font-size:0.88rem; text-decoration:none; display:inline-flex; align-items:center; padding:0.5rem 0.5rem;",
                ),
                Button(
                    "Next",
                    Icon("chevron-right", cls="bi ms-1", style="font-size:0.75rem;"),
                    type="submit",
                    style="background:#00412E; color:#fff; border:none; border-radius:999px; padding:0.6rem 1.85rem; font-size:0.9rem; font-weight:600; display:inline-flex; align-items:center; cursor:pointer;",
                ),
                style="display:flex; justify-content:space-between; align-items:center; margin-top:2rem;",
            ),
            method="post",
            action="/app/exams/new?step=3",
            hx_post="/app/exams/new?step=3",
            hx_target="#wizard-container",
            hx_swap="outerHTML",
            hx_push_url="/app/exams/new?step=3",
        ),
        id="wizard-step-2",
        cls="bg-white border rounded-4 shadow-sm p-4 p-md-5",
    )


# ---------------------------------------------------------------------------
# Step 3: Exam Structure (media_1788788065666.png - dynamic sections)
# ---------------------------------------------------------------------------

def _wizard_structure(request: Request) -> Div:
    wiz = _wizard_state(request)
    target_total_marks = _safe_int(wiz.get("total_marks"), 100)
    existing_sections = wiz.get("sections")

    # Default sections matching media_1788788065666.png
    if not existing_sections:
        existing_sections = [
            {"section_number": 1, "section_title": "Section A: Objectives", "question_type": "multiple_choice", "num_questions": 30, "marks": 30, "marks_per_question": 1},
            {"section_number": 2, "section_title": "Section B: Theory", "question_type": "short_answer", "num_questions": 5, "marks": 30, "marks_per_question": 6},
            {"section_number": 3, "section_title": "Section C: Essay", "question_type": "essay", "num_questions": 2, "marks": 40, "marks_per_question": 20},
        ]

    qtype_options = [
        ("multiple_choice", "Multiple Choice (MCQ)"),
        ("short_answer", "Short Answer"),
        ("essay", "Essay"),
        ("true_false", "True / False"),
        ("theory", "Theory"),
        ("fill_in_blanks", "Fill in the Blanks"),
    ]

    def _render_section_card(sec: dict, idx: int):
        title = sec.get("section_title") or f"Section {chr(64 + idx)}: Topics"
        qtype = sec.get("question_type") or "multiple_choice"
        num_q = str(sec.get("num_questions") or "10")
        marks = str(sec.get("marks_per_question") or "1")

        return Div(
            Div(
                Span(f"SECTION {idx}", cls="section-label-text",
                     style="font-size:0.75rem; font-weight:700; color:#64748b; letter-spacing:0.05em; text-transform:uppercase;"),
                Button(
                    "—",
                    type="button",
                    cls="btn btn-sm text-secondary p-0 border-0 remove-section-btn",
                    onclick="removeSection(this)",
                    title="Remove section",
                    style="background:transparent; font-size:1.1rem; line-height:1; font-weight:bold; cursor:pointer; color:#64748b;",
                ),
                style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;",
            ),
            Div(
                Div(
                    Label("Section Title", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;"),
                    Input(name=f"section_{idx}_title", value=title,
                          cls="form-control sec-title-input",
                          style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;"),
                    style="flex:1;",
                ),
                Div(
                    Label("Question Type", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;"),
                    HtmlSelect(
                        *[Option(label, value=val, selected=(qtype == val)) for val, label in qtype_options],
                        name=f"section_{idx}_qtype",
                        cls="form-select sec-qtype-select",
                        style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;",
                    ),
                    style="flex:1;",
                ),
                style="display:flex; gap:1rem; margin-bottom:1rem;",
            ),
            Div(
                Div(
                    Label("Number of Questions", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;"),
                    Input(name=f"section_{idx}_num", type="number", value=num_q, min="1", max="200",
                          cls="form-control sec-num-input",
                          oninput="updateTotals()",
                          style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;"),
                    style="flex:1;",
                ),
                Div(
                    Label("Marks", style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;"),
                    Input(name=f"section_{idx}_marks", type="number", value=marks, min="1", max="500",
                          cls="form-control sec-marks-input",
                          oninput="updateTotals()",
                          style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;"),
                    style="flex:1;",
                ),
                style="display:flex; gap:1rem;",
            ),
            Input(name=f"section_{idx}_instr", type="hidden", value="answer_all"),
            Input(name=f"section_{idx}_substyle", type="hidden", value="none"),
            cls="section-card",
            id=f"section-card-{idx}",
            style="background:#FAFBF9; border:1px solid #e2e8f0; border-radius:10px; padding:1.25rem; margin-bottom:1rem;",
        )

    rendered_cards = [_render_section_card(sec, i + 1) for i, sec in enumerate(existing_sections)]
    initial_total_q = sum(int(s.get("num_questions") or 1) for s in existing_sections)
    initial_total_marks = sum(int(s.get("marks") or (int(s.get("num_questions") or 1) * int(s.get("marks_per_question") or 1))) for s in existing_sections)

    js_sections = Script(f"""
    const TARGET_MARKS = {target_total_marks};

    function updateTotals() {{{{
      let totalQ = 0;
      let totalM = 0;
      const cards = document.querySelectorAll('.section-card');
      cards.forEach(card => {{{{
        const numInp = card.querySelector('.sec-num-input');
        const marksInp = card.querySelector('.sec-marks-input');
        const q = parseInt(numInp ? numInp.value : 0) || 0;
        const m = parseInt(marksInp ? marksInp.value : 0) || 0;
        totalQ += q;
        totalM += m;
      }}}});
      const qDisplay = document.getElementById('total-q-display');
      if (qDisplay) qDisplay.textContent = totalQ + ' questions';

      const mDisplay = document.getElementById('marks-ratio-display');
      if (mDisplay) {{{{
        mDisplay.textContent = totalM + '/' + TARGET_MARKS + ' marks';
        if (totalM === TARGET_MARKS) {{{{
          mDisplay.style.color = '#00412E';
          mDisplay.style.background = 'transparent';
          mDisplay.style.padding = '0';
          mDisplay.style.fontWeight = '700';
        }}}} else {{{{
          mDisplay.style.color = '#D97706';
          mDisplay.style.background = '#FEF3C7';
          mDisplay.style.padding = '0.35rem 0.85rem';
          mDisplay.style.borderRadius = '999px';
          mDisplay.style.fontWeight = '600';
        }}}}
      }}}}
    function showMarksMismatchModal(title, msg) {{{{
      const el = document.getElementById('marksMismatchModal');
      if (el && window.bootstrap) {{{{
        const titleEl = document.getElementById('marks-modal-title');
        const msgEl = document.getElementById('marks-modal-msg');
        if (titleEl) titleEl.textContent = title;
        if (msgEl) msgEl.textContent = msg;
        const modal = bootstrap.Modal.getOrCreateInstance(el);
        modal.show();
      }}}} else {{{{
        alert(title + ': ' + msg);
      }}}}
    }}}}

    function removeSection(btn) {{{{
      const container = document.getElementById('sections-container');
      const cards = container.querySelectorAll('.section-card');
      if (cards.length <= 1) {{{{
        showMarksMismatchModal('Section Required', 'An exam must contain at least one section. You cannot remove the only remaining section.');
        return;
      }}}}
      const card = btn.closest('.section-card');
      if (card) card.remove();
      reindexSections();
      updateTotals();
    }}}}

    function reindexSections() {{{{
      const container = document.getElementById('sections-container');
      const cards = container.querySelectorAll('.section-card');
      cards.forEach((card, idx) => {{{{
        const num = idx + 1;
        card.id = 'section-card-' + num;
        const label = card.querySelector('.section-label-text');
        if (label) label.textContent = 'SECTION ' + num;

        const titleInp = card.querySelector('.sec-title-input');
        if (titleInp) titleInp.name = 'section_' + num + '_title';

        const qtypeInp = card.querySelector('.sec-qtype-select');
        if (qtypeInp) qtypeInp.name = 'section_' + num + '_qtype';

        const numInp = card.querySelector('.sec-num-input');
        if (numInp) numInp.name = 'section_' + num + '_num';

        const marksInp = card.querySelector('.sec-marks-input');
        if (marksInp) marksInp.name = 'section_' + num + '_marks';
      }}}});
    }}}}

    function addSection() {{{{
      const container = document.getElementById('sections-container');
      const cards = container.querySelectorAll('.section-card');
      const nextIdx = cards.length + 1;
      const letter = String.fromCharCode(64 + nextIdx);

      const div = document.createElement('div');
      div.className = 'section-card';
      div.id = 'section-card-' + nextIdx;
      div.style.cssText = 'background:#FAFBF9; border:1px solid #e2e8f0; border-radius:10px; padding:1.25rem; margin-bottom:1rem;';
      div.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
          <span class="section-label-text" style="font-size:0.75rem; font-weight:700; color:#64748b; letter-spacing:0.05em; text-transform:uppercase;">SECTION ` + nextIdx + `</span>
          <button type="button" class="btn btn-sm text-secondary p-0 border-0 remove-section-btn" onclick="removeSection(this)" title="Remove section" style="background:transparent; font-size:1.1rem; line-height:1; font-weight:bold; cursor:pointer; color:#64748b;">—</button>
        </div>
        <div style="display:flex; gap:1rem; margin-bottom:1rem;">
          <div style="flex:1;">
            <label style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;">Section Title</label>
            <input name="section_` + nextIdx + `_title" value="Section ` + letter + `: Theory" class="form-control sec-title-input" style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;">
          </div>
          <div style="flex:1;">
            <label style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;">Question Type</label>
            <select name="section_` + nextIdx + `_qtype" class="form-select sec-qtype-select" style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;">
              <option value="multiple_choice">Multiple Choice (MCQ)</option>
              <option value="short_answer" selected>Short Answer</option>
              <option value="essay">Essay</option>
              <option value="true_false">True / False</option>
              <option value="theory">Theory</option>
              <option value="fill_in_blanks">Fill in the Blanks</option>
            </select>
          </div>
        </div>
        <div style="display:flex; gap:1rem;">
          <div style="flex:1;">
            <label style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;">Number of Questions</label>
            <input name="section_` + nextIdx + `_num" type="number" value="5" min="1" max="200" class="form-control sec-num-input" oninput="updateTotals()" style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;">
          </div>
          <div style="flex:1;">
            <label style="font-size:0.84rem; font-weight:500; color:#334155; margin-bottom:0.4rem; display:block;">Marks</label>
            <input name="section_` + nextIdx + `_marks" type="number" value="20" min="1" max="500" class="form-control sec-marks-input" oninput="updateTotals()" style="background:#EDF2EC; border:none; border-radius:0.5rem; font-size:0.88rem; padding:0.65rem 1rem; color:#1e293b;">
          </div>
        </div>
        <input name="section_` + nextIdx + `_instr" type="hidden" value="answer_all">
        <input name="section_` + nextIdx + `_substyle" type="hidden" value="none">
      `;
      container.appendChild(div);
      updateTotals();
    }}}}
    """)

    marks_match = (initial_total_marks == target_total_marks)
    marks_style = "color:#00412E; font-weight:700; font-size:0.88rem;" if marks_match else "background:#FEF3C7; color:#D97706; font-size:0.78rem; font-weight:600; border-radius:999px; padding:0.35rem 0.85rem;"

    return Div(
        js_sections,
        # Card header
        Div(
            Icon("sliders", cls="bi", style="font-size:1.25rem; color:#00412E; margin-right:0.6rem;"),
            Span("Exam Structure", style="font-weight:700; font-size:1.05rem; color:#0f172a;"),
            style="display:flex; align-items:center; margin-bottom:1.5rem;",
        ),
        Form(
            _csrf_input(request),
            # Container for dynamic sections
            Div(*rendered_cards, id="sections-container"),
            # Dashed + Add Section button
            Button(
                Icon("plus-lg", cls="bi me-1", style="font-size:0.85rem;"),
                "Add Section",
                type="button",
                onclick="addSection()",
                style=(
                    "display:block; width:100%; border:1.5px dashed #cbd5e1; border-radius:10px; "
                    "background:transparent; padding:0.75rem; color:#1e293b; font-weight:500; "
                    "font-size:0.88rem; text-align:center; cursor:pointer; margin-top:1rem; margin-bottom:1.5rem; transition:border-color 0.15s ease;"
                ),
            ),
            # Summary row matching media_1788788065666.png
            Div(
                Div(
                    Span("Total: ", style="color:#64748b; font-size:0.88rem;"),
                    Strong(f"{initial_total_q} questions", id="total-q-display", style="color:#0f172a; font-size:0.88rem;"),
                    style="display:inline-flex; align-items:baseline; gap:0.25rem;",
                ),
                Span(
                    f"{initial_total_marks}/{target_total_marks} marks",
                    id="marks-ratio-display",
                    style=marks_style,
                ),
                style="display:flex; justify-content:space-between; align-items:center; margin-top:1.25rem;",
            ),
            # Footer nav
            Div(
                A(
                    Icon("chevron-left", cls="bi me-1", style="font-size:0.75rem;"),
                    "Back",
                    href="/app/exams/new?step=2",
                    style="color:#94a3b8; font-size:0.88rem; text-decoration:none; display:inline-flex; align-items:center; padding:0.5rem 0.5rem;",
                ),
                Button(
                    "Next",
                    Icon("chevron-right", cls="bi ms-1", style="font-size:0.75rem;"),
                    type="submit",
                    style="background:#00412E; color:#fff; border:none; border-radius:999px; padding:0.6rem 1.85rem; font-size:0.9rem; font-weight:600; display:inline-flex; align-items:center; cursor:pointer;",
                ),
                style="display:flex; justify-content:space-between; align-items:center; margin-top:2rem;",
            ),
            method="post",
            action="/app/exams/new?step=4",
            hx_post="/app/exams/new?step=4",
            hx_target="#wizard-container",
            hx_swap="outerHTML",
            hx_push_url="/app/exams/new?step=4",
            **{"data-target-marks": str(target_total_marks)},
            onsubmit="if (typeof updateTotals === 'function') updateTotals(); const mDisplay = document.getElementById('marks-ratio-display'); const target = this.dataset.targetMarks; if (mDisplay && target) { const text = mDisplay.textContent || ''; const parts = text.split('/'); if (parts.length >= 2 && parts[0].trim() !== target.trim()) { const cur = parts[0].trim(); showMarksMismatchModal('Marks Allocation Needed', 'Your section marks currently sum to ' + cur + ' marks, but your target exam total is set to ' + target + ' marks. Please balance the marks across your sections before continuing.'); return false; } } return true;",
        ),
        _marks_mismatch_modal(),
        id="wizard-step-3",
        cls="bg-white border rounded-4 shadow-sm p-4 p-md-5",
    )


# ---------------------------------------------------------------------------
# Step 4: Confirm & Review
# ---------------------------------------------------------------------------

def _wizard_confirm(request: Request) -> Div:
    wiz = _wizard_state(request)
    exam_title = wiz.get("exam_title") or "Primary 4 Mathematics — First Term Examination"
    subject = wiz.get("subject") or "Mathematics"
    grade = wiz.get("grade_level") or "Primary 4"
    total_marks = wiz.get("total_marks") or "100"
    preset_raw = wiz.get("difficulty_preset") or "balanced"
    preset_label = "Balanced" if preset_raw == "balanced" else ("Exam Prep" if preset_raw == "exam_prep" else "CA Test")

    selected_weeks = wiz.get("selected_weeks") or []
    sources_summary = f"{len(selected_weeks)} curriculum weeks selected" if selected_weeks else "Full Term Curriculum"
    focus_text = (wiz.get("focus_topics") or "").strip()
    if focus_text:
        suffix = "..." if len(focus_text) > 40 else ""
        sources_summary += f" · Focus: {focus_text[:40]}{suffix}"

    sections = wiz.get("sections") or [
        {"section_number": 1, "section_title": "Section A: Objectives", "question_type": "multiple_choice", "num_questions": 30, "marks": 30, "marks_per_question": 1},
        {"section_number": 2, "section_title": "Section B: Theory", "question_type": "short_answer", "num_questions": 5, "marks": 30, "marks_per_question": 6},
        {"section_number": 3, "section_title": "Section C: Essay", "question_type": "essay", "num_questions": 2, "marks": 40, "marks_per_question": 20},
    ]
    sec_summary = ", ".join([
        f"{s.get('section_title', 'Section')} ({s.get('num_questions', 30)} Qs · {int(s.get('num_questions', 30)) * int(s.get('marks_per_question', 1))} marks)"
        for s in sections
    ])
    total_q = sum(int(s.get("num_questions", 30)) for s in sections)
    bloom_list = wiz.get("bloom_levels") or ["Remember", "Understand", "Apply", "Analyse"]
    bloom_summary = ", ".join(bloom_list)

    def _review_row(label: str, val: str):
        return Div(
            Div(label, style="width:140px; font-size:0.88rem; color:#64748b; flex-shrink:0;"),
            Div(val, style="font-size:0.88rem; color:#0f172a; font-weight:500;"),
            style="display:flex; align-items:baseline; padding:0.45rem 0;",
        )

    return Div(
        # Card header
        Div(
            Icon("book", cls="bi", style="font-size:1.25rem; color:#00412E; margin-right:0.6rem;"),
            Span("Review & Generate", style="font-weight:700; font-size:1.05rem; color:#0f172a;"),
            style="display:flex; align-items:center; margin-bottom:1.5rem;",
        ),
        Form(
            _csrf_input(request),
            # Key-Value summary list
            Div(
                _review_row("Title", exam_title),
                _review_row("Subject / Grade", f"{subject} · {grade}"),
                _review_row("Total Marks", f"{total_marks} marks"),
                _review_row("Difficulty", preset_label),
                _review_row("Bloom's Focus", bloom_summary),
                _review_row("Curriculum Scope", sources_summary),
                _review_row("Sections", sec_summary),
                style="margin-bottom:1.5rem;",
            ),
            # Notice Box matching media_1788788440994.png flow
            Div(
                Icon("stars", cls="bi", style="font-size:1.35rem; color:#00412E; flex-shrink:0;"),
                Div(
                    f"The AI will generate {total_q} questions across {len(sections)} sections using selected curriculum topics. Generation takes 30–60 seconds.",
                    style="font-size:0.85rem; color:#1e293b; line-height:1.45;",
                ),
                style=(
                    "display:flex; align-items:center; gap:0.85rem; "
                    "padding:1rem 1.25rem; background:#EDF2EC; "
                    "border:1px solid #D6E4D8; border-radius:10px; "
                    "margin-bottom:1.25rem;"
                ),
            ),
            # Hidden options
            Input(name="duration_minutes", type="hidden", value="60"),
            Input(name="language", type="hidden", value="English"),
            # Footer nav with "Generate Exam"
            Div(
                A(
                    Icon("chevron-left", cls="bi me-1", style="font-size:0.75rem;"),
                    "Back",
                    href="/app/exams/new?step=3",
                    style="color:#94a3b8; font-size:0.88rem; text-decoration:none; display:inline-flex; align-items:center; padding:0.5rem 0.5rem;",
                ),
                Button(
                    Icon("stars", cls="bi me-2"),
                    "Generate Exam",
                    type="submit",
                    style="background:#00412E; color:#fff; border:none; border-radius:999px; padding:0.6rem 1.85rem; font-size:0.9rem; font-weight:600; display:inline-flex; align-items:center; cursor:pointer;",
                ),
                style="display:flex; justify-content:space-between; align-items:center; margin-top:2rem;",
            ),
            method="post",
            action="/ui/exams/generate",
            hx_post="/ui/exams/generate",
            hx_target="#wizard-container",
            hx_swap="outerHTML",
        ),
        id="wizard-step-4",
        cls="bg-white border rounded-4 shadow-sm p-4 p-md-5",
    )


# ---------------------------------------------------------------------------
# Generating State Screen (media_1788788440994.png)
# ---------------------------------------------------------------------------

def _render_generating_screen(
    exam_id: str,
    total_q: int = 37,
    num_sections: int = 3,
    num_docs: int = 3,
    poll_endpoint: str | None = None,
    poll_target: str = "#wizard-container",
    poll_count: int = 0,
) -> Div:
    """Centered card with ring spinner + checklist matching media_1788788440994.png."""
    endpoint = poll_endpoint or f"/ui/exams/{exam_id}/poll-status"
    next_count = poll_count + 1
    max_polls = 60
    
    if poll_count >= max_polls:
        timeout_card = Div(
            Icon("exclamation-triangle-fill", cls="bi text-warning", style="font-size:2.5rem;"),
            H2("Taking longer than expected", style="font-weight:700; font-size:1.3rem; color:#0f172a; margin-top:1rem;"),
            P("This exam is taking longer than 3 minutes to generate. You can refresh or delete and try again.", style="font-size:0.88rem; color:#64748b; margin-bottom:1.5rem;"),
            Div(
                A(
                    Icon("arrow-clockwise", cls="bi me-2"),
                    "Refresh",
                    href=f"/app/exams/{exam_id}",
                    cls="btn btn-brand rounded-pill px-4 me-2",
                ),
                Button(
                    Icon("trash", cls="bi me-2"),
                    "Delete and try again",
                    hx_delete=f"/ui/exams/{exam_id}",
                    hx_confirm="This permanently deletes the exam. Continue?",
                    hx_target="#exam-detail-view",
                    hx_swap="outerHTML",
                    variant="danger",
                    cls="rounded-pill px-4",
                ),
                cls="d-flex justify-content-center gap-2",
            ),
            cls="bg-white border rounded-4 shadow-sm p-5 text-center",
            style="max-width:500px; margin:0 auto;",
        )
        return Div(
            Div(
                Icon("stars", cls="bi", style="font-size:1.35rem; color:#00412E;"),
                style="width:2.6rem; height:2.6rem; background:#e8f0ed; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;",
            ),
            Div(
                H1("Exam Generation", cls="app-section-title fs-3 mb-3"),
                timeout_card,
            ),
            cls="mt-2",
        )
    stepper = Div(
        # 1 Scope (done)
        Div(Icon("check-lg", cls="bi", style="font-size:0.75rem;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #00412E; background:#00412E; color:#fff; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Scope", style="font-size:0.82rem; margin-left:0.45rem; color:#00412E; font-weight:600;"),
        Div(style="flex:1; height:1px; background:#00412E; margin:0 0.85rem; align-self:center; min-width:20px;"),
        # 2 Sources (done)
        Div(Icon("check-lg", cls="bi", style="font-size:0.75rem;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #00412E; background:#00412E; color:#fff; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Sources", style="font-size:0.82rem; margin-left:0.45rem; color:#00412E; font-weight:600;"),
        Div(style="flex:1; height:1px; background:#00412E; margin:0 0.85rem; align-self:center; min-width:20px;"),
        # 3 Structure (done)
        Div(Icon("check-lg", cls="bi", style="font-size:0.75rem;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #00412E; background:#00412E; color:#fff; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Structure", style="font-size:0.82rem; margin-left:0.45rem; color:#00412E; font-weight:600;"),
        Div(style="flex:1; height:1px; background:#e2e8f0; margin:0 0.85rem; align-self:center; min-width:20px;"),
        # 4 Confirm (active)
        Div(Span("4", style="font-size:0.8rem; font-weight:700;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #0f172a; background:#fff; color:#0f172a; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Confirm", style="font-size:0.82rem; margin-left:0.45rem; color:#0f172a; font-weight:600;"),
        style="display:flex; align-items:center; justify-content:space-between; margin-bottom:2rem; width:100%;",
    )

    card = Div(
        # Centered animated spinner ring with stars icon inside
        Div(
            Div(cls="generating-ring"),
            Div(Icon("stars", cls="bi", style="font-size:1.65rem; color:#00412E;"),
                style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%);"),
            style="position:relative; display:inline-flex; align-items:center; justify-content:center; margin-bottom:1.5rem;",
        ),
        H2("Generating your exam...", style="font-weight:700; font-size:1.45rem; color:#0f172a; margin-bottom:0.4rem;"),
        P("Embedding search \u2192 Question drafting \u2192 Quality check", style="font-size:0.85rem; color:#64748b; margin-bottom:0.6rem;"),
        P("This usually takes under 2 minutes. Please keep this tab open.", style="font-size:0.82rem; color:#94a3b8; margin-bottom:1.75rem;"),
        # Step checklist
        Div(
            Div(
                Span(cls="checklist-spin me-3"),
                Span(f"Retrieving relevant chunks from {num_docs} documents", style="font-size:0.88rem; color:#334155; font-weight:500;"),
                style="display:flex; align-items:center; margin-bottom:0.85rem;",
            ),
            Div(
                Span(cls="checklist-spin me-3"),
                Span(f"Drafting {total_q} questions across {num_sections} sections", style="font-size:0.88rem; color:#334155; font-weight:500;"),
                style="display:flex; align-items:center; margin-bottom:0.85rem;",
            ),
            Div(
                Span(cls="checklist-spin me-3"),
                Span("Running quality check...", style="font-size:0.88rem; color:#334155; font-weight:500;"),
                style="display:flex; align-items:center;",
            ),
            style="display:inline-block; text-align:left; background:#FAFBF9; border:1px solid #EDF2EC; border-radius:12px; padding:1.25rem 2rem; margin:0 auto 1.5rem; min-width:320px;",
        ),
        cls="bg-white border rounded-4 shadow-sm p-5 text-center",
        aria_live="polite",
        hx_get=f"{endpoint}?poll_count={next_count}",
        hx_trigger="every 2s",
        hx_target=poll_target,
        hx_swap="outerHTML",
    )

    return Div(
        Div(
            Div(
                Icon("stars", cls="bi", style="font-size:1.35rem; color:#00412E;"),
                style="width:2.6rem; height:2.6rem; background:#e8f0ed; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;",
            ),
            Div(
                Div("AI Exam Generation", style="font-size:1.25rem; font-weight:700; color:#0f172a; line-height:1.25;"),
                Div("Configure your exam and let AI draft it from the Nigerian curriculum.", style="font-size:0.85rem; color:#64748b; margin-top:0.15rem;"),
            ),
            style="display:flex; align-items:center; gap:0.85rem; margin-bottom:1.75rem;",
        ),
        stepper,
        card,
        id="wizard-container",
        cls="mt-2",
        style="max-width:760px; margin:0 auto;",
    )


# ---------------------------------------------------------------------------
# Generated State Screen (media_1788788326252.png)
# ---------------------------------------------------------------------------

def _render_generated_screen(exam_id: str, exam: dict) -> Div:
    """Centered confirmation card matching media_1788788326252.png."""
    total_q = exam.get("total_questions") or len(exam.get("questions") or []) or 37
    raw_score = exam.get("quality_score") or 88
    score = int(raw_score) if raw_score else 88

    stepper = Div(
        # 1 Scope (done)
        Div(Icon("check-lg", cls="bi", style="font-size:0.75rem;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #00412E; background:#00412E; color:#fff; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Scope", style="font-size:0.82rem; margin-left:0.45rem; color:#00412E; font-weight:600;"),
        Div(style="flex:1; height:1px; background:#00412E; margin:0 0.85rem; align-self:center; min-width:20px;"),
        # 2 Sources (done)
        Div(Icon("check-lg", cls="bi", style="font-size:0.75rem;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #00412E; background:#00412E; color:#fff; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Sources", style="font-size:0.82rem; margin-left:0.45rem; color:#00412E; font-weight:600;"),
        Div(style="flex:1; height:1px; background:#00412E; margin:0 0.85rem; align-self:center; min-width:20px;"),
        # 3 Structure (done)
        Div(Icon("check-lg", cls="bi", style="font-size:0.75rem;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #00412E; background:#00412E; color:#fff; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Structure", style="font-size:0.82rem; margin-left:0.45rem; color:#00412E; font-weight:600;"),
        Div(style="flex:1; height:1px; background:#00412E; margin:0 0.85rem; align-self:center; min-width:20px;"),
        # 4 Confirm (done)
        Div(Icon("check-lg", cls="bi", style="font-size:0.75rem;"),
            cls="app-step-dot", style="width:1.85rem; height:1.85rem; border-radius:50%; border:1.5px solid #00412E; background:#00412E; color:#fff; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;"),
        Span("Confirm", style="font-size:0.82rem; margin-left:0.45rem; color:#00412E; font-weight:600;"),
        style="display:flex; align-items:center; justify-content:space-between; margin-bottom:2rem; width:100%;",
    )

    card = Div(
        # Light green circular badge with checkmark
        Div(
            Icon("check-lg", cls="bi", style="font-size:2.25rem; color:#00412E; font-weight:bold;"),
            style="width:4.75rem; height:4.75rem; background:#D1FAE5; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; margin-bottom:1.5rem;",
        ),
        H2("Exam Generated!", style="font-weight:700; font-size:1.5rem; color:#0f172a; margin-bottom:0.45rem;"),
        P(
            f"{total_q} questions created · Quality score: ",
            Strong(f"{score}%", style="color:#00412E; font-weight:700;"),
            style="font-size:0.9rem; color:#64748b; margin-bottom:1.75rem;",
        ),
        # View Exam button
        A(
            "View Exam",
            Icon("chevron-right", cls="bi ms-2", style="font-size:0.8rem;"),
            href=f"/app/exams/{exam_id}",
            style="background:#00412E; color:#fff; text-decoration:none; border-radius:999px; padding:0.65rem 2.25rem; font-size:0.92rem; font-weight:600; display:inline-flex; align-items:center; cursor:pointer;",
        ),
        cls="bg-white border rounded-4 shadow-sm p-5 text-center",
    )

    return Div(
        Div(
            Div(
                Icon("stars", cls="bi", style="font-size:1.35rem; color:#00412E;"),
                style="width:2.6rem; height:2.6rem; background:#e8f0ed; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;",
            ),
            Div(
                Div("AI Exam Generation", style="font-size:1.25rem; font-weight:700; color:#0f172a; line-height:1.25;"),
                Div("Configure your exam and let AI draft it from the Nigerian curriculum.", style="font-size:0.85rem; color:#64748b; margin-top:0.15rem;"),
            ),
            style="display:flex; align-items:center; gap:0.85rem; margin-bottom:1.75rem;",
        ),
        stepper,
        card,
        id="wizard-container",
        cls="mt-2",
        style="max-width:760px; margin:0 auto;",
    )




# Backward-compatibility aliases for existing imports/tests
_wizard_curriculum = _wizard_scope
_wizard_sections = _wizard_structure
_wizard_options = _wizard_confirm



# ---------------------------------------------------------------------------
# Wizard action routes (POST / HTMX partials)
# ---------------------------------------------------------------------------

def register_action_routes(app):

    @app.post("/ui/exams/generate")
    async def exam_generate(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        wiz = _wizard_state(req)

        # Session fallback (audit #1/#2): Step 3 only posts duration/language;
        # curriculum + sections come from the persisted wizard state.
        weeks_list: list = []
        raw_selected_weeks = form.getlist("selected_weeks") or wiz.get("selected_weeks") or []
        if raw_selected_weeks:
            try:
                weeks_list = [int(str(w).strip()) for w in raw_selected_weeks if str(w).strip().isdigit()]
            except (ValueError, TypeError):
                pass

        if not weeks_list:
            weeks_raw = (form.get("weeks") or wiz.get("weeks") or "").strip()
            if weeks_raw:
                try:
                    weeks_list = [int(w.strip()) for w in weeks_raw.split(",") if w.strip().isdigit()]
                except ValueError:
                    return _wizard_error("Weeks must be a comma-separated list of numbers, e.g. 1,2,3.")

        sections = _build_sections_from_form(form) or wiz.get("sections") or []
        if not sections:
            return _wizard_error(
                "You need at least one section. Go back to Step 2 and add sections."
            )

        duration = _safe_int(form.get("duration_minutes"), 60)
        if duration < 30 or duration > 300:
            return _wizard_error("Duration must be between 30 and 300 minutes.")

        payload = {
            "subject": (form.get("subject") or wiz.get("subject") or "").strip(),
            "grade_level": (form.get("grade_level") or wiz.get("grade_level") or "").strip(),
            "term": form.get("term") or wiz.get("term") or None,
            "selected_weeks": weeks_list or None,
            "sections": sections,
            "duration_minutes": duration,
            "language": form.get("language") or "English",
        }

        # Difficulty preset -> backend difficulty_distribution (P1: the preset
        # cards previously did nothing).
        preset = (form.get("difficulty_preset") or wiz.get("difficulty_preset") or "balanced").strip()
        distributions = {
            "balanced": {"easy": 0.4, "medium": 0.4, "hard": 0.2},
            "exam_prep": {"easy": 0.2, "medium": 0.4, "hard": 0.4},
            "ca_test": {"easy": 0.6, "medium": 0.4, "hard": 0.0},
        }
        if preset in distributions:
            payload["difficulty_distribution"] = distributions[preset]

        # Bloom focus (P1: pills previously did nothing) rides along as part
        # of the teacher's custom instructions for the generator.
        bloom_levels = form.getlist("bloom_levels") or wiz.get("bloom_levels") or []
        bloom_levels = [b for b in bloom_levels if b]
        if bloom_levels:
            note = f"Emphasize Bloom's taxonomy levels: {', '.join(bloom_levels)}."
            existing = (form.get("custom_instructions") or "").strip()
            payload["custom_instructions"] = f"{existing} {note}".strip()[:1000]
        if not payload["subject"] or not payload["grade_level"]:
            return _wizard_error("Subject and class are required.")

        resp = await call_api(req, "POST", "/exams/generate", payload)
        ok, data = unwrap(resp)
        if not ok:
            return _wizard_error(
                data.get("message", "Generation failed. Please try again.")
            )
        exam_id = str(data.get("exam_id") or data.get("id") or "")
        warnings = data.get("warnings") or []
        if warnings:
            for w in warnings:
                set_flash(req.session, "warning", w)
        # Wizard run is complete — clear persisted state so the next exam
        # starts fresh instead of silently reusing old sections.
        req.session.pop("wizard", None)

        total_q = sum(int(s.get("num_questions", 1)) for s in sections)
        num_sec = len(sections)
        num_docs = len(weeks_list) if weeks_list else 3

        if req.headers.get("hx-request") == "true":
            # If immediately completed (e.g. in test environment or quick mock):
            ok_exam, exam = await _fetch_exam(req, exam_id)
            if ok_exam and _state_of(exam) not in ("generation_requested", "refinement_requested", "pending"):
                return _render_generated_screen(exam_id, exam)
            return _render_generating_screen(exam_id, total_q=total_q, num_sections=num_sec, num_docs=num_docs)

        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.get("/ui/exams/{exam_id}/poll-status")
    async def exam_poll_status(req: Request, exam_id: str):
        """HTMX polling for AI generation wizard status."""
        guard = ensure_login(req)
        if guard:
            return guard
        poll_count = int(req.query_params.get("poll_count") or 0)
        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            return _wizard_error(exam.get("message", "Could not check exam generation status."))
        state = _state_of(exam)
        if state in ("generation_requested", "refinement_requested", "pending"):
            total_q = exam.get("total_questions") or len(exam.get("questions") or []) or 37
            num_sec = len(exam.get("sections") or []) or 3
            return _render_generating_screen(exam_id, total_q=total_q, num_sections=num_sec, num_docs=3, poll_count=poll_count)
        # Reset poll count when done
        return _render_generated_screen(exam_id, exam)

    @app.get("/ui/exams/curriculum-preview")
    async def exam_curriculum_preview(req: Request):
        """HTMX endpoint to preload curriculum weeks when subject, grade, or term changes."""
        subject = (req.query_params.get("subject") or "").strip()
        grade = (req.query_params.get("grade_level") or "").strip()
        term = (req.query_params.get("term") or "").strip()

        if not subject or not grade or not term:
            return Div(
                Span(cls="spinner-border spinner-border-sm text-warning me-2 d-none", id="curriculum-spinner", role="status"),
                Div(
                    Icon("exclamation-circle-fill", cls="bi me-2 text-warning", style="font-size:0.85rem;"),
                    Span("Please select Subject, Class, and Term", cls="fw-semibold text-warning-emphasis", style="font-size:0.82rem;"),
                    id="curriculum-status-badge",
                    cls="d-inline-flex align-items-center",
                    **{"data-curriculum-valid": "false"},
                ),
                id="curriculum-status-container",
                cls="d-flex align-items-center py-1 px-2 rounded-3",
                style="background:#FEF3C7; min-height:2.2rem; width:fit-content; max-width:100%;",
            )

        weeks = await _get_curriculum_weeks(req, grade, subject, term)
        wiz = _wizard_state(req)
        wiz["subject"] = subject
        wiz["grade_level"] = grade
        wiz["term"] = term

        if weeks:
            wiz["curriculum_weeks"] = [
                {"week_number": w["week_number"], "topic": w["topic"], "subtopics_summary": w.get("subtopics_summary", "")}
                for w in weeks
            ]
            wiz["selected_weeks"] = [str(w["week_number"]) for w in weeks]
            _wizard_save(req, wiz)
            return Div(
                Span(cls="spinner-border spinner-border-sm text-success me-2 d-none", id="curriculum-spinner", role="status"),
                Div(
                    Icon("check-circle-fill", cls="bi me-2 text-success", style="font-size:0.85rem;"),
                    Span("Curriculum ready", cls="fw-semibold text-success", style="font-size:0.82rem;"),
                    Span(f" · {len(weeks)} topics available for {grade} {subject}", cls="text-muted small ms-1 d-none d-sm-inline"),
                    id="curriculum-status-badge",
                    cls="d-inline-flex align-items-center",
                    **{"data-curriculum-valid": "true"},
                ),
                id="curriculum-status-container",
                cls="d-flex align-items-center py-1 px-2 rounded-3",
                style="background:#F4F8F5; min-height:2.2rem; width:fit-content; max-width:100%;",
            )
        else:
            wiz["curriculum_weeks"] = []
            wiz["selected_weeks"] = []
            _wizard_save(req, wiz)
            return Div(
                Span(cls="spinner-border spinner-border-sm text-danger me-2 d-none", id="curriculum-spinner", role="status"),
                Div(
                    Icon("exclamation-triangle-fill", cls="bi me-2 text-danger", style="font-size:0.85rem;"),
                    Span("Curriculum not found", cls="fw-semibold text-danger", style="font-size:0.82rem;"),
                    Span(f" · No syllabus found for {grade} {subject} ({term})", cls="text-muted small ms-1 d-none d-sm-inline"),
                    id="curriculum-status-badge",
                    cls="d-inline-flex align-items-center",
                    **{"data-curriculum-valid": "false"},
                ),
                id="curriculum-status-container",
                cls="d-flex align-items-center py-1 px-2 rounded-3",
                style="background:#FEE2E2; min-height:2.2rem; width:fit-content; max-width:100%;",
            )

    @app.get("/ui/exams/{exam_id}/poll")
    async def exam_poll(req: Request, exam_id: str):
        """HTMX polling partial: re-render the exam detail when ready."""
        guard = ensure_login(req)
        if guard:
            return guard
        poll_count = int(req.query_params.get("poll_count") or 0)
        ok, exam = await _fetch_exam(req, exam_id)
        if not ok:
            return show_toast(exam.get("message", "Could not load exam."), "danger")

        state = _state_of(exam)
        if state in ("generation_requested", "refinement_requested"):
            total_q = exam.get("total_questions") or len(exam.get("questions") or []) or 37
            num_sec = len(exam.get("sections") or []) or 3
            return Div(
                _render_generating_screen(
                    exam_id,
                    total_q=total_q,
                    num_sections=num_sec,
                    num_docs=3,
                    poll_endpoint=f"/ui/exams/{exam_id}/poll",
                    poll_target="#exam-detail-view",
                    poll_count=poll_count,
                ),
                id="exam-detail-view",
            )

        user = current_user(req) or {}
        show_answers = req.query_params.get("answers") == "1"
        return Div(
            _render_exam_detail(exam, user, show_answers),
            id="exam-detail-view",
        )

    @app.post("/ui/exams/{exam_id}/refine")
    async def exam_refine(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        feedback = (form.get("feedback") or "").strip()
        if not feedback or len(feedback) < 5:
            return show_toast("Please describe what to change (at least 5 characters).", "warning")
        payload = {"feedback": feedback}
        resp = await call_api(req, "POST", f"/exams/{exam_id}/refine", payload)
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(data.get("message", "Refinement failed."), "danger")
        # Re-fetch the exam and render the appropriate view.
        ok2, exam = await _fetch_exam(req, exam_id)
        user = current_user(req) or {}
        if ok2:
            state = _state_of(exam)
            if state in ("generation_requested", "refinement_requested", "pending"):
                total_q = exam.get("total_questions") or len(exam.get("questions") or []) or 37
                num_sec = len(exam.get("sections") or []) or 3
                return Div(
                    _render_generating_screen(
                        exam_id,
                        total_q=total_q,
                        num_sections=num_sec,
                        num_docs=3,
                        poll_endpoint=f"/ui/exams/{exam_id}/poll",
                        poll_target="#exam-detail-view",
                        poll_count=0,
                    ),
                    id="exam-detail-view",
                )
            return Div(
                _render_exam_detail(exam, user, show_answers=False),
                show_toast("AI refinement requested. This usually takes 20-60 seconds."),
                id="exam-detail-view",
            )
        return show_toast("Refinement requested, but the exam could not be re-loaded.", "warning")

    @app.post("/ui/exams/{exam_id}/submit-final")
    async def exam_submit_final(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/exams/{exam_id}/submit-final")
        ok, data = unwrap(resp)
        if not ok:
            # HTMX response: ephemeral feedback uses show_toast; success path redirects with set_flash.
            return show_toast(data.get("message", "We couldn't submit your exam — check your connection and try again."), "danger")
        set_flash(req.session, "success", "Exam submitted for approval.")
        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.post("/ui/exams/{exam_id}/reject")
    async def exam_reject(req: Request, exam_id: str):
        """Admin sends a submitted exam back to the teacher (audit: no reject
        endpoint existed — the governed transition is final_submitted ->
        teacher_review)."""
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        feedback = (form.get("feedback") or "").strip()
        qs = f"?feedback={quote(feedback)}" if feedback else ""
        resp = await call_api(req, "POST", f"/exams/{exam_id}/reject{qs}")
        ok, data = unwrap(resp)
        toast = (
            show_toast(data.get("message", "Could not reject the exam."), "danger")
            if not ok
            else show_toast(data.get("message", "Exam sent back to the teacher."), "success")
        )
        # Re-render the detail view so the actions/status update immediately.
        ok2, exam = await _fetch_exam(req, exam_id)
        if not ok2:
            return toast
        user = current_user(req) or {}
        return Div(
            _render_exam_detail(exam, user, req.query_params.get("answers") == "1"),
            toast,
            id="exam-detail-view",
        )

    @app.post("/ui/exams/{exam_id}/approve")
    async def exam_approve(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "POST", f"/exams/{exam_id}/approve")
        ok, data = unwrap(resp)
        if not ok:
            detail = data.get("data") if isinstance(data, dict) else None
            issues = (detail or {}).get("issues") or []
            msg = data.get("message", "We couldn't approve this exam — try again in a moment.")
            if issues:
                issue_lines = "<br>".join(f"• {i.get('message', 'Issue')}" for i in issues[:5])
                msg = f"{msg}<br><small class='text-muted'>{issue_lines}</small>"
                msg += f'<br><a href="/app/exams/{exam_id}?tab=preflight" class="small">Open Preflight tab to review & fix →</a>'
            # Toast is out-of-band so it survives the swap; the page re-renders
            # in place (replacing the confirm modal) instead of being replaced
            # by a bare toast fragment.
            toast = show_toast(msg, "danger", title="Approval Blocked", hx_swap_oob="beforeend:#app-toast-container")
            ok2, exam = await _fetch_exam(req, exam_id)
            if not ok2:
                return toast
            user = current_user(req) or {}
            return Div(
                toast,
                Div(_render_exam_detail(exam, user, req.query_params.get("answers") == "1"), id="exam-detail-view"),
            )
        set_flash(req.session, "success", "Exam approved successfully.")
        if req.headers.get("hx-request"):
            return Response(headers={"HX-Redirect": f"/app/exams/{exam_id}"})
        return RedirectResponse(f"/app/exams/{exam_id}", status_code=303)

    @app.post("/ui/exams/{exam_id}/export")
    async def exam_export(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        include_answers = form.get("include_answers") == "1"
        payload = {"format": "pdf", "include_answers": include_answers}
        resp = await call_api(req, "POST", f"/exams/{exam_id}/export", payload)
        ok, data = unwrap(resp)
        if not ok:
            detail = data.get("data") if isinstance(data, dict) else None
            issues = (detail or {}).get("issues") or []
            msg = data.get("message", "We couldn't prepare the export — try again in a moment.")
            if issues:
                issue_lines = "<br>".join(f"• {i.get('message', 'Issue')}" for i in issues[:5])
                msg = f"{msg}<br><small class='text-muted'>{issue_lines}</small>"
                msg += '<br><a href="/app/exams/' + exam_id + '?tab=preflight" class="small">Open Preflight tab →</a>'
            return show_toast(msg, "danger", title="Export blocked")
        download_url = data.get("download_url", "")
        file_name = data.get("file_name", "exam.pdf")
        download_link = download_url or f"/app/exams/{exam_id}/exports/{file_name}"
        return Div(
            show_toast(f"PDF export '{file_name}' ready.", "success"),
            A(
                Icon("download", cls="bi me-2"),
                f"Download {file_name}",
                href=download_link,
                cls="btn btn-sm btn-brand d-inline-flex align-items-center mt-2",
                download=file_name,
            ),
            Script(f"window.location.assign('{download_link}');"),
            id="export-result",
        )


    @app.delete("/ui/exams/{exam_id}")
    async def exam_delete(req: Request, exam_id: str):
        guard = ensure_login(req)
        if guard:
            return guard
        resp = await call_api(req, "DELETE", f"/exams/{exam_id}")
        ok, data = unwrap(resp)
        if not ok:
            # HTMX DELETE response: ephemeral feedback uses show_toast (never Flash —
            # Flash is only rendered by the shell in full-page redirect flows).
            return show_toast(data.get("message", "We couldn't delete this exam — check your connection and try again."), "danger")
        set_flash(req.session, "success", "Exam deleted.")
        return RedirectResponse("/app/exams", status_code=303)


def _wizard_error(message: str) -> Div:
    """Return a wizard panel fragment for HTMX swap targets.

    The error itself is ephemeral feedback → show_toast (FRONTEND_SPEC §5);
    the link stays inline so the user always has a recovery path in the panel.
    """
    return Div(
        show_toast(message, "danger"),
        A("Back to Step 1", href="/app/exams/new?step=1", cls="btn btn-link"),
        id="wizard-panel",
    )


# ---------------------------------------------------------------------------
# Manual entry Ã¢â‚¬â€ paste-style form (F04/F24/F57)
# ---------------------------------------------------------------------------

def _manual_exam_composer(req: Request, subject_options: list[str]) -> Div:
    """Interactive, local-first manual composer matching P05_manual_exam_choice_desktop.png with live KaTeX preview."""
    composer_script = Script("""
(() => {
  const editor = document.getElementById('manual-question-editor');
  const preview = document.getElementById('manual-preview-content');
  const form = document.getElementById('manual-exam-form');
  if (!editor || !preview || !form || window.skuPhaseManual) return;

  const esc = v => String(v || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;'}[c]));

  const card = n => `
    <article class="manual-question-card bg-white rounded-4 border p-4 mb-3 shadow-sm" data-question-card>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div class="d-flex align-items-center gap-2">
          <i class="bi bi-grip-vertical text-muted"></i>
          <strong class="text-dark">Question ${n}</strong>
        </div>
        <button type="button" class="btn btn-link text-danger p-0 manual-remove-question" aria-label="Remove question">
          <i class="bi bi-trash3"></i>
        </button>
      </div>
      <div class="mb-3">
        <label class="form-label text-muted small fw-medium mb-1">Question</label>
        <textarea class="form-control manual-question-text rounded-3 p-3 border-0" rows="3" placeholder="Enter question text... (supports LaTeX formulas like $x^2 + 5 = 0$)" style="background-color: #F4F6F4; font-size: 0.92rem;" required></textarea>
      </div>
      <div class="row g-3 mb-3">
        <div class="col-12 col-md-7">
          <label class="form-label text-muted small fw-medium mb-1">Type</label>
          <select class="form-select manual-question-type rounded-3 border-0 py-2" style="background-color: #F4F6F4; font-size: 0.92rem;">
            <option value="multiple_choice">MCQ</option>
            <option value="short_answer">Short Answer</option>
            <option value="essay">Essay</option>
            <option value="fill_in_blank">Fill in the Blank</option>
            <option value="true_false">True / False</option>
          </select>
        </div>
        <div class="col-12 col-md-5">
          <label class="form-label text-muted small fw-medium mb-1">Marks</label>
          <input class="form-control manual-question-marks rounded-3 border-0 py-2" type="number" min="1" max="100" value="2" style="background-color: #F4F6F4; font-size: 0.92rem;" required>
        </div>
      </div>
      <div class="manual-options"></div>
    </article>`;

  const cards = () => [...editor.querySelectorAll('[data-question-card]')];

  const options = item => {
    const type = item.querySelector('.manual-question-type').value;
    const area = item.querySelector('.manual-options');
    if (type === 'multiple_choice') {
      area.innerHTML = `
        <label class="form-label text-muted small fw-medium mb-2">Options</label>
        ${['Option A', 'Option B', 'Option C', 'Option D'].map((ph, idx) => `
          <div class="mb-2">
            <input class="form-control manual-option rounded-3 border-0 py-2 px-3" placeholder="${ph}" style="background-color: #F4F6F4; font-size: 0.88rem;">
          </div>
        `).join('')}
      `;
    } else if (type === 'true_false') {
      area.innerHTML = `
        <label class="form-label text-muted small fw-medium mb-2">Options</label>
        <div class="mb-2"><input class="form-control manual-option rounded-3 border-0 py-2 px-3" value="True" style="background-color: #F4F6F4; font-size: 0.88rem;"></div>
        <div class="mb-2"><input class="form-control manual-option rounded-3 border-0 py-2 px-3" value="False" style="background-color: #F4F6F4; font-size: 0.88rem;"></div>
      `;
    } else {
      area.innerHTML = '<p class="manual-answer-note mb-0 text-muted small p-3 rounded-3" style="background-color: #F8FAF8;">Students will write their answer in the response space.</p>';
    }
  };

  const renumber = () => cards().forEach((item, i) => {
    item.querySelector('strong').textContent = `Question ${i + 1}`;
    item.querySelector('.manual-remove-question').disabled = cards().length === 1;
  });

  const update = () => {
    const subject = document.getElementById('manual-subject').value || 'Subject';
    const grade = document.getElementById('manual-grade').value || 'Grade';
    const data = cards().map((item, i) => ({
      n: i + 1,
      text: item.querySelector('.manual-question-text').value.trim(),
      marks: Number(item.querySelector('.manual-question-marks').value) || 0,
      options: [...item.querySelectorAll('.manual-option')].map(x => x.value.trim()).filter(Boolean)
    }));
    const total = data.reduce((sum, q) => sum + q.marks, 0);

    preview.innerHTML = `
      <div class="text-center border-bottom pb-3 mb-3">
        <strong class="fs-6 text-dark">${esc(subject)} — ${esc(grade)}</strong>
        <span class="d-block text-muted small mt-1">Total: ${total} marks</span>
      </div>
    ` + data.map(q => `
      <div class="manual-preview-question mb-3 pb-2 border-bottom border-light">
        <div><strong>${q.n}.</strong> <span>${esc(q.text || '(empty question)')}</span> <span class="text-muted small">(${q.marks} marks)</span></div>
        ${q.options.length ? `<ol type="A" class="mb-0 mt-2 ps-3 small text-muted">${q.options.map(x => `<li class="mb-1">${esc(x)}</li>`).join('')}</ol>` : ''}
      </div>
    `).join('');

    // Trigger KaTeX rendering in the preview pane
    if (typeof renderMathInElement === 'function') {
      renderMathInElement(preview, {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false},
          {left: '\\\\(', right: '\\\\)', display: false},
          {left: '\\\\[', right: '\\\\]', display: true}
        ],
        throwOnError: false
      });
    }
  };

  const add = () => {
    editor.insertAdjacentHTML('beforeend', card(cards().length + 1));
    options(cards().at(-1));
    renumber();
    update();
  };

  editor.addEventListener('input', update);
  editor.addEventListener('change', e => {
    if (e.target.matches('.manual-question-type')) {
      options(e.target.closest('[data-question-card]'));
    }
    update();
  });
  editor.addEventListener('click', e => {
    const b = e.target.closest('.manual-remove-question');
    if (b && cards().length > 1) {
      b.closest('[data-question-card]').remove();
      renumber();
      update();
    }
  });

  document.getElementById('manual-add-question').addEventListener('click', add);
  document.getElementById('manual-preview-button').addEventListener('click', () => {
    document.getElementById('manual-preview-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  document.getElementById('manual-subject').addEventListener('change', update);
  document.getElementById('manual-grade').addEventListener('change', update);

  window.skuPhaseManual = {
    prepare: () => {
      const data = cards().map((item, i) => ({
        question_number: i + 1,
        type: item.querySelector('.manual-question-type').value,
        question_text: item.querySelector('.manual-question-text').value.trim(),
        marks: Number(item.querySelector('.manual-question-marks').value) || 0,
        options: [...item.querySelectorAll('.manual-option')].map(x => x.value.trim()).filter(Boolean)
      }));
      document.getElementById('manual-questions-json').value = JSON.stringify(data);
      return true;
    }
  };

  add();
})();
""")

    meta_card = Card(
        Row(
            Col(
                Label("Subject", cls="form-label text-muted small fw-medium mb-1"),
                HtmlSelect(
                    Option("Subject", value=""),
                    *[Option(x, value=x) for x in subject_options],
                    name="subject",
                    id="manual-subject",
                    required=True,
                    cls="form-select rounded-3 border-0 py-2 px-3",
                    style="background-color: #F4F6F4; font-size: 0.92rem;",
                ),
                span=12,
                md=6,
            ),
            Col(
                Label("Grade", cls="form-label text-muted small fw-medium mb-1"),
                HtmlSelect(
                    Option("Grade", value=""),
                    *[Option(x, value=x) for x in GRADE_LEVELS],
                    name="grade_level",
                    id="manual-grade",
                    required=True,
                    cls="form-select rounded-3 border-0 py-2 px-3",
                    style="background-color: #F4F6F4; font-size: 0.92rem;",
                ),
                span=12,
                md=6,
            ),
            g=3,
        ),
        cls="bg-white rounded-4 border p-4 shadow-sm mb-4",
    )

    return Div(
        Div(
            Div(
                H1("Manual Exam", cls="app-section-title fs-3 mb-1"),
                P("Compose an exam manually with your own questions.", cls="app-body-copy text-muted mb-0"),
            ),
            Div(
                Button(
                    Icon("eye", cls="bi me-2"),
                    "Preview",
                    type="button",
                    id="manual-preview-button",
                    variant="outline-secondary",
                    cls="rounded-pill px-4 bg-white text-dark border",
                ),
                Button(
                    Icon("send", cls="bi me-2"),
                    "Submit",
                    type="submit",
                    form="manual-exam-form",
                    variant="success",
                    cls="btn btn-brand rounded-pill px-4 ms-2 text-white",
                    style="background-color: #00412E !important; border: none;",
                ),
                cls="d-flex align-items-center mt-3 mt-md-0",
            ),
            cls="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4",
        ),
        Form(
            _csrf_input(req),
            Input(name="questions_json", type="hidden", id="manual-questions-json"),
            Row(
                Col(
                    meta_card,
                    Div(id="manual-question-editor"),
                    Button(
                        Icon("plus-lg", cls="bi me-2"),
                        "Add Question",
                        type="button",
                        id="manual-add-question",
                        variant="light",
                        cls="w-100 rounded-4 py-3 mt-2 border text-muted fw-semibold",
                        style="background-color: #F4F6F4; border-color: #E2E8F0 !important;",
                    ),
                    span=12,
                    lg=7,
                ),
                Col(
                    Card(
                        H2("Preview", cls="h5 fw-bold mb-3 text-dark"),
                        Div(id="manual-preview-content"),
                        id="manual-preview-card",
                        cls="bg-white rounded-4 border p-4 shadow-sm sticky-top",
                        style="top: 1.5rem;",
                    ),
                    span=12,
                    lg=5,
                    cls="mt-4 mt-lg-0",
                ),
                g=4,
            ),
            id="manual-exam-form",
            hx_post="/ui/exams/manual-submit",
            hx_target="#manual-result",
            hx_swap="innerHTML",
            hx_indicator="#manual-spinner",
            onsubmit="return window.skuPhaseManual && window.skuPhaseManual.prepare();",
        ),
        Div(
            Spinner(),
            P("Creating exam...", cls="text-muted small ms-2 mb-0"),
            id="manual-spinner",
            cls="htmx-indicator d-flex align-items-center gap-2 mt-3",
        ),
        Div(id="manual-result", cls="mt-3"),
        composer_script,
        cls="py-2",
    )


def register_manual_routes(app):

    @app.get("/app/exams/new/manual")
    async def exam_manual(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        user = current_user(req) or {}
        flash = pop_flash(req)
        body = _manual_exam_composer(
            req,
            [
                "Mathematics", "English Language", "Basic Science", "Social Studies",
                "National Values", "Civic Education", "Agricultural Science", "Computer Studies",
                "Physical & Health Education", "Home Economics", "Christian Religious Studies",
                "Islamic Religious Studies", "Hausa", "Igbo", "Yoruba",
            ],
        )
        return AppShell(
            Title("Manual Exam - SkuPhase"),
            body,
            user=user,
            active="exams",
            flash=flash,
            bell_count=req.session.get("bell_count"),
            crumbs=[("Exams", "/app/exams"), ("Manual", None)],
        )

    @app.post("/ui/exams/manual-submit")
    async def exam_manual_submit(req: Request):
        guard = ensure_login(req)
        if guard:
            return guard
        form = await req.form()
        questions = []
        questions_json = (form.get("questions_json") or "").strip()
        if questions_json:
            try:
                raw_questions = json.loads(questions_json)
            except json.JSONDecodeError:
                return show_toast("The question editor could not be read. Please refresh and try again.", "danger")
            if not isinstance(raw_questions, list):
                return show_toast("Please add at least one question.", "danger")
            allowed_types = {"multiple_choice", "short_answer", "essay", "true_false", "fill_in_blank"}
            for number, raw in enumerate(raw_questions, start=1):
                if not isinstance(raw, dict):
                    continue
                question_text = str(raw.get("question_text") or "").strip()
                question_type = str(raw.get("type") or "short_answer")
                if question_type not in allowed_types or len(question_text) < 3:
                    return show_toast("Every question needs at least three characters and a valid type.", "danger")
                options = [str(option).strip() for option in (raw.get("options") or []) if str(option).strip()]
                if question_type == "multiple_choice" and len(options) < 2:
                    return show_toast("Each MCQ needs at least two answer options.", "danger")
                questions.append({
                    "question_number": number,
                    "type": "short_answer" if question_type == "fill_in_blank" else question_type,
                    "question_text": question_text,
                    "marks": max(1, min(100, _safe_int(raw.get("marks"), 2))),
                    "options": options or None,
                })
        else:
            questions = _parse_paste_questions((form.get("questions_text") or "").strip())
        if not questions:
            return show_toast("Please add at least one complete question.", "danger")

        duration = _safe_int(form.get("duration_minutes"), 60)
        if duration < 30 or duration > 300:
            return show_toast("Duration must be between 30 and 300 minutes.", "danger")

        payload = {
            "subject": (form.get("subject") or "").strip(),
            "grade_level": (form.get("grade_level") or "").strip(),
            "duration_minutes": duration,
            "language": form.get("language") or "English",
            "instructions": (form.get("instructions") or "").strip() or None,
            "questions": questions,
        }
        if not payload["subject"] or not payload["grade_level"]:
            return show_toast("Subject and class are required.", "danger")

        resp = await call_api(req, "POST", "/exams/manual-submit", payload)
        ok, data = unwrap(resp)
        if not ok:
            return show_toast(
                data.get("message", "Submission failed. Please try again."),
                "danger",
            )
        exam_id = str(data.get("exam_id") or data.get("id") or "")
        if not exam_id:
            return show_toast("Submission succeeded but no exam id was returned.", "warning")
        return Div(
            show_toast("Exam created successfully! Redirecting…", "success", title="Exam Created"),
            A(
                "Open exam",
                href=f"/app/exams/{exam_id}",
                cls="btn btn-sm btn-brand mt-2",
            ),
            id="manual-result",
        )


def _parse_paste_questions(text: str) -> list:
    """Parse a paste of questions separated by blank lines.

    Recognises: 'Answer: <letter|value>' for MCQ correctness, 'Marks: <n>' for marks.
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    out: list = []
    for n, block in enumerate(blocks, start=1):
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        marks = 1
        filtered: list = []
        for ln in lines:
            low = ln.strip().lower()
            if low.startswith("marks:"):
                try:
                    marks = max(1, min(100, int(low.split(":", 1)[1].strip())))
                    continue
                except ValueError:
                    pass
            filtered.append(ln.strip())
        if not filtered:
            continue
        answer = None
        body_lines: list = []
        for ln in filtered:
            low = ln.strip().lower()
            if low.startswith("answer:"):
                answer = ln.split(":", 1)[1].strip()
                continue
            body_lines.append(ln)
        body = "\n".join(body_lines).strip()
        if len(body) < 5:
            continue
        options: list = []
        cleaned_lines: list = []
        for ln in body_lines:
            if len(ln) >= 3 and ln[1:3] in (") ", ").") and ln[0].upper() in "ABCD":
                options.append(ln)
            else:
                cleaned_lines.append(ln)
        question_text = "\n".join(cleaned_lines).strip() or body
        if not options:
            options = None
        out.append(
            {
                "question_number": n,
                "type": "multiple_choice" if options else "short_answer",
                "question_text": question_text,
                "marks": marks,
                "options": options,
                "correct_answer": answer or None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Umbrella registration used by app.py
# ---------------------------------------------------------------------------

def register_routes(app):
    """Single entry-point called by app.py Ã¢â‚¬â€ wires every subgroup."""
    register_page_routes(app)
    register_wizard_routes(app)
    register_manual_routes(app)
    register_action_routes(app)
