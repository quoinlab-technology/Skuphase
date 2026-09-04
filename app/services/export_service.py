"""Export service for exam documents (ReportLab platypus, word-wrapped)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

from app.models.exam import Exam, Question


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
            )
        except Exception as e:  # pragma: no cover - env without reportlab
            raise ValueError(f"PDF export dependencies are not available: {e}") from e

        directory = cls.exam_dir(exam.id)
        directory.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}.pdf"
        output_path = directory / file_name

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ExamTitle", parent=styles["Title"], fontSize=16, spaceAfter=2 * mm
        )
        meta_style = ParagraphStyle(
            "ExamMeta", parent=styles["Normal"], fontSize=10, spaceAfter=1.5 * mm
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

        header = [
            Paragraph(f"{esc(exam.subject)} — {esc(exam.grade_level)}", title_style),
            Paragraph(
                f"Duration: {exam.duration_minutes or '-'} minutes &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Total Marks: {exam.total_marks}",
                meta_style,
            ),
        ]
        if exam.instructions:
            header.append(Paragraph("<b>Instructions</b>", meta_style))
            for line in cls._clean(exam.instructions).splitlines():
                if line.strip():
                    header.append(Paragraph(esc(line), meta_style))
        story.append(Table([[header]], colWidths=[None]))
        story[-1].setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.75, "#444444"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(Spacer(1, 4 * mm))

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
            if q.question_text and getattr(q, "section_title", None):
                pass  # sections are flattened onto questions by numbering only

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
                for option in q.options:
                    story.append(Paragraph(esc(str(option)), option_style))

            if include_answers:
                if q.correct_answer:
                    story.append(Paragraph(f"<b>Answer:</b> {esc(q.correct_answer)}", answer_style))
                if q.marking_scheme:
                    story.append(Paragraph("<b>Marking scheme:</b>", answer_style))
                    for point in q.marking_scheme:
                        story.append(Paragraph(f"• {esc(str(point))}", answer_style))
                if q.explanation:
                    story.append(Paragraph(f"<i>{esc(q.explanation)}</i>", answer_style))

            current_section = None  # noqa: F841 - kept for future section headers

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
