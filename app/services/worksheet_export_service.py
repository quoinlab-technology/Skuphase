"""Printable weekly exercise worksheet export."""
from pathlib import Path
from uuid import uuid4
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from xml.sax.saxutils import escape
from app.services.branding import logo_flowable


def export_worksheet_pdf(*, export_dir: Path, title: str, subject: str, grade_level: str, instructions: str | None, questions: list[dict], school_logo_path: str | None = None) -> str:
    folder = export_dir / "worksheets"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.pdf"
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("WorksheetHeading", parent=styles["Heading1"], fontSize=14, alignment=1, spaceAfter=4 * mm)
    body = ParagraphStyle("WorksheetBody", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=2 * mm)
    doc = SimpleDocTemplate(str(folder / filename), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    story = []
    logo_image = logo_flowable(school_logo_path, width=18 * mm, height=18 * mm)
    if logo_image:
        from reportlab.platypus import Table, TableStyle
        story.append(Table([[logo_image]], colWidths=[170 * mm], style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")])) )
    story.extend([Paragraph(escape(title), heading), Paragraph(escape(f"{subject} - {grade_level}"), body)])
    if instructions:
        story += [Paragraph(f"<b>Instructions:</b> {escape(instructions)}", body), Spacer(1, 2 * mm)]
    for index, question in enumerate(questions, 1):
        text = escape(str(question.get("question_text") or question.get("text") or ""))
        marks = question.get("marks")
        story.append(Paragraph(f"<b>{index}.</b> {text}" + (f" <b>[{marks} marks]</b>" if marks else ""), body))
        for _ in range(int(question.get("answer_lines", 2))):
            story.append(Paragraph("________________________________________________________________________________", body))
    doc.build(story)
    return filename
