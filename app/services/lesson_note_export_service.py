"""PDF rendering for saved teacher lesson notes."""

from __future__ import annotations

import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


_INLINE_TOKEN_RE = re.compile(
    r"(\$[^$]+\$|\\\(.+?\\\)|\*\*.+?\*\*|`[^`]+`|(?<!\*)\*[^*]+\*(?!\*))"
)


def _readable_inline_formula(source: str) -> str:
    """Turn common inline TeX into readable text without exposing delimiters."""
    value = source.strip().strip("$")
    if value.startswith(r"\(") and value.endswith(r"\)"):
        value = value[2:-2]
    value = re.sub(r"\\(?:left|right)\b", "", value)
    value = re.sub(r"\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", value)
    value = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", value)
    for command, symbol in {
        r"\times": "×", r"\div": "÷", r"\pm": "±", r"\cdot": "·",
        r"\leq": "≤", r"\geq": "≥", r"\neq": "≠", r"\rightarrow": "→",
        r"\to": "→", r"\pi": "π", r"\theta": "θ", r"\Delta": "Δ",
        r"\lambda": "λ", r"\infty": "∞", r"\log": "log", r"\sin": "sin",
        r"\cos": "cos", r"\tan": "tan", r"\ln": "ln",
    }.items():
        value = value.replace(command, symbol)
    value = re.sub(r"\\[,;!]", " ", value)
    value = re.sub(r"([_^])\{([^{}]*)\}", r"\1\2", value)
    value = re.sub(r"\\([{}%&#_$])", r"\1", value)
    value = re.sub(r"\\[a-zA-Z]+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _reportlab_inline(text: str) -> str:
    """Escape untrusted content while supporting safe Markdown emphasis/code."""
    rendered: list[str] = []
    for token in _INLINE_TOKEN_RE.split(text):
        if not token:
            continue
        if token.startswith("$") or token.startswith(r"\("):
            rendered.append(escape(_readable_inline_formula(token)))
        elif token.startswith("**") and token.endswith("**"):
            rendered.append(f"<b>{escape(token[2:-2])}</b>")
        elif token.startswith("*") and token.endswith("*"):
            rendered.append(f"<i>{escape(token[1:-1])}</i>")
        elif token.startswith("`") and token.endswith("`"):
            rendered.append(f'<font name="Courier">{escape(token[1:-1])}</font>')
        else:
            rendered.append(escape(token))
    return "".join(rendered)


def export_lesson_note_pdf(
    *,
    title: str,
    subject: str,
    class_level: str,
    term: str,
    week_number: int,
    content: str,
    school_name: str | None = None,
) -> bytes:
    """Render a saved lesson note to a printable, safely escaped PDF."""
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title[:200],
        author=(school_name or "SkuPhase")[:200],
    )
    styles = getSampleStyleSheet()
    school_style = ParagraphStyle(
        "LessonNoteSchool", parent=styles["Normal"], alignment=TA_CENTER,
        fontSize=10, leading=13, textColor=colors.HexColor("#53615B"), spaceAfter=2 * mm,
    )
    title_style = ParagraphStyle(
        "LessonNoteTitle", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=17, leading=21, textColor=colors.HexColor("#064E3B"), spaceAfter=3 * mm,
    )
    meta_style = ParagraphStyle(
        "LessonNoteMeta", parent=styles["Normal"], alignment=TA_CENTER,
        fontSize=9, leading=13, textColor=colors.HexColor("#53615B"), spaceAfter=7 * mm,
    )
    body_style = ParagraphStyle(
        "LessonNoteBody", parent=styles["BodyText"], fontSize=10, leading=15,
        spaceAfter=2.5 * mm, wordWrap="CJK",
    )
    heading_style = ParagraphStyle(
        "LessonNoteSection", parent=styles["Heading2"], fontSize=12, leading=16,
        textColor=colors.HexColor("#064E3B"), spaceBefore=3 * mm, spaceAfter=1.5 * mm,
    )

    story = []
    if school_name:
        story.append(Paragraph(escape(school_name), school_style))
    story.append(Paragraph(escape(title), title_style))
    meta = " · ".join(
        part for part in (
            f"{subject} · {class_level}" if subject or class_level else "",
            term,
            f"Week {week_number}",
        ) if part
    )
    story.append(Paragraph(escape(meta), meta_style))

    for raw_line in (content or "").splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
            continue
        if re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})", line):
            story.append(Spacer(1, 1.5 * mm))
            continue
        heading = re.sub(r"^#{1,3}\s*", "", line).rstrip(":").strip()
        if line.startswith("#") or heading.casefold() in {
            "objectives", "learning objectives", "starter", "introduction",
            "explanation", "guided practice", "assessment", "differentiation",
            "teaching materials", "resources", "conclusion",
        }:
            story.append(Paragraph(_reportlab_inline(heading), heading_style))
        elif line.startswith(("- ", "* ", "• ")):
            story.append(Paragraph(_reportlab_inline(line[2:]), body_style, bulletText="•"))
        elif re.match(r"^\d+[.)]\s+", line):
            story.append(Paragraph(_reportlab_inline(line), body_style))
        else:
            story.append(Paragraph(_reportlab_inline(line), body_style))

    document.build(story)
    return stream.getvalue()


