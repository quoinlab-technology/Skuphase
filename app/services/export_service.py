"""Export service for exam documents."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List

from app.models.exam import Exam, Question


class ExportService:
    """Generate export files for exams (PDF MVP)."""

    EXPORT_DIR = Path("exports")

    @classmethod
    def export_exam_pdf(
        cls,
        exam: Exam,
        questions: List[Question],
        include_answers: bool = False,
        question_assets: Dict[str, List[Dict[str, Any]]] | None = None,
    ) -> str:
        """
        Export exam to PDF and return file path.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except Exception as e:
            raise ValueError(f"PDF export dependencies are not available: {str(e)}")

        cls.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"exam_{exam.id}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = cls.EXPORT_DIR / file_name

        c = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4
        margin = 18 * mm
        y = height - margin
        line_height = 6 * mm
        max_image_width = width - (2 * margin)
        question_assets = question_assets or {}

        def draw_line(text: str, bold: bool = False) -> None:
            nonlocal y
            if y < margin:
                c.showPage()
                y = height - margin
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
            c.drawString(margin, y, text[:120])
            y -= line_height

        def draw_image_block(image_path: str, caption: str) -> None:
            nonlocal y
            try:
                image_reader = ImageReader(image_path)
                img_width, img_height = image_reader.getSize()
                if not img_width or not img_height:
                    raise ValueError("Invalid image dimensions")

                scale = min(max_image_width / img_width, 110 * mm / img_height, 1.0)
                render_width = img_width * scale
                render_height = img_height * scale
                needed_height = render_height + (2 * line_height)
                if y - needed_height < margin:
                    c.showPage()
                    y = height - margin

                c.drawImage(
                    image_reader,
                    margin,
                    y - render_height,
                    width=render_width,
                    height=render_height,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                y -= render_height + line_height
                draw_line(caption)
            except Exception:
                draw_line(f"[Asset unavailable] {caption}")

        draw_line(f"Subject: {exam.subject}", bold=True)
        draw_line(f"Grade: {exam.grade_level}")
        draw_line(f"Duration: {exam.duration_minutes or '-'} minutes")
        draw_line(f"Total Marks: {exam.total_marks}")
        draw_line("")

        if exam.instructions:
            draw_line("Instructions:", bold=True)
            for line in exam.instructions.splitlines():
                draw_line(line)
            draw_line("")

        for q in questions:
            draw_line(f"Q{q.question_number}. {q.question_text} ({q.marks} marks)", bold=True)

            if q.options:
                for option in q.options:
                    draw_line(f"   {option}")

            if include_answers:
                if q.correct_answer:
                    draw_line(f"   Answer: {q.correct_answer}")
                if q.marking_scheme:
                    draw_line("   Marking scheme:")
                    for point in q.marking_scheme:
                        draw_line(f"   - {point}")

            linked_assets = question_assets.get(str(q.id), [])
            for index, asset in enumerate(linked_assets, start=1):
                caption = (
                    f"Figure {q.question_number}.{index}: "
                    f"{asset.get('reference_code') or asset.get('title') or 'Linked asset'}"
                )
                draw_image_block(
                    image_path=str(asset.get("file_path") or ""),
                    caption=caption,
                )
            draw_line("")

        c.save()
        return str(output_path).replace("\\", "/")
