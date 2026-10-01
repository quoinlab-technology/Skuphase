"""Comprehensive test suite for the Visual & Formula Assessment Studio Library."""

import pytest
from app.services.formula_catalog import (
    get_all_formulas,
    get_formulas_by_subject,
    search_formulas,
    get_formula_by_id,
)
from app.services.diagram_catalog import (
    get_all_diagrams,
    get_diagrams_by_subject,
    search_diagrams,
    get_diagram_by_id,
)
from app.services.diagram_templates import render_archetype
from app.services.library_service import LibraryService
from app.schemas.library import DiagramRenderSpec


def test_formula_catalog_structure():
    """Verify formula catalog integrity, subject distribution and field presence."""
    formulas = get_all_formulas()
    assert len(formulas) >= 25, f"Expected at least 25 formulas, got {len(formulas)}"

    subjects = {f.subject for f in formulas}
    assert "Mathematics" in subjects
    assert "Physics" in subjects
    assert "Chemistry" in subjects
    assert "Further Mathematics" in subjects

    for f in formulas:
        assert f.id, "Formula must have an id"
        assert f.name, "Formula must have a name"
        assert f.latex, f"Formula {f.id} missing LaTeX"
        assert f.variables, f"Formula {f.id} missing variables breakdown"
        for v in f.variables:
            assert v.symbol, f"Variable in {f.id} missing symbol"
            assert v.name, f"Variable {v.symbol} in {f.id} missing name"


def test_formula_catalog_search():
    """Verify formula query and subject filtering."""
    quadratic = get_formula_by_id("math.quadratic_formula")
    assert quadratic is not None
    assert "4ac" in quadratic.latex

    physics_list = get_formulas_by_subject("Physics")
    assert len(physics_list) >= 6
    for p in physics_list:
        assert p.subject == "Physics"

    search_res = search_formulas("suvat")
    assert len(search_res) >= 1
    assert any("suvat" in f.id for f in search_res)


def test_diagram_catalog_structure():
    """Verify diagram catalog integrity across all 5 curriculum subjects."""
    diagrams = get_all_diagrams()
    assert len(diagrams) == 32, f"Expected 32 diagrams, got {len(diagrams)}"

    subjects = {d.subject for d in diagrams}
    assert "Mathematics" in subjects
    assert "Physics" in subjects
    assert "Chemistry" in subjects
    assert "Biology" in subjects
    assert "Agricultural Science" in subjects

    for d in diagrams:
        assert d.id.startswith(("math.", "physics.", "phys.", "chem.", "bio.", "biology.", "agric.", "agriculture."))
        assert d.title, f"Diagram {d.id} missing title"
        assert d.renderer, f"Diagram {d.id} missing renderer key"
        assert d.topics, f"Diagram {d.id} missing curriculum topics"


def test_callout_masking_behavior():
    """Assert hidden labels are replaced with callout badges in exam mode and preserved in study mode."""
    # 1. Biology Cell
    spec_study = DiagramRenderSpec(mode="study")
    res_study = LibraryService.render_diagram("bio.cell", spec_study)
    assert "Nucleus" in res_study.svg
    assert "Cell Wall" in res_study.svg
    assert ">I<" not in res_study.svg

    spec_exam = DiagramRenderSpec(
        mode="exam",
        hidden_parts=["nucleus", "cell_wall"],
        callout_style="roman",
    )
    res_exam = LibraryService.render_diagram("bio.cell", spec_exam)
    assert ">I<" in res_exam.svg
    assert ">II<" in res_exam.svg
    assert len(res_exam.marking_points) == 2
    assert "Part I: Nucleus" in res_exam.marking_points[0]
    assert "Part II: Cell Wall" in res_exam.marking_points[1]

    # 2. Physics Electric Circuit
    res_ckt_exam = LibraryService.render_diagram(
        "physics.electric_circuit",
        DiagramRenderSpec(mode="exam", hidden_parts=["resistor", "battery"], callout_style="alpha")
    )
    assert ">A<" in res_ckt_exam.svg
    assert ">B<" in res_ckt_exam.svg
    assert "Part A:" in res_ckt_exam.marking_points[0]

    # 3. Agriculture Wheelbarrow
    res_wb_exam = LibraryService.render_diagram(
        "agric.wheelbarrow",
        DiagramRenderSpec(mode="exam", hidden_parts=["wheel", "handles"], callout_style="numeric")
    )
    assert ">1<" in res_wb_exam.svg
    assert "Part 1:" in res_wb_exam.marking_points[0]
    assert "wheel" in res_wb_exam.marking_points[0].lower()


