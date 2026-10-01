import pytest

from app.services.diagram_templates import ARCHETYPES_META, render_archetype


@pytest.mark.parametrize("name", ["electric_circuit", "optical_ray", "burette", "liebig_condenser", "biology_cell"])
def test_secondary_diagram_archetypes_are_safe_svg(name):
    svg = render_archetype(name, {"sample_label": "<unsafe>"})
    assert svg.startswith("<svg")
    assert "<script" not in svg.lower()
    assert "&lt;unsafe&gt;" in svg
    assert name in ARCHETYPES_META
