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


def test_svg_to_flowable_conversion():
    """Verify that svglib converts SVG into a ReportLab Drawing flowable."""
    from app.services.export_service import _svg_to_flowable

    sample_svg = (
        '<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="200" height="100" fill="#f0f0f0"/>'
        '<circle cx="100" cy="50" r="40" fill="#0d6efd"/>'
        '</svg>'
    )
    flowable = _svg_to_flowable(sample_svg)
    assert flowable is not None
    assert getattr(flowable, "width", 0) > 0
    assert getattr(flowable, "height", 0) > 0


def test_export_exam_pdf_with_svg_diagram(tmp_path):
    """Golden-file regression test: exams with SVG diagrams render into valid PDFs."""
    from app.services.diagram_templates import render_horizontal_y_fork

    exam = _exam()
    y_fork_svg = render_horizontal_y_fork(parent=10, child_top=3, child_bottom=7, sample_label="SAMPLE A")

    questions = [
        SimpleNamespace(
            question_number=1,
            type="multiple_choice",
            question_text="Study the sample diagram below and determine the missing value in the circle.",
            marks=2,
            options=["A. 15", "B. 20", "C. 25", "D. 30"],
            correct_answer="B",
            explanation="The parent circle equals the sum of the two rectangles.",
            marking_scheme=None,
            diagram_svg=y_fork_svg,
        )
    ]

    original_dir = ExportService.EXPORT_DIR
    ExportService.EXPORT_DIR = Path(tmp_path)
    try:
        file_name = ExportService.export_exam_pdf(
            exam=exam,
            questions=questions,
            include_answers=True,
            school_name="Federal Government College Lagos",
            school_address="Ijanikin, Lagos",
        )
        created_path = ExportService.exam_dir(exam.id) / file_name
    finally:
        ExportService.EXPORT_DIR = original_dir

    assert created_path.exists()
    assert created_path.stat().st_size > 1000

    from pypdf import PdfReader
    reader = PdfReader(str(created_path))
    assert len(reader.pages) >= 1
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Study the sample diagram" in text
    assert "FEDERAL GOVERNMENT COLLEGE LAGOS" in text

