"""Small, deterministic math renderer used by PDF export.

The browser uses KaTeX, while the PDF backend does not assume Node or a
system TeX installation.  This adapter gives both paths one delimiter
contract and produces a readable SVG fallback for display equations.  It is
deliberately conservative: complex TeX is preserved as text rather than
executed or interpreted as markup.
"""

from __future__ import annotations

import html
import re


_DISPLAY_RE = re.compile(r"(?:\$\$(.+?)\$\$|\\\[(.+?)\\\])", re.DOTALL)


def extract_display_formulas(text: str | None) -> list[str]:
    if not text:
        return []
    return [((m.group(1) or m.group(2) or "").strip().rstrip("\\")) for m in _DISPLAY_RE.finditer(str(text))]


def formula_to_svg(formula: str, *, width: int = 640) -> str:
    """Render a safe, self-contained display formula SVG.

    This is a fallback renderer, not a TeX evaluator. Common commands are
    converted to Unicode and the original expression remains legible for
    formulas outside the supported subset.
    """
    value = str(formula or "").strip()
    replacements = {
        r"\times": "×", r"\div": "÷", r"\pm": "±", r"\cdot": "·",
        r"\leq": "≤", r"\geq": "≥", r"\neq": "≠", r"\rightarrow": "→",
        r"\sqrt": "√", r"\infty": "∞",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = re.sub(r"\\(?:text|mathrm|mathbf)\{([^{}]*)\}", r"\1", value)
    value = value.replace("{", "(").replace("}", ")")
    value = re.sub(r"\\[a-zA-Z]+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    escaped = html.escape(value, quote=True)
    estimated = max(180, min(width, 18 + len(value) * 10))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{estimated}" height="44" viewBox="0 0 {estimated} 44" role="img" aria-label="{escaped}">
<rect x="1" y="1" width="{estimated - 2}" height="42" rx="5" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="{estimated / 2:g}" y="29" text-anchor="middle" font-family="Arial, sans-serif" font-size="18">{escaped}</text></svg>'''
