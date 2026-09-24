"""Export service for exam documents (ReportLab platypus, word-wrapped)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

from app.models.exam import Exam, Question
from app.utils.exam_utils import format_mcq_option



def _font_registered(name: str) -> bool:
    """Return True if *name* is already registered with ReportLab's pdfmetrics."""
    try:
        from reportlab.pdfbase import pdfmetrics as _pm
        return name in _pm.getRegisteredFontNames()
    except Exception:
        return False


def _svg_to_flowable(svg_code: str, max_width_pt: float = 380.0, max_height_pt: float = 140.0):
    """Convert raw SVG string to a ReportLab Drawing flowable, scaled to fit margins."""
    if not svg_code or not isinstance(svg_code, str):
        return None
    cleaned_svg = svg_code.strip()
    if not cleaned_svg.startswith("<svg") and "<svg" in cleaned_svg:
        start = cleaned_svg.find("<svg")
        end = cleaned_svg.rfind("</svg>")
        if start != -1 and end != -1:
            cleaned_svg = cleaned_svg[start : end + 6]
    if not cleaned_svg.startswith("<svg"):
        return None

    try:
        import io
        from svglib.svglib import svg2rlg
        drawing = svg2rlg(io.StringIO(cleaned_svg))
        if drawing is None:
            return None
        orig_w = float(getattr(drawing, "width", 0) or 0)
        orig_h = float(getattr(drawing, "height", 0) or 0)
        if orig_w <= 0 or orig_h <= 0:
            return drawing

        scale = 1.0
        if orig_w > max_width_pt:
            scale = min(scale, max_width_pt / orig_w)
        if orig_h > max_height_pt:
            scale = min(scale, max_height_pt / orig_h)

        if scale < 0.999:
            drawing.scale(scale, scale)
            drawing.width = orig_w * scale
            drawing.height = orig_h * scale

        drawing.hAlign = "CENTER"
        return drawing
    except Exception:
        return None


