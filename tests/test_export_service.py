from types import SimpleNamespace
from pathlib import Path

from app.services.export_service import ExportService


def test_export_exam_pdf_creates_file(tmp_path):
    exam = SimpleNamespace(
        id="exam-1",
        subject="Biology",
        grade_level="SSS 1",
        duration_minutes=90,
        total_marks=20,
        instructions="Answer all questions.",
    )
    questions = [
        SimpleNamespace(
            question_number=1,
            question_text="Define photosynthesis.",
            marks=5,
            options=None,
            correct_answer=None,
            marking_scheme=["Definition", "Process", "Products"],
        ),
        SimpleNamespace(
            question_number=2,
            question_text="Which organelle performs photosynthesis?",
            marks=2,
            options=["A. Nucleus", "B. Chloroplast", "C. Ribosome", "D. Mitochondria"],
            correct_answer="B",
            marking_scheme=None,
        ),
    ]

    original_dir = ExportService.EXPORT_DIR
    ExportService.EXPORT_DIR = Path(tmp_path)
    try:
        file_path = ExportService.export_exam_pdf(
            exam=exam,
            questions=questions,
            include_answers=True,
        )
    finally:
        ExportService.EXPORT_DIR = original_dir

    path = Path(file_path)
    assert path.exists()
    assert path.suffix == ".pdf"
