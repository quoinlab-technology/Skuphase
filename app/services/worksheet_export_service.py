"""Printable weekly exercise worksheet export."""
import re
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.services.branding import logo_flowable


def export_worksheet_pdf(*, export_dir: Path, title: str, subject: str, grade_level: str, term: str | None = None, instructions: str | None, questions: list[dict], school_logo_path: str | None = None) -> str:
    folder = export_dir / "worksheets"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.pdf"
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("WorksheetHeading", parent=styles["Heading1"], fontSize=14, alignment=1, spaceAfter=4 * mm)
    body = ParagraphStyle("WorksheetBody", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=2 * mm)
    doc = SimpleDocTemplate(str(folder / filename), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    story = []
    total_marks = 0
    for question in questions:
        if not isinstance(question, dict):
            continue
        question_text = str(question.get("question_text") or question.get("text") or "")
        suffix = re.search(r"\s*\[(\d+)\s+marks?\]\s*$", question_text, re.IGNORECASE)
        value = suffix.group(1) if suffix else question.get("marks", 1)
        try:
            total_marks += max(0, int(value))
        except (TypeError, ValueError):
            continue
    logo_image = logo_flowable(school_logo_path, width=18 * mm, height=18 * mm)
    if logo_image:
        from reportlab.platypus import Table, TableStyle
        story.append(Table([[logo_image]], colWidths=[170 * mm], style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")])) )
    story.extend([
        Paragraph(escape(title), heading),
        Paragraph(
            escape(f"Subject: {subject or 'Not specified'}  |  Class: {grade_level or 'Not specified'}  |  Term: {term or 'Not specified'}"),
            body,
        ),
        Paragraph(escape(f"Total marks: {total_marks}"), body),
    ])
    if instructions:
        story += [Paragraph(f"<b>Instructions:</b> {escape(instructions)}", body), Spacer(1, 2 * mm)]
    for index, question in enumerate(questions, 1):
        if not isinstance(question, dict):
            continue
        raw_text = str(question.get("question_text") or question.get("text") or "").strip()
        suffix = re.search(r"\s*\[(\d+)\s+marks?\]\s*$", raw_text, re.IGNORECASE)
        marks = question.get("marks")
        if suffix:
            # Older rows stored the mark suffix in the text while the UI
            # hardcoded marks=1. The explicit suffix is the reliable source.
            marks = int(suffix.group(1))
            raw_text = raw_text[:suffix.start()].strip()
        text = escape(raw_text)
        try:
            mark_value = int(marks) if marks is not None else 0
        except (TypeError, ValueError):
            mark_value = 0
        mark_label = f"[{mark_value} {'mark' if mark_value == 1 else 'marks'}]" if mark_value > 0 else ""
        story.append(Paragraph(f"<b>{index}.</b> {text}" + (f" <b>{mark_label}</b>" if mark_label else ""), body))
        if str(question.get("type", "")).lower() == "mcq":
            options = question.get("answer_options") or []
            for option_index, option in enumerate(options):
                label = chr(ord("A") + option_index) if option_index < 26 else str(option_index + 1)
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;{label}. {escape(str(option))}", body))
        try:
            answer_lines = max(0, min(12, int(question.get("answer_lines", 2))))
        except (TypeError, ValueError):
            answer_lines = 2
        for _ in range(answer_lines):
            story.append(Paragraph("________________________________________________________________________________", body))
    doc.build(story)
    return filename
