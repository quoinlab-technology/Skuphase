"""Tests for Wizard Step 2 Curriculum Weeks selection and validation."""

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.frontend.routes.exams import _clean_topic_title, _get_curriculum_weeks_sync, _wizard_sources
from fasthtml.common import to_xml
from unittest.mock import MagicMock


@pytest.fixture
def client():
    return TestClient(app)


def test_clean_topic_title_formatting():
    """_clean_topic_title must format topics without redundant prefixes or merged words."""
    assert _clean_topic_title("WholeNumbers(Part1)") == "Whole Numbers (Part 1)"
    assert _clean_topic_title("Fractions(Part1)") == "Fractions (Part 1)"
    assert _clean_topic_title("Week 1: Whole Numbers") == "Whole Numbers"
    assert _clean_topic_title("Week 2 - Fractions") == "Fractions"
    assert _clean_topic_title("Multiplication(Part2)") == "Multiplication (Part 2)"


def test_curriculum_cache_returns_real_topics():
    """_get_curriculum_weeks_sync must return real NERDC topics for Primary 4 Mathematics."""
    wiz = {
        "grade_level": "Primary 4",
        "subject": "Mathematics",
        "term": "First Term",
    }
    weeks = _get_curriculum_weeks_sync(wiz)
    # The wizard intentionally exposes teaching weeks only; revision, exam,
    # and break rows are excluded from the selectable scope.
    assert len(weeks) >= 8
    assert all(not week.get("is_exam_or_break") for week in weeks)
    topics = [w["topic"] for w in weeks]
    # Must NOT contain the old generic text
    assert not any("Core Topics & Skills" in t for t in topics)
    # Must contain real topics
    assert any("Whole Numbers" in t for t in topics)
    assert any("Fractions" in t for t in topics)


def test_wizard_sources_renders_real_topics():
    """_wizard_sources must render the real curriculum topics in the HTML."""
    req = MagicMock()
    req.session = {
        "wizard": {
            "grade_level": "Primary 4",
            "subject": "Mathematics",
            "term": "First Term",
        }
    }
    div = _wizard_sources(req)
    html = to_xml(div)
    assert "Whole Numbers (Part 1)" in html
    assert "Fractions (Part 1)" in html
    assert "Core Topics & Skills" not in html
    assert "week-validation-msg" in html


def test_wizard_sources_empty_weeks_shows_validation():
    """_wizard_sources with empty selected_weeks must display the validation warning."""
    req = MagicMock()
    req.session = {
        "wizard": {
            "grade_level": "Primary 4",
            "subject": "Mathematics",
            "term": "First Term",
            "selected_weeks": [],
        }
    }
    div = _wizard_sources(req)
    html = to_xml(div)
    assert 'id="week-validation-msg" style="display:flex;' in html


def test_build_sections_marks_calculation():
    """_build_sections_from_form must accurately compute marks and marks_per_question."""
    from app.frontend.routes.exams import _build_sections_from_form
    form = {
        "section_1_title": "Section A: Objectives",
        "section_1_qtype": "multiple_choice",
        "section_1_num": "20",
        "section_1_marks_per_q": "1",
        "section_1_marks": "20",
        "section_2_title": "Section B: Theory",
        "section_2_qtype": "short_answer",
        "section_2_num": "4",
        "section_2_marks_per_q": "10",
        "section_2_marks": "40",
    }
    secs = _build_sections_from_form(form)
    assert len(secs) == 2
    assert secs[0]["num_questions"] == 20
    assert secs[0]["marks"] == 20
    assert secs[0]["marks_per_question"] == 1
    assert secs[1]["num_questions"] == 4
    assert secs[1]["marks"] == 40
    assert secs[1]["marks_per_question"] == 10


def test_wizard_confirm_marks_calculation():
    """Step 4 confirm screen must not explode marks with duplicate multiplication."""
    from app.frontend.routes.exams import _wizard_confirm
    req = MagicMock()
    req.session = {
        "wizard": {
            "grade_level": "Primary 4",
            "subject": "Mathematics",
            "term": "First Term",
            "total_marks": "60",
            "sections": [
                {"section_number": 1, "section_title": "Section A: Objectives", "question_type": "multiple_choice", "num_questions": 20, "marks": 20, "marks_per_question": 1},
                {"section_number": 2, "section_title": "Section B: Theory", "question_type": "short_answer", "num_questions": 4, "marks": 40, "marks_per_question": 10},
            ],
        }
    }
    div = _wizard_confirm(req)
    html = to_xml(div)
    assert "20 Qs · 20 marks" in html
    assert "4 Qs · 40 marks" in html
    assert "400 marks" not in html
    assert "160 marks" not in html
