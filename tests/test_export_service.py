"""Export service tests — word-wrap, download naming, answer key."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.services.export_service import ExportService


def _exam():
    return SimpleNamespace(
        id=uuid4(),
        subject="Basic Science",
        grade_level="Primary 4",
        duration_minutes=90,
        total_marks=7,
        instructions=(
            "Answer ALL questions in section A.\n"
            "Answer any TWO questions in section B."
        ),
    )


def _questions():
    long_text = (
        "A farmer in Kano planted cassava and maize on the same plot of land "
        "during the rainy season. Explain TWO benefits the farmer gets from "
        "planting the two crops together, and mention ONE problem that may "
        "arise if the crops are planted too close to each other."
    )
    return [
        SimpleNamespace(
            question_number=1,
            type="multiple_choice",
            question_text="Which of these is a living thing?",
            marks=2,
            options=["A. goat", "B. stone", "C. water", "D. chair"],
            correct_answer="A",
            explanation="A goat grows, feeds and moves by itself.",
            marking_scheme=None,
        ),
        SimpleNamespace(
            question_number=2,
            type="essay",
            question_text=long_text,
            marks=5,
            options=None,
            correct_answer=None,
            explanation=None,
            marking_scheme=["Two benefits", "One problem"],
        ),
    ]


def test_export_exam_pdf_creates_wrapped_file(tmp_path):
    exam = _exam()
    original_dir = ExportService.EXPORT_DIR
    ExportService.EXPORT_DIR = Path(tmp_path)
    try:
        file_name = ExportService.export_exam_pdf(
            exam=exam,
            questions=_questions(),
            include_answers=True,
            school_name="Kings College Lagos",
            school_address="Catholic Mission Street, Lagos Island",
        )
        created_path = ExportService.exam_dir(exam.id) / file_name
    finally:
        ExportService.EXPORT_DIR = original_dir

    assert created_path.exists()
    assert created_path.suffix == ".pdf"
    # New naming contract: 32-hex UUID name (downloadable via router).
    assert len(Path(file_name).stem) == 32

    from pypdf import PdfReader

    reader = PdfReader(str(created_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    # Standard school header elements rendered
    assert "KINGS COLLEGE LAGOS" in text
    assert "Catholic Mission Street" in text

    # Section headers and answer key masthead
    assert "SECTION A" in text
    assert "MARKING SCHEME / ANSWER KEY" in text
    assert "FOR TEACHER USE ONLY" in text

    # A5 regression: no truncation at 120 chars — full question present.
    assert "planted too close" in text
    assert "Answer: A" in text  # include_answers renders the key
    assert "Marking scheme:" in text
    assert "Page" not in ""



def test_export_path_rejects_bad_names():
    exam_id = uuid4()
    try:
        ExportService.export_path(exam_id, "../../.env")
        raised = False
    except ValueError:
        raised = True
    assert raised

    good = f"{uuid4().hex}.pdf"
    path = ExportService.export_path(exam_id, good)
    assert str(path).endswith(good)
