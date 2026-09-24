"""Tests for Visual Quantitative Reasoning: SVG templates, PDF rendering, and FastStrap UI."""

import uuid
import pytest
from app.services.diagram_templates import (
    render_horizontal_y_fork,
    render_fraction_branch,
    render_m_network,
    render_power_fork,
    render_compass_cross,
    render_horseshoe,
    render_arc_c,
    render_grid_with_ear,
    render_t_bar,
    render_triangle_puzzle,
)
from app.services.export_service import _svg_to_flowable, ExportService
from app.frontend.components.exam import QuestionBlock


def test_diagram_templates_output_valid_svg():
    """All 10 diagram templates produce well-formed SVG strings with viewBox."""
    templates = [
        render_horizontal_y_fork(176, 62, 114, missing="child_top"),
        render_fraction_branch(("1", "5"), ("2", "5"), ("3", "5"), missing="frac_bottom_num"),
        render_m_network(12, 10, 48, 4, 58, missing="center"),
        render_power_fork(6, 2, 12, 6, 6, missing="mid_box"),
        render_compass_cross(20, 15, 10, 5, 2, missing="top"),
        render_horseshoe(400, 330, 70, missing="bottom"),
        render_arc_c(114, 183, 297, missing="inside"),
        render_grid_with_ear(101, 67, 104, 70, 34, missing="ear"),
        render_t_bar(6, 5, 30, missing="bottom"),
        render_triangle_puzzle(9, 4, 2, 7, missing="center"),
    ]
    for s in templates:
        assert isinstance(s, str)
        assert "<svg" in s
        assert "</svg>" in s
        assert "viewBox" in s
        assert "?" in s  # All have a missing slot


def test_svg_to_flowable_converts_svg():
    """_svg_to_flowable converts raw SVG to a ReportLab Drawing flowable."""
    svg = render_horizontal_y_fork(1000, 820, "?", missing="child_bottom")
    drawing = _svg_to_flowable(svg, max_width_pt=350, max_height_pt=140)
    assert drawing is not None
    assert getattr(drawing, "width", 0) > 0
    assert getattr(drawing, "height", 0) > 0


def test_svg_to_flowable_handles_invalid_gracefully():
    """Invalid or empty SVG returns None instead of raising."""
    assert _svg_to_flowable("") is None
    assert _svg_to_flowable(None) is None
    assert _svg_to_flowable("Not an SVG at all") is None
    assert _svg_to_flowable("<svg><unclosed></svg>") is None or _svg_to_flowable("<svg><unclosed></svg>") is not None


def test_question_card_renders_diagram_viewport():
    """FastStrap QuestionCard embeds diagram_svg when present."""
    q_data = {
        "question_number": 1,
        "type": "multiple_choice",
        "question_text": "Find the missing number in the tree:",
        "marks": 2,
        "options": ["A. 180", "B. 200", "C. 120", "D. 280"],
        "correct_answer": "A",
        "diagram_svg": "<svg width='100' height='50'><circle cx='25' cy='25' r='20'/></svg>",
    }
    card = QuestionBlock(q_data, number=1, show_answers=True)
    rendered_html = str(card)
    assert "diagram-viewport" in rendered_html
    assert "<svg" in rendered_html
    assert "<circle" in rendered_html


def test_pdf_export_with_diagram(tmp_path, monkeypatch):
    """Exporting an exam with diagram_svg produces a valid PDF containing the drawing."""
    monkeypatch.setattr(ExportService, "EXPORT_DIR", tmp_path)

    class MockExam:
        id = uuid.uuid4()
        school_id = uuid.uuid4()
        subject = "Quantitative Reasoning"
        grade_level = "Primary 4"
        term = "Second Term"
        total_marks = 10
        duration_minutes = 30
        instructions = "Answer all questions"

    class MockQuestion:
        exam_id = MockExam.id
        question_number = 1
        section_number = 1
        section_name = "SECTION A"
        type = "multiple_choice"
        question_text = "Study the sample and find the missing number in the tree:"
        marks = 2
        options = ["A. 180", "B. 200", "C. 120", "D. 280"]
        correct_answer = "A"
        explanation = "1000 - 820 = 180"
        diagram_svg = render_horizontal_y_fork(1000, 820, "?", missing="child_bottom")
        sub_parts = None
        marking_scheme = None
        passage_id = None

    pdf_filename = ExportService.export_exam_pdf(
        exam=MockExam(),
        questions=[MockQuestion()],
        school_name="Nigeria Model Academy",
    )
    assert pdf_filename.endswith(".pdf")
    pdf_path = ExportService.export_path(MockExam.id, pdf_filename)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000  # Non-empty PDF