def test_strict_parameter_validation():
    """Verify unknown parameters are rejected/filtered and defaults are populated."""
    spec = DiagramRenderSpec(
        mode="study",
        params={"cell_type": "Custom Plant Specimen", "evil_injected_key": "DROP TABLE exams"}
    )
    res = LibraryService.render_diagram("bio.cell", spec)
    assert "Custom Plant Specimen" in res.svg
    assert "evil_injected_key" not in res.svg
    assert "DROP TABLE exams" not in res.svg


def test_unknown_hidden_parts_are_rejected():
    with pytest.raises(ValueError, match="Unknown hideable part"):
        LibraryService.render_diagram(
            "bio.cell",
            DiagramRenderSpec(mode="exam", hidden_parts=["not_a_real_part"]),
        )


def test_diagram_rendering_all_templates():
    """Ensure every single registered diagram renders safely in both study and exam modes."""
    diagrams = get_all_diagrams()

    for d in diagrams:
        # Study mode
        spec_study = DiagramRenderSpec(mode="study")
        res_study = LibraryService.render_diagram(d.id, spec_study)
        assert res_study.svg.startswith("<svg"), f"{d.id} study mode failed"
        assert "</svg>" in res_study.svg

        # Exam mode with callout styles
        for style in ["roman", "alpha", "numeric", "question_mark"]:
            hidden = [p.key for p in d.hideable_parts]
            spec_exam = DiagramRenderSpec(
                mode="exam",
                hidden_parts=hidden,
                callout_style=style,
            )
            res_exam = LibraryService.render_diagram(d.id, spec_exam)
            assert res_exam.svg.startswith("<svg"), f"{d.id} exam mode failed ({style})"
            assert "</svg>" in res_exam.svg

            if d.hideable_parts:
                assert len(res_exam.marking_points) == len(d.hideable_parts)
                assert "mark" in res_exam.marking_points[0].lower()


def test_svg_sanitization_security():
    """Ensure malicious injection inside diagram fields is sanitized."""
    spec = DiagramRenderSpec(
        mode="study",
        params={"parent": '<script>alert("pwned")</script>', "battery": '"><img src=x onerror=alert(1)>'},
    )
    res = LibraryService.render_diagram("math.horizontal_y_fork", spec)
    assert "<script>" not in res.svg
    assert "onerror=" not in res.svg


def test_composer_dom_structure():
    """Verify that FastHTML renders the Formula Ribbon and Diagram Modal in the composer."""
    from fasthtml.common import to_xml
    from starlette.requests import Request
    from app.frontend.routes.exams import _manual_exam_composer

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/app/exams/new/manual",
        "headers": [],
        "session": {"user": {"id": "test", "account_type": "individual_teacher"}},
    }
    req = Request(scope)

    html = to_xml(_manual_exam_composer(req, ["Mathematics", "Physics"]))
    assert "formula-ribbon-search" in html, "Formula ribbon search input must be present"
    assert "formula-chips-container" in html, "Formula chips container must be present"
    assert "diagram-library-modal" in html, "Diagram library modal must be present in DOM"
    assert "diag-items-list" in html, "Diagram items catalog list must be present"
    assert "btn-insert-diag-and-marking" in html, "Insert Diagram + Append Marking button must be present"
    assert "CATALOG_DIAGRAMS" in html, "Embedded diagram catalog JSON must be present in JS script"
    assert "CATALOG_FORMULAS" in html, "Embedded formula catalog JSON must be present in JS script"