class ExportService:
    """Generate export files for exams (PDF MVP).

    Files live under ``exports/{school_id}/{exam_id}/`` on local disk.
    Downloads go through the tenant-checked router endpoint; the absolute
    server path is never exposed to clients.
    """

    EXPORT_DIR = Path("exports")

    @classmethod
    def exam_dir(cls, exam_id: Any) -> Path:
        return cls.EXPORT_DIR / "exams" / str(exam_id)

    @classmethod
    def export_path(cls, exam_id: Any, file_name: str) -> Path:
        """Resolve an export file path (caller must validate file_name)."""
        if not re.fullmatch(r"[0-9a-f]{32}\.pdf", file_name or ""):
            raise ValueError("Invalid export file name")
        return cls.exam_dir(exam_id) / file_name

    @classmethod
    def list_exports(cls, exam_id: Any) -> List[str]:
        directory = cls.exam_dir(exam_id)
        if not directory.is_dir():
            return []
        return sorted(p.name for p in directory.glob("*.pdf"))

    @staticmethod
    def _clean(text: str | None) -> str:
        """Normalise text for ReportLab PDF rendering.

        Converts common LaTeX / markdown notation to plain text or ReportLab
        Paragraph XML tags (<super>, <sub>, <b>, <i>).  Strips code fences and
        math delimiters that would appear as raw characters in the PDF.
        """
        if not text:
            return ""
        cleaned = str(text)

        # ── Code fences ────────────────────────────────────────────────────────
        cleaned = re.sub(
            r"```mermaid\s*(.*?)\s*```",
            lambda m: f"[Diagram: {m.group(1).splitlines()[0] if m.group(1).splitlines() else 'see question'}]",
            cleaned,
            flags=re.DOTALL,
        )
        cleaned = re.sub(r"```[a-zA-Z]*\n?", "", cleaned)
        cleaned = cleaned.replace("```", "")

        # ── LaTeX: fractions ───────────────────────────────────────────────────
        cleaned = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", lambda m: f"({m.group(1)}/{m.group(2)})", cleaned)

        # ── LaTeX: other common commands ────────────────────────────────────────
        cleaned = re.sub(r"\\ce\{([^}]+)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\sqrt\{([^}]+)\}", r"√(\1)", cleaned)
        cleaned = re.sub(r"\\text\{([^}]+)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\mathrm\{([^}]+)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\mathbf\{([^}]+)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\left[\(\[\{]", "(", cleaned)
        cleaned = re.sub(r"\\right[\)\]\}]", ")", cleaned)

        # ── LaTeX: superscripts / subscripts → ReportLab XML ───────────────────
        cleaned = re.sub(r"\^\{([^}]+)\}", r"<super>\1</super>", cleaned)
        cleaned = re.sub(r"\^([0-9A-Za-z])", r"<super>\1</super>", cleaned)
        cleaned = re.sub(r"_\{([^}]+)\}", r"<sub>\1</sub>", cleaned)
        cleaned = re.sub(r"_([0-9A-Za-z])", r"<sub>\1</sub>", cleaned)

        # ── LaTeX: Greek letters & math symbols ────────────────────────────────
        _greek = {
            r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
            r"\epsilon": "ε", r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ",
            r"\iota": "ι", r"\kappa": "κ", r"\lambda": "λ", r"\mu": "μ",
            r"\nu": "ν", r"\xi": "ξ", r"\pi": "π", r"\rho": "ρ",
            r"\sigma": "σ", r"\tau": "τ", r"\upsilon": "υ", r"\phi": "φ",
            r"\chi": "χ", r"\psi": "ψ", r"\omega": "ω",
            r"\Alpha": "Α", r"\Beta": "Β", r"\Gamma": "Γ", r"\Delta": "Δ",
            r"\Theta": "Θ", r"\Lambda": "Λ", r"\Pi": "Π", r"\Sigma": "Σ",
            r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
            r"\times": "×", r"\div": "÷", r"\pm": "±", r"\mp": "∓",
            r"\cdot": "·", r"\cdots": "···", r"\ldots": "…",
            r"\le": "≤", r"\leq": "≤", r"\ge": "≥", r"\geq": "≥",
            r"\neq": "≠", r"\approx": "≈", r"\equiv": "≡", r"\sim": "∼",
            r"\infty": "∞", r"\partial": "∂", r"\nabla": "∇",
            r"\forall": "∀", r"\exists": "∃",
            r"\in": "∈", r"\notin": "∉", r"\subset": "⊂", r"\cup": "∪",
            r"\cap": "∩", r"\emptyset": "∅",
            r"\rightarrow": "→", r"\leftarrow": "←", r"\Rightarrow": "⇒",
            r"\Leftrightarrow": "⟺",
            r"\degree": "°", r"\circ": "°",
        }
        for latex, sym in _greek.items():
            cleaned = cleaned.replace(latex, sym)

        # ── Markdown: bold / italic → ReportLab XML ────────────────────────────
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", cleaned)
        cleaned = re.sub(r"__(.+?)__", r"<b>\1</b>", cleaned)
        cleaned = re.sub(r"\*(.+?)\*", r"<i>\1</i>", cleaned)

        # ── Math delimiters: strip $$ / $ wrappers (content already converted) ─
        cleaned = re.sub(r"(?<!\\)\$\$([^$]*)\$\$", r"\1", cleaned)
        cleaned = re.sub(r"(?<!\\)\$([^$\n]*)\$", r"\1", cleaned)
        cleaned = re.sub(r"(?<!\\)\$", "", cleaned)

        # ── Strip leftover \command{...} and bare \command ─────────────────────
        cleaned = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", cleaned)
        cleaned = re.sub(r"\\[a-zA-Z]+\b", "", cleaned)

        return cleaned.replace("\u0000", "").strip()

    @classmethod
    def export_exam_pdf(
        cls,
        exam: Exam,
        questions: List[Question],
        include_answers: bool = False,
        passages: list | None = None,
        school_name: str | None = None,
        school_address: str | None = None,
        school_logo_path: str | None = None,
    ) -> str:
        """
        Export exam to a fully word-wrapped PDF and return the file NAME.
        Download via GET /api/v1/exams/{exam_id}/exports/{file_name}.

        ``passages`` (optional) is a list of ExamPassage-like objects used for
        comprehension sections; each passage renders once, above the first
        question that references it.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
                Image as ReportLabImage,
            )
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except Exception as e:  # pragma: no cover - env without reportlab
            raise ValueError(f"PDF export dependencies are not available: {e}") from e

        # ── Font registration (Arial for full Unicode coverage: ₦, π, α …) ─────
        import os as _os
        _arial_path = r"C:\Windows\Fonts\arial.ttf"
        _arial_bd_path = r"C:\Windows\Fonts\arialbd.ttf"
        _arial_it_path = r"C:\Windows\Fonts\ariali.ttf"
        if _os.path.exists(_arial_path) and not _font_registered("ExamArial"):
            try:
                pdfmetrics.registerFont(TTFont("ExamArial", _arial_path))
                if _os.path.exists(_arial_bd_path):
                    pdfmetrics.registerFont(TTFont("ExamArial-Bold", _arial_bd_path))
                if _os.path.exists(_arial_it_path):
                    pdfmetrics.registerFont(TTFont("ExamArial-Italic", _arial_it_path))
                from reportlab.pdfbase.pdfmetrics import registerFontFamily
                registerFontFamily(
                    "ExamArial",
                    normal="ExamArial",
                    bold="ExamArial-Bold" if _os.path.exists(_arial_bd_path) else "ExamArial",
                    italic="ExamArial-Italic" if _os.path.exists(_arial_it_path) else "ExamArial",
                )
                _base_font = "ExamArial"
                _bold_font = "ExamArial-Bold" if _os.path.exists(_arial_bd_path) else "ExamArial"
            except Exception:
                _base_font = "Helvetica"
                _bold_font = "Helvetica-Bold"
        else:
            _base_font = "ExamArial" if _os.path.exists(_arial_path) else "Helvetica"
            _bold_font = "ExamArial-Bold" if _os.path.exists(_arial_bd_path) else "Helvetica-Bold"

        directory = cls.exam_dir(exam.id)
        directory.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}.pdf"
        output_path = directory / file_name

        styles = getSampleStyleSheet()
        school_name_style = ParagraphStyle(
            "SchoolName", parent=styles["Title"], fontName=_bold_font,
            fontSize=14, leading=17, alignment=1, spaceAfter=0.5 * mm,
        )
        school_addr_style = ParagraphStyle(
            "SchoolAddr", parent=styles["Normal"], fontName=_base_font,
            fontSize=8.5, leading=11, alignment=1, textColor="#555555", spaceAfter=1 * mm,
        )
        title_style = ParagraphStyle(
            "ExamTitle", parent=styles["Normal"], fontName=_bold_font,
            fontSize=11, leading=14, alignment=1, spaceAfter=1.5 * mm,
        )
        meta_style = ParagraphStyle(
            "ExamMeta", parent=styles["Normal"], fontName=_base_font,
            fontSize=9, leading=12, alignment=1, spaceAfter=1 * mm,
        )
        instruction_style = ParagraphStyle(
            "ExamInstructions", parent=styles["Normal"], fontName=_base_font,
            fontSize=8.5, leading=11, spaceAfter=0.5 * mm,
        )
        section_style = ParagraphStyle(
            "SectionHeader", parent=styles["Normal"], fontName=_bold_font,
            fontSize=10.5, leading=13, spaceBefore=3 * mm, spaceAfter=1.5 * mm,
            borderPad=2, borderWidth=0,
        )
        question_style = ParagraphStyle(
            "QuestionText", parent=styles["Normal"], fontName=_base_font,
            fontSize=10, leading=13.5, spaceBefore=2 * mm, spaceAfter=0.5 * mm,
        )
        option_style = ParagraphStyle(
            "OptionText", parent=styles["Normal"], fontName=_base_font,
            fontSize=9.5, leading=12.5, leftIndent=14, spaceAfter=0,
        )
        answer_style = ParagraphStyle(
            "AnswerText", parent=styles["Normal"], fontName=_base_font,
            fontSize=9, leading=11.5, leftIndent=14, textColor="#333333",
        )

        from xml.sax.saxutils import escape as _xml_escape

        def esc(raw: str) -> str:
            """XML-escape then convert LaTeX/markdown → ReportLab XML tags."""
            # Escape &, <, > so they become &amp;, &lt;, &gt; BEFORE _clean()
            # processes the rest of the text into ReportLab tags.
            safe = _xml_escape(str(raw) if raw else "")
            cleaned = cls._clean(safe)
            return cleaned.replace("\n", "<br/>")

        story: list = []

        header = []
        if school_name:
            header.append(Paragraph(f"<b>{esc(school_name.upper())}</b>", school_name_style))
        if school_address:
            header.append(Paragraph(f"{esc(school_address)}", school_addr_style))

        header.append(Paragraph(f"<b>{esc(exam.subject).upper()} EXAMINATION — {esc(exam.grade_level).upper()}</b>", title_style))
        header.append(
            Paragraph(
                f"<b>Duration:</b> {exam.duration_minutes or '-'} minutes &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Total Marks:</b> {exam.total_marks}",
                meta_style,
            )
        )

        if include_answers:
            answer_key_style = ParagraphStyle(
                "AnswerKeyMasthead",
                parent=styles["Heading2"],
                fontSize=10,
                leading=13,
                alignment=1,
                textColor="#b02a37",
                spaceAfter=1 * mm,
            )
            header.append(Paragraph("<b>MARKING SCHEME / ANSWER KEY</b>", answer_key_style))

        if exam.instructions:
            header.append(Spacer(1, 1.5 * mm))
            header.append(Paragraph("<b>INSTRUCTIONS:</b>", instruction_style))
            for line in cls._clean(exam.instructions).splitlines():
                if line.strip():
                    header.append(Paragraph(esc(line), instruction_style))

        # Check for school logo
        logo_flowable = None
        if school_logo_path:
            try:
                lpath = Path(school_logo_path)
                if not lpath.is_file() and str(school_logo_path).startswith("/"):
                    candidate = Path(str(school_logo_path).lstrip("/"))
                    if candidate.is_file():
                        lpath = candidate
                    elif (Path("app") / candidate).is_file():
                        lpath = Path("app") / candidate
                if lpath.is_file():
                    logo_flowable = ReportLabImage(str(lpath), width=22 * mm, height=22 * mm)
            except Exception:
                logo_flowable = None

        if logo_flowable:
            header_table = Table([[logo_flowable, header]], colWidths=[26 * mm, None])
            header_table.setStyle(
                TableStyle([
                    ("BOX", (0, 0), (-1, -1), 1, "#222222"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ])
            )
        else:
            header_table = Table([[header]], colWidths=[None])
            header_table.setStyle(
                TableStyle([
                    ("BOX", (0, 0), (-1, -1), 1, "#222222"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ])
            )
        story.append(header_table)
        story.append(Spacer(1, 2 * mm))

        # ── Helper: infer section title from question type ─────────────────────
        def _sec_title(q: Any) -> str:
            t = getattr(q, "section_title", None)
            if t:
                return t
            qtype = getattr(q, "type", "multiple_choice")
            if qtype == "multiple_choice":
                return "SECTION A — OBJECTIVE QUESTIONS"
            if qtype in ("short_answer", "theory"):
                return "SECTION B — SHORT ANSWER / THEORY"
            if qtype == "essay":
                return "SECTION C — ESSAY QUESTIONS"
            return "SECTION A"

        # Pre-compute total marks per section
        section_marks: dict[str, int] = {}
        for q in questions:
            st = _sec_title(q)
            section_marks[st] = section_marks.get(st, 0) + (getattr(q, "marks", 0) or 0)

        # ── Question loop ──────────────────────────────────────────────────────
        current_section: str | None = None
        section_q_counter: dict[str, int] = {}   # per-section numbering
        rendered_passage_ids: set = set()

        # Build passage lookup
        passage_meta: dict = {}
        for p in (passages or []):
            pid = getattr(p, "id", None)
            if pid is None:
                continue
            passage_meta[str(pid)] = (
                getattr(p, "title", None) or "",
                getattr(p, "body", "") or "",
                getattr(p, "section_number", None) or "",
            )

        for q in questions:
            sec_title = _sec_title(q)

            # ── Section header (only when section changes) ─────────────────────
            if sec_title != current_section:
                current_section = sec_title
                tot_m = section_marks.get(sec_title, 0)
                marks_suffix = f" ({tot_m} MARKS)" if tot_m > 0 else ""
                story.append(
                    Paragraph(f"<b>{esc(sec_title.upper())}{marks_suffix}</b>", section_style)
                )
                story.append(Spacer(1, 1 * mm))

            # ── Per-section question numbering ────────────────────────────────
            section_q_counter[sec_title] = section_q_counter.get(sec_title, 0) + 1
            q_num = section_q_counter[sec_title]

            # ── Render passage (first time seen for this passage) ─────────────
            pid = str(getattr(q, "passage_id", "") or "")
            if pid in passage_meta and pid not in rendered_passage_ids:
                rendered_passage_ids.add(pid)
                p_title, p_body, p_section = passage_meta[pid]
                sec_lbl = f"Section {p_section}: " if p_section else ""
                story.append(
                    Paragraph(
                        f"<b>{esc(sec_lbl)}Read the passage and answer the questions that follow.</b>",
                        question_style,
                    )
                )
                if p_title:
                    story.append(Paragraph(f"<b>{esc(p_title)}</b>", question_style))
                for para in p_body.splitlines():
                    if para.strip():
                        story.append(Paragraph(esc(para), question_style))
                story.append(Spacer(1, 2 * mm))

            # ── Question text ─────────────────────────────────────────────────
            marks_bit = f"&nbsp;&nbsp;<b>[{q.marks}m]</b>" if q.marks else ""
            story.append(
                Paragraph(f"<b>{q_num}.</b>&nbsp;{esc(q.question_text)}{marks_bit}", question_style)
            )

            # ── Diagram SVG (if question has a visual diagram) ─────────────────
            diag_svg = getattr(q, "diagram_svg", None)
            if diag_svg:
                diag_drawing = _svg_to_flowable(diag_svg, max_width_pt=A4[0] - 28 * mm, max_height_pt=140)
                if diag_drawing is not None:
                    story.append(Spacer(1, 1.5 * mm))
                    story.append(diag_drawing)
                    story.append(Spacer(1, 1.5 * mm))

            # ── MCQ Options ────────────────────────────────────────────────────
            if q.options:
                raw_opts = [format_mcq_option(str(opt), idx) for idx, opt in enumerate(q.options)]
                # Use 2-column layout only if ALL options are short (<= 55 chars each)
                _all_short = all(len(o) <= 55 for o in raw_opts)
                if len(raw_opts) == 4 and _all_short:
                    # Compact 2×2 table — A/B on row 1, C/D on row 2
                    fmt_opts = [Paragraph(esc(o), option_style) for o in raw_opts]
                    usable_w = A4[0] - 28 * mm   # page width minus margins
                    col_w = usable_w / 2
                    opt_table = Table(
                        [[fmt_opts[0], fmt_opts[1]], [fmt_opts[2], fmt_opts[3]]],
                        colWidths=[col_w, col_w],
                    )
                    opt_table.setStyle(
                        TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ])
                    )
                    story.append(opt_table)
                else:
                    # Single-column stacking for long options or non-4-option sets
                    for o in raw_opts:
                        story.append(Paragraph(esc(o), option_style))

            # ── Answer key (when include_answers) ─────────────────────────────
            if include_answers:
                if q.correct_answer:
                    story.append(Paragraph(f"<b>Answer:</b> {esc(q.correct_answer)}", answer_style))
                if q.marking_scheme:
                    story.append(Paragraph("<b>Marking scheme:</b>", answer_style))
                    for point in q.marking_scheme:
                        story.append(Paragraph(f"• {esc(str(point))}", answer_style))
                if q.explanation:
                    story.append(Paragraph(f"<i>{esc(q.explanation)}</i>", answer_style))

        if include_answers:
            story.append(Spacer(1, 5 * mm))
            footer_style = ParagraphStyle(
                "TeacherOnlyFooter", parent=styles["Normal"], fontName=_base_font,
                fontSize=8, leading=10, alignment=1, textColor="#777777",
            )
            story.append(Paragraph("<b>FOR TEACHER USE ONLY — NOT FOR DISTRIBUTION</b>", footer_style))

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=f"{exam.subject} {exam.grade_level}",
        )

        def _footer(canvas, _doc):
            canvas.saveState()
            canvas.setFont(_base_font, 8)
            canvas.drawCentredString(
                A4[0] / 2, 8 * mm, f"Page {_doc.page}"
            )
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return file_name


    @classmethod
    def export_marking_guide_pdf(
        cls,
        exam: Exam,
        questions: List[Question],
        school_name: str | None = None,
        school_address: str | None = None,
    ) -> str:
        """Export a compact 1-page Teacher Answer Key & Marking Guide."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape

        def esc(text: str) -> str:
            return escape(cls._clean(text)).replace("\n", "<br/>")

        directory = cls.exam_dir(exam.id)
        directory.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}.pdf"
        output_path = directory / file_name

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("MGTitle", parent=styles["Heading1"], fontSize=13, leading=16, alignment=1)
        sub_style = ParagraphStyle("MGSub", parent=styles["Normal"], fontSize=9, leading=12, alignment=1, textColor="#b02a37")
        body_style = ParagraphStyle("MGBody", parent=styles["Normal"], fontSize=8.5, leading=11)
        th_style = ParagraphStyle("MGTh", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold", alignment=1)
        tc_style = ParagraphStyle("MGTc", parent=styles["Normal"], fontSize=9, leading=11, fontName="Helvetica-Bold", alignment=1)

        story = []
        if school_name:
            story.append(Paragraph(f"<b>{esc(school_name.upper())}</b>", title_style))
        story.append(Paragraph(f"<b>{esc(exam.subject).upper()} ({esc(exam.grade_level).upper()}) — MARKING GUIDE</b>", title_style))
        story.append(Paragraph("CONFIDENTIAL — FOR EXAMINER & SUPERVISOR USE ONLY", sub_style))
        story.append(Spacer(1, 4 * mm))

        # Separate MCQs and Theory questions
        mcqs = [q for q in questions if getattr(q, "type", "") == "multiple_choice"]
        theory = [q for q in questions if getattr(q, "type", "") != "multiple_choice"]

        if mcqs:
            story.append(Paragraph("<b>SECTION A: OBJECTIVE ANSWER KEY</b>", body_style))
            story.append(Spacer(1, 2 * mm))

            # Render MCQs in 10-column compact blocks
            chunk_size = 10
            for i in range(0, len(mcqs), chunk_size):
                chunk = mcqs[i : i + chunk_size]
                header_row = [Paragraph(f"Q{q.question_number}", th_style) for q in chunk]
                ans_row = [Paragraph(f"<b>{esc(q.correct_answer or '-')}</b>", tc_style) for q in chunk]
                # Pad to 10 columns if needed
                while len(header_row) < 10:
                    header_row.append(Paragraph("", th_style))
                    ans_row.append(Paragraph("", tc_style))

                table_data = [header_row, ans_row]
                t = Table(table_data, colWidths=[17.5 * mm] * 10)
                t.setStyle(
                    TableStyle([
                        ("GRID", (0, 0), (-1, -1), 0.5, "#444444"),
                        ("BACKGROUND", (0, 0), (-1, 0), "#EAEAEA"),
                        ("BACKGROUND", (0, 1), (-1, 1), "#F8FAF8"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ])
                )
                story.append(t)
                story.append(Spacer(1, 2 * mm))

        if theory:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("<b>SECTION B / C: THEORY & ESSAY MARKING SCHEMES</b>", body_style))
            story.append(Spacer(1, 2 * mm))

            theory_rows = [[
                Paragraph("<b>Q#</b>", th_style),
                Paragraph("<b>Marks</b>", th_style),
                Paragraph("<b>Expected Answer / Marking Criteria</b>", th_style),
            ]]
            for q in theory:
                criteria = []
                if q.correct_answer:
                    criteria.append(f"<b>Key Answer:</b> {esc(q.correct_answer)}")
                if q.marking_scheme:
                    criteria.append("<b>Marking Scheme:</b>")
                    for pt in q.marking_scheme:
                        criteria.append(f"• {esc(str(pt))}")
                if q.explanation:
                    criteria.append(f"<i>Note: {esc(q.explanation)}</i>")
                criteria_text = "<br/>".join(criteria) if criteria else "Award marks per teacher rubric."

                theory_rows.append([
                    Paragraph(f"Q{q.question_number}", tc_style),
                    Paragraph(f"{q.marks}m", tc_style),
                    Paragraph(criteria_text, body_style),
                ])

            tt = Table(theory_rows, colWidths=[15 * mm, 16 * mm, 144 * mm])
            tt.setStyle(
                TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.5, "#444444"),
                    ("BACKGROUND", (0, 0), (-1, 0), "#EAEAEA"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ])
            )
            story.append(tt)

        story.append(Spacer(1, 6 * mm))
        sig_data = [[
            Paragraph("<b>Subject Teacher:</b> ___________________________", body_style),
            Paragraph("<b>HOD / Principal:</b> ___________________________", body_style),
        ]]
        sig_table = Table(sig_data, colWidths=[87 * mm, 87 * mm])
        sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(sig_table)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=f"Marking Guide - {exam.subject}",
        )
        doc.build(story)
        return file_name

    @classmethod
    def export_omr_sheet_pdf(
        cls,
        exam: Exam,
        school_name: str | None = None,
    ) -> str:
        """Export a standardized 50-question A4 OMR Bubble Sheet for optical/rapid marking."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from xml.sax.saxutils import escape

        def esc(text: str) -> str:
            return escape(cls._clean(text))

        directory = cls.exam_dir(exam.id)
        directory.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}.pdf"
        output_path = directory / file_name

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("OMRTitle", parent=styles["Heading1"], fontSize=13, leading=16, alignment=1)
        sub_style = ParagraphStyle("OMRSub", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=1)
        field_style = ParagraphStyle("OMRField", parent=styles["Normal"], fontSize=9, leading=13)
        cell_style = ParagraphStyle("OMRCell", parent=styles["Normal"], fontSize=8.5, leading=11, fontName="Courier")

        story = []
        if school_name:
            story.append(Paragraph(f"<b>{esc(school_name.upper())}</b>", title_style))
        story.append(Paragraph(f"<b>{esc(exam.subject).upper()} — OMR ANSWER SHEET</b>", title_style))
        story.append(Paragraph("Instructions: Shade bubbles completely with 2B/HB pencil. Erase cleanly any change.", sub_style))
        story.append(Spacer(1, 3 * mm))

        # Candidate Details Header Table
        hdr_data = [
            [
                Paragraph("<b>Candidate Name:</b> ___________________________", field_style),
                Paragraph("<b>Class:</b> ____________", field_style),
                Paragraph("<b>Score:</b> [ &nbsp; &nbsp; / 50 ]", field_style),
            ],
            [
                Paragraph("<b>Candidate ID:</b> ___________________________", field_style),
                Paragraph("<b>Date:</b> _____________", field_style),
                Paragraph("<b>Supervisor Sign:</b> _________", field_style),
            ],
        ]
        ht = Table(hdr_data, colWidths=[75 * mm, 45 * mm, 54 * mm])
        ht.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, "#000000"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(ht)
        story.append(Spacer(1, 4 * mm))

        # 50 Questions in 2 columns of 25 rows each
        left_rows = []
        right_rows = []
        for qnum in range(1, 26):
            left_rows.append(Paragraph(f"<b>{qnum:02d}.</b> &nbsp;[A] &nbsp;[B] &nbsp;[C] &nbsp;[D] &nbsp;[E]", cell_style))
        for qnum in range(26, 51):
            right_rows.append(Paragraph(f"<b>{qnum:02d}.</b> &nbsp;[A] &nbsp;[B] &nbsp;[C] &nbsp;[D] &nbsp;[E]", cell_style))

        omr_table_data = []
        for i in range(25):
            omr_table_data.append([left_rows[i], right_rows[i]])

        omr_table = Table(omr_table_data, colWidths=[87 * mm, 87 * mm])
        omr_table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, "#cccccc"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
            ])
        )
        story.append(omr_table)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
            title=f"OMR Sheet - {exam.subject}",
        )
        doc.build(story)
        return file_name
