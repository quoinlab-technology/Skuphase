"""Deterministic, safe math fallback used by server-side document exports."""
from __future__ import annotations

import html
import re

_DISPLAY_RE = re.compile(r"(?:\$\$(.+?)\$\$|\\\[(.+?)\\\])", re.DOTALL)
_CHEM_RE = re.compile(r"\\ce\{([^{}]*)\}")
_MATRIX_RE = re.compile(
    r"\\begin\{(?P<kind>[pbBvV]?matrix)\}(?P<body>.*?)\\end\{(?P=kind)\}",
    re.DOTALL,
)


def split_matrix_expressions(text: str | None) -> list[tuple[str, str]]:
    """Split text into plain-text and LaTeX matrix segments.

    Matrix segments are returned as ("matrix", latex); other segments use
    ("text", value). Keeping this parser small and strict means arbitrary
    LaTeX is never passed through as SVG/XML.
    """
    value = str(text or "")
    segments: list[tuple[str, str]] = []
    cursor = 0
    for match in _MATRIX_RE.finditer(value):
        if match.start() > cursor:
            segments.append(("text", value[cursor:match.start()]))
        segments.append(("matrix", match.group(0)))
        cursor = match.end()
    if cursor < len(value):
        segments.append(("text", value[cursor:]))
    return segments or [("text", value)]


def extract_display_formulas(text: str | None) -> list[str]:
    if not text:
        return []
    return [((m.group(1) or m.group(2) or "").strip().rstrip("\\")) for m in _DISPLAY_RE.finditer(str(text))]


def _readable_formula(formula: str) -> str:
    value = _CHEM_RE.sub(lambda m: m.group(1), str(formula or "").strip())
    replacements = {
        r"\times": "\u00d7", r"\div": "\u00f7", r"\pm": "\u00b1", r"\cdot": "\u00b7",
        r"\leq": "\u2264", r"\geq": "\u2265", r"\neq": "\u2260", r"\rightarrow": "\u2192",
        r"\to": "\u2192", r"\sqrt": "\u221a", r"\infty": "\u221e",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", value)
    value = re.sub(r"\\(?:text|mathrm|mathbf)\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\^\{([^{}]*)\}", r"^\1", value)
    value = re.sub(r"_\{([^{}]*)\}", r"_\1", value)
    value = value.replace("{", "(").replace("}", ")")
    value = re.sub(r"\\[a-zA-Z]+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def formula_to_svg(formula: str, *, width: int = 640) -> str:
    matrix = _MATRIX_RE.search(str(formula or ""))
    if matrix:
        rows = [
            [cell.strip() for cell in row.split("&")]
            for row in re.split(r"\\\\", matrix.group("body").strip().strip("\\"))
        ]
        if rows and all(rows) and len(rows) <= 8 and max(map(len, rows)) <= 8:
            columns = max(map(len, rows))
            cell_w, cell_h = 54, 34
            content_w, content_h = columns * cell_w, len(rows) * cell_h
            pad_x, pad_y = 26, 12
            svg_w, svg_h = content_w + 2 * pad_x, content_h + 2 * pad_y
            kind = matrix.group("kind")
            left, right = {
                "pmatrix": ("(", ")"), "bmatrix": ("[", "]"),
                "Bmatrix": ("{", "}"), "vmatrix": ("|", "|"),
                "Vmatrix": ("‖", "‖"), "matrix": ("", ""),
            }[kind]
            cells = []
            for row_idx, row in enumerate(rows):
                for col_idx, cell in enumerate(row):
                    x = pad_x + col_idx * cell_w + cell_w / 2
                    y = pad_y + row_idx * cell_h + cell_h / 2 + 6
                    cells.append(
                        f'<text x="{x}" y="{y}" text-anchor="middle" '
                        f'font-family="Arial, sans-serif" font-size="18">{html.escape(_readable_formula(cell), quote=True)}</text>'
                    )
            left_x = pad_x - 8
            right_x = pad_x + content_w + 8
            top_y, bottom_y = pad_y, pad_y + content_h
            mid_y = (top_y + bottom_y) / 2
            bracket_markup = ""
            if kind == "pmatrix":
                bracket_markup = (
                    f'<path d="M {left_x + 6} {top_y} C {left_x - 3} {top_y}, {left_x - 3} {mid_y}, {left_x + 6} {mid_y} '
                    f'C {left_x - 3} {mid_y}, {left_x - 3} {bottom_y}, {left_x + 6} {bottom_y} '
                    f'M {right_x - 6} {top_y} C {right_x + 3} {top_y}, {right_x + 3} {mid_y}, {right_x - 6} {mid_y} '
                    f'C {right_x + 3} {mid_y}, {right_x + 3} {bottom_y}, {right_x - 6} {bottom_y}" '
                    'fill="none" stroke="#111827" stroke-width="2"/>'
                )
            elif kind == "bmatrix":
                bracket_markup = (
                    f'<path d="M {left_x + 5} {top_y} H {left_x} V {bottom_y} H {left_x + 5} '
                    f'M {right_x - 5} {top_y} H {right_x} V {bottom_y} H {right_x - 5}" '
                    'fill="none" stroke="#111827" stroke-width="2"/>'
                )
            elif kind == "Bmatrix":
                bracket_markup = (
                    f'<path d="M {left_x + 7} {top_y} C {left_x - 2} {top_y}, {left_x + 4} {mid_y - 5}, {left_x - 2} {mid_y} '
                    f'C {left_x + 4} {mid_y + 5}, {left_x - 2} {bottom_y}, {left_x + 7} {bottom_y} '
                    f'M {right_x - 7} {top_y} C {right_x + 2} {top_y}, {right_x - 4} {mid_y - 5}, {right_x + 2} {mid_y} '
                    f'C {right_x - 4} {mid_y + 5}, {right_x + 2} {bottom_y}, {right_x - 7} {bottom_y}" '
                    'fill="none" stroke="#111827" stroke-width="2"/>'
                )
            elif kind in ("vmatrix", "Vmatrix"):
                if kind == "Vmatrix":
                    bracket_markup = (
                        f'<path d="M {left_x - 5} {top_y} V {bottom_y} M {left_x} {top_y} V {bottom_y} '
                        f'M {right_x} {top_y} V {bottom_y} M {right_x + 5} {top_y} V {bottom_y}" '
                        'fill="none" stroke="#111827" stroke-width="2"/>'
                    )
                else:
                    bracket_markup = (
                        f'<path d="M {left_x} {top_y} V {bottom_y} M {right_x} {top_y} V {bottom_y}" '
                        'fill="none" stroke="#111827" stroke-width="2"/>'
                    )
            aria = html.escape(
                "matrix: " + "; ".join(" , ".join(row) for row in rows),
                quote=True,
            )
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
                f'viewBox="0 0 {svg_w} {svg_h}" role="img" aria-label="{aria}">'
                f'{bracket_markup}{"".join(cells)}</svg>'
            )

    value = _readable_formula(formula)
    escaped = html.escape(value, quote=True)
    estimated = max(180, min(width, 18 + len(value) * 10))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{estimated}" height="44" viewBox="0 0 {estimated} 44" role="img" aria-label="{escaped}">
<rect x="1" y="1" width="{estimated - 2}" height="42" rx="5" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="{estimated / 2:g}" y="29" text-anchor="middle" font-family="Arial, sans-serif" font-size="18">{escaped}</text></svg>'''
