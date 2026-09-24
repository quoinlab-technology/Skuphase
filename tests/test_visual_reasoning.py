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
