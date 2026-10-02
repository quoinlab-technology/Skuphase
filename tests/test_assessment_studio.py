import pytest
from app.schemas.assessment_studio import BlueprintRequest, MathBlock, QuestionDocument, TextBlock
from app.services.blueprint_service import build_blueprint
from app.services.constants_catalog import list_constants

def test_document_blocks_are_structured():
    doc = QuestionDocument(blocks=[TextBlock(text="Solve"), MathBlock(latex=r"x^2=4")])
    assert [b.type for b in doc.blocks] == ["text", "math"]

def test_constants_filter_by_subject():
    assert any(c["id"] == "chem.avogadro" for c in list_constants("Chemistry"))
    assert not any(c["id"] == "chem.avogadro" for c in list_constants("Physics"))


def test_constants_expose_editorial_metadata():
    item = list_constants("Physics")[0]
    assert item["review_status"] == "verified"
    assert item["class_levels"]

def test_blueprint_reports_allocation_and_bloom_warnings():
    req = BlueprintRequest(subject="Physics", grade_level="SSS 1", total_questions=2, total_marks=4, sections=[{"topic":"Motion", "bloom":"application", "questions":2, "marks":4}])
    result = build_blueprint(req)
    assert result.topic_totals == {"Motion": 4}
    assert any("only one Bloom" in w for w in result.warnings)

def test_blueprint_detects_wrong_totals():
    req = BlueprintRequest(subject="Math", grade_level="JSS 3", total_questions=3, total_marks=6, sections=[{"topic":"Algebra", "bloom":"knowledge", "questions":2, "marks":4}])
    result = build_blueprint(req)
    assert len(result.warnings) == 3
