from app.services.math_rendering import extract_display_formulas, formula_to_svg


def test_extract_display_formula_delimiters():
    assert extract_display_formulas(r"Solve $$x^2 + 1 = 0$$ and \\[y=2\\].") == ["x^2 + 1 = 0", "y=2"]


def test_formula_svg_is_escaped_and_self_contained():
    svg = formula_to_svg(r"x \times y < 3")
    assert svg.startswith("<svg")
    assert "×" in svg
    assert "&lt;" in svg
    assert "<script" not in svg.lower()
