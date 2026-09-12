"""Export service for exam documents (ReportLab platypus, word-wrapped)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

from app.models.exam import Exam, Question
from app.utils.exam_utils import format_mcq_option


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
        """Normalise text for PDF rendering (strip fences, control chars)."""
        if not text:
            return ""
        cleaned = str(text)
        # Mermaid blocks cannot render in reportlab: keep a caption placeholder.
        cleaned = re.sub(
            r"```mermaid\s*(.*?)\s*```",
            lambda m: f"[Diagram: {m.group(1).splitlines()[0] if m.group(1).splitlines() else 'see question'}]",
            cleaned,
            flags=re.DOTALL,
        )
        cleaned = re.sub(r"``([a-zA-Z]*)\n?", "", cleaned)
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
        except Exception as e:  # pragma: no cover - env without reportlab
            raise ValueError(f"PDF export dependencies are not available: {e}") from e

        directory = cls.exam_dir(exam.id)
        directory.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}.pdf"
        output_path = directory / file_name

        styles = getSampleStyleSheet()
        school_name_style = ParagraphStyle(
            "SchoolName", parent=styles["Title"], fontSize=15, leading=18, alignment=1, spaceAfter=1 * mm
        )
        school_addr_style = ParagraphStyle(
            "SchoolAddr", parent=styles["Normal"], fontSize=9, leading=12, alignment=1, textColor="#555555", spaceAfter=2 * mm
        )
        title_style = ParagraphStyle(
            "ExamTitle", parent=styles["Heading1"], fontSize=12, leading=15, alignment=1, spaceAfter=2 * mm
        )
        meta_style = ParagraphStyle(
            "ExamMeta", parent=styles["Normal"], fontSize=9.5, leading=13, alignment=1, spaceAfter=1.5 * mm
        )
        instruction_style = ParagraphStyle(
            "ExamInstructions", parent=styles["Normal"], fontSize=9, leading=12, spaceAfter=1 * mm
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=11,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        )
        question_style = ParagraphStyle(
            "QuestionText",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            spaceBefore=3 * mm,
            spaceAfter=1 * mm,
        )
        option_style = ParagraphStyle(
            "OptionText", parent=styles["Normal"], fontSize=10, leading=13, leftIndent=18
        )
        answer_style = ParagraphStyle(
            "AnswerText",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            leftIndent=18,
            textColor="#333333",
        )

        def esc(text: str) -> str:
            from xml.sax.saxutils import escape

            return escape(cls._clean(text)).replace("\n", "<br/>")

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
        story.append(Spacer(1, 4 * mm))

        # Pre-compute section marks
        section_marks: dict = {}
        for q in questions:
            stitle = getattr(q, "section_title", None)
            if not stitle:
                qtype = getattr(q, "type", "multiple_choice")
                if qtype == "multiple_choice":
                    stitle = "SECTION A — OBJECTIVE QUESTIONS"
                elif qtype in ("short_answer", "theory"):
                    stitle = "SECTION B — SHORT ANSWER / THEORY"
                elif qtype == "essay":
                    stitle = "SECTION C — ESSAY QUESTIONS"
                else:
                    stitle = "SECTION A"
            section_marks[stitle] = section_marks.get(stitle, 0) + (getattr(q, "marks", 0) or 0)

        current_section = None
        rendered_passage_ids: set = set()
        passage_meta: dict = {}
        for p in (passages or []):
            pid = getattr(p, "id", None)
            if pid is None:
                continue
            p_title = getattr(p, "title", None) or ""
            p_body = getattr(p, "body", "") or ""
            p_section = getattr(p, "section_number", None) or ""
            passage_meta[str(pid)] = (p_title, p_body, p_section)

        for q in questions:
            sec_title = getattr(q, "section_title", None)
            if not sec_title:
                qtype = getattr(q, "type", "multiple_choice")
                if qtype == "multiple_choice":
                    sec_title = "SECTION A — OBJECTIVE QUESTIONS"
                elif qtype in ("short_answer", "theory"):
                    sec_title = "SECTION B — SHORT ANSWER / THEORY"
                elif qtype == "essay":
                    sec_title = "SECTION C — ESSAY QUESTIONS"
                else:
                    sec_title = "SECTION A"

            if sec_title != current_section:
                current_section = sec_title
                tot_m = section_marks.get(sec_title, 0)
                marks_suffix = f" ({tot_m} MARKS)" if tot_m > 0 else ""
                story.append(
                    Paragraph(f"<b>{esc(sec_title.upper())}{marks_suffix}</b>", section_style)
                )
                story.append(Spacer(1, 1.5 * mm))

            pid = str(getattr(q, "passage_id", "") or "")
            if pid in passage_meta and pid not in rendered_passage_ids:
                rendered_passage_ids.add(pid)
                p_title, p_body, p_section = passage_meta[pid]
                section_label = f"Section {p_section}: " if p_section else ""
                story.append(
                    Paragraph(
                        f"<b>{esc(section_label)}Read the passage and answer the questions that follow.</b>",
                        question_style,
                    )
                )
                if p_title:
                    story.append(Paragraph(f"<b>{esc(p_title)}</b>", question_style))
                for para in p_body.splitlines():
                    if para.strip():
                        story.append(Paragraph(esc(para), question_style))
                story.append(Spacer(1, 3 * mm))

            marks_bit = f"&nbsp;&nbsp;<b>[{q.marks}]</b>" if q.marks else ""
            story.append(
                Paragraph(f"<b>Q{q.question_number}.</b> {esc(q.question_text)}{marks_bit}", question_style)
            )

            if q.options:
                for idx, option in enumerate(q.options):
                    opt_str = format_mcq_option(str(option), idx)
                    story.append(Paragraph(esc(opt_str), option_style))

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
            story.append(Spacer(1, 6 * mm))
            footer_style = ParagraphStyle(
                "TeacherOnlyFooter", parent=styles["Normal"], fontSize=8, leading=10, alignment=1, textColor="#777777"
            )
            story.append(Paragraph("<b>FOR TEACHER USE ONLY — NOT FOR DISTRIBUTION</b>", footer_style))


        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=f"{exam.subject} {exam.grade_level}",
        )

        def _footer(canvas, _doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.drawCentredString(
                A4[0] / 2, 10 * mm, f"Page {_doc.page}"
            )
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return file_name