def export_lesson_note_docx(
    *,
    title: str,
    subject: str,
    class_level: str,
    term: str,
    week_number: int,
    content: str,
    school_name: str | None = None,
    teacher_name: str | None = None,
) -> bytes:
    """Build an editable Word lesson note from the saved Markdown-like text.

    Headings, lists, and simple pipe tables become native Word structures.
    Inline math remains as literal TeX source (for example ``$a^2+b^2$``),
    rather than being silently discarded or misrepresented as rendered math.
    """
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    normal = document.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(5)

    if school_name:
        school = document.add_paragraph()
        school.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = school.add_run(school_name.strip())
        run.bold = True
        run.font.color.rgb = RGBColor(6, 78, 59)
        run.font.size = Pt(11)

    heading = document.add_paragraph()
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = heading.add_run(title.strip() or "Lesson Note")
    title_run.bold = True
    title_run.font.color.rgb = RGBColor(6, 78, 59)
    title_run.font.size = Pt(17)

    metadata = document.add_paragraph()
    metadata.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta = " | ".join(part for part in (
        f"Subject: {subject}" if subject else "",
        f"Class: {class_level}" if class_level else "",
        f"Term: {term}" if term else "",
        f"Week {week_number}" if week_number else "",
        f"Teacher: {teacher_name}" if teacher_name else "",
    ) if part)
    metadata.add_run(meta).font.color.rgb = RGBColor(83, 97, 91)

    known_headings = {
        "objectives", "learning objectives", "starter", "introduction",
        "explanation", "guided practice", "assessment", "differentiation",
        "teaching materials", "resources", "conclusion",
    }

    def add_inline(paragraph, text: str) -> None:
        # Preserve TeX literally; translate only simple Markdown emphasis/code.
        tokens = re.split(r"(\*\*.+?\*\*|`[^`]+`|\$[^$]+\$)", text)
        for token in tokens:
            if not token:
                continue
            if token.startswith("**") and token.endswith("**"):
                paragraph.add_run(token[2:-2]).bold = True
            elif token.startswith("`") and token.endswith("`"):
                run = paragraph.add_run(token[1:-1])
                run.font.name = "Consolas"
            else:
                paragraph.add_run(token)

    def table_cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    def is_table_separator(line: str) -> bool:
        cells = table_cells(line)
        return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)

    lines = (content or "").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})", line):
            index += 1
            continue

        if line.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1].strip()):
            rows = [table_cells(line)]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(table_cells(lines[index]))
                index += 1
            column_count = max(len(row) for row in rows)
            table = document.add_table(rows=1, cols=column_count)
            table.style = "Table Grid"
            table.autofit = True
            for row_index, values in enumerate(rows):
                cells = table.rows[0].cells if row_index == 0 else table.add_row().cells
                for col_index in range(column_count):
                    cell = cells[col_index]
                    cell.text = values[col_index] if col_index < len(values) else ""
                    if row_index == 0:
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
            document.add_paragraph()
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            paragraph = document.add_heading(heading_match.group(2).strip(), level=level)
        elif line.rstrip(":").casefold() in known_headings:
            paragraph = document.add_heading(line.rstrip(":").strip(), level=2)
        elif re.match(r"^(?:[-*]|•)\s+", line):
            paragraph = document.add_paragraph(style="List Bullet")
            add_inline(paragraph, re.sub(r"^(?:[-*]|•)\s+", "", line))
        elif re.match(r"^\d+[.)]\s+", line):
            paragraph = document.add_paragraph(style="List Number")
            add_inline(paragraph, re.sub(r"^\d+[.)]\s+", "", line))
        else:
            paragraph = document.add_paragraph()
            add_inline(paragraph, line)
        index += 1

    if not (content or "").strip():
        document.add_paragraph("No lesson-note content was provided.")

    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()
