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
from app.services.math_rendering import formula_to_svg
from app.services.export_service import _svg_to_flowable

_FORMULA_TOKEN = re.compile(r"\\\[(.+?)\\\]|\\\((.+?)\\\)|\$\$(.+?)\$\$|(?<!\$)\$(?!\$)(.+?)(?<!\$)\$", re.DOTALL)


def _append_rich_text(story: list, value: str, body: ParagraphStyle, *, prefix: str = "", suffix: str = "") -> None:
    """Render formula delimiters as the same vector math used by exam PDFs."""
    text = str(value or "")
    matches = list(_FORMULA_TOKEN.finditer(text))
    if not matches:
        safe_text = "<br/>".join(escape(line) for line in text.splitlines())
        story.append(Paragraph(prefix + safe_text + suffix, body))
        return
    cursor = 0
    first_text = True
    for match in matches:
        plain = text[cursor:match.start()]
        if plain.strip() or (first_text and prefix):
            safe_plain = "<br/>".join(escape(line) for line in plain.splitlines())
            story.append(Paragraph(prefix + safe_plain, body))
            first_text = False
        latex = next((part for part in match.groups() if part is not None), "").strip()
        drawing = _svg_to_flowable(formula_to_svg(latex), max_width_pt=380, max_height_pt=60)
        if drawing is not None:
            story.append(drawing)
        else:
            story.append(Paragraph(escape(latex), body))
        cursor = match.end()
    remainder = text[cursor:]
    if remainder.strip() or first_text:
        safe_remainder = "<br/>".join(escape(line) for line in remainder.splitlines())
        story.append(Paragraph(prefix + safe_remainder + suffix, body))
    elif suffix:
        story.append(Paragraph(suffix.lstrip(), body))


def export_worksheet_pdf(*, export_dir: Path, title: str, subject: str, grade_level: str, term: str | None = None, instructions: str | None, questions: list[dict], school_name: str | None = None, school_logo_path: str | None = None) -> str:
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
    if logo_image or school_name:
        from reportlab.platypus import Table, TableStyle
        identity = []
        if logo_image:
            identity.append(logo_image)
        if school_name:
            identity.append(Paragraph(escape(school_name.upper()), ParagraphStyle("WorksheetBrand", parent=styles["Normal"], fontSize=10, alignment=1, spaceAfter=2 * mm)))
        story.append(Table([identity], colWidths=[170 * mm], style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")])) )
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
        try:
            mark_value = int(marks) if marks is not None else 0
        except (TypeError, ValueError):
            mark_value = 0
        mark_label = f"[{mark_value} {'mark' if mark_value == 1 else 'marks'}]" if mark_value > 0 else ""
        _append_rich_text(
            story,
            raw_text,
            body,
            prefix=f"<b>{index}.</b> ",
            suffix=f" <b>{escape(mark_label)}</b>" if mark_label else "",
        )
        if str(question.get("type", "")).lower() == "mcq":
            options = question.get("answer_options") or []
            for option_index, option in enumerate(options):
                label = chr(ord("A") + option_index) if option_index < 26 else str(option_index + 1)
                _append_rich_text(story, str(option), body, prefix=f"&nbsp;&nbsp;&nbsp;{label}. ")
        try:
            answer_lines = max(0, min(12, int(question.get("answer_lines", 2))))
        except (TypeError, ValueError):
            answer_lines = 2
        for _ in range(answer_lines):
            story.append(Paragraph("________________________________________________________________________________", body))
    def _watermark(canvas, _doc):
        if not school_name:
            return
        from reportlab.lib.colors import HexColor
        canvas.saveState()
        canvas.setFillColor(HexColor("#E5ECE8"))
        canvas.setFont("Helvetica-Bold", 27)
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, school_name.upper()[:60])
        canvas.restoreState()

    doc.build(story, onFirstPage=_watermark, onLaterPages=_watermark)
    return filename
