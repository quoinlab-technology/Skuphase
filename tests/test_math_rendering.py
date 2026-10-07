from app.services.math_rendering import extract_display_formulas, formula_to_svg
from app.services.formula_catalog import get_all_formulas, validate_formula_catalog


def test_extract_display_formula_delimiters():
    assert extract_display_formulas(r"Solve $$x^2 + 1 = 0$$ and \\[y=2\\].") == ["x^2 + 1 = 0", "y=2"]


def test_formula_svg_is_escaped_and_self_contained():
    svg = formula_to_svg(chr(120) + " " + chr(92) + "times y < 3")
    assert svg.startswith("<svg")
    assert chr(215) in svg
    assert "&lt;" in svg
    assert "<script" not in svg.lower()


def test_formula_svg_normalises_fraction_and_chemistry_without_markup():
    formula = chr(92) + "frac{-b}{2a} + " + chr(92) + "ce{H2O} " + chr(92) + "rightarrow " + chr(92) + "ce{H2} + " + chr(92) + "ce{O2}"
    svg = formula_to_svg(formula)
    assert "(-b)/(2a)" in svg
    assert "H2O" in svg and chr(8594) in svg
    assert chr(92) + "frac" not in svg and chr(92) + "ce" not in svg


def test_formula_catalog_has_reviewable_metadata():
    assert len(get_all_formulas()) >= 28
    assert validate_formula_catalog() == []