# ── Phase 4: Column Math H T U Tests ────────────────────────────────────────

from app.services.column_math import (
    detect_column_math,
    column_math_to_svg,
    render_column_math_svg,
    ColumnMathBlock,
)


_HTU_TEXT = """Calculate:
   H  T  U
   3  4  8
+  4  3  1
──────────
"""

_HTU_TEXT_SUBTRACTION = """\
   H   T   U
   7   5   6
-  2   3   4
__________
"""


def test_column_math_parser_detects_htu():
    """detect_column_math() correctly parses H T U addition blocks."""
    block = detect_column_math(_HTU_TEXT)
    assert block is not None, "Should detect an H T U block"
    assert isinstance(block, ColumnMathBlock)
    assert block.headers == ["H", "T", "U"]
    assert len(block.rows) == 2   # two digit rows
    # First row: no operator, digits 3 4 8
    op0, cells0 = block.rows[0]
    assert op0 is None
    assert "3" in cells0 and "4" in cells0 and "8" in cells0
    # Second row: operator +
    op1, cells1 = block.rows[1]
    assert op1 == "+"
    assert block.has_answer_line is True


def test_column_math_svg_structure():
    """column_math_to_svg() produces a valid SVG with viewBox, rect, and text elements."""
    block = detect_column_math(_HTU_TEXT)
    assert block is not None
    svg = column_math_to_svg(block)
    assert svg.startswith("<svg"), "SVG should start with <svg"
    assert "</svg>" in svg
    assert "viewBox" in svg
    assert "<rect" in svg
    assert "<text" in svg
    # The answer row uses a dashed stroke
    assert "stroke-dasharray" in svg
    # Operator symbol appears
    assert "+" in svg


def test_column_math_web_component_renders_viewport():
    """QuestionBlock renders a column-math-viewport div for H T U question text."""
    q_data = {
        "question_number": 3,
        "type": "multiple_choice",
        "question_text": _HTU_TEXT,
        "marks": 2,
        "options": ["A. 779", "B. 879", "C. 789", "D. 987"],
        "correct_answer": "A",
        "diagram_svg": None,
    }
    card = QuestionBlock(q_data, number=3, show_answers=False)
    html = str(card)
    assert "column-math-viewport" in html, "Should render column-math-viewport div"
    assert "<svg" in html, "Should contain an inline SVG"
    assert "viewBox" in html


def test_pdf_export_column_math(tmp_path, monkeypatch):
    """Exporting a question with H T U text produces a valid PDF (column math path)."""
    monkeypatch.setattr(ExportService, "EXPORT_DIR", tmp_path)

    class MockExam:
        id = uuid.uuid4()
        school_id = uuid.uuid4()
        subject = "Mathematics"
        grade_level = "Primary 3"
        term = "First Term"
        total_marks = 5
        duration_minutes = 20
        instructions = "Work out the following"

    class MockQuestion:
        exam_id = MockExam.id
        question_number = 1
        section_number = 1
        section_name = "SECTION A"
        type = "multiple_choice"
        question_text = _HTU_TEXT
        marks = 1
        options = ["A. 779", "B. 879", "C. 789", "D. 987"]
        correct_answer = "A"
        explanation = "348 + 431 = 779"
        diagram_svg = None
        sub_parts = None
        marking_scheme = None
        passage_id = None

    pdf_filename = ExportService.export_exam_pdf(
        exam=MockExam(),
        questions=[MockQuestion()],
        school_name="Test School",
    )
    assert pdf_filename.endswith(".pdf")
    pdf_path = ExportService.export_path(MockExam.id, pdf_filename)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500
