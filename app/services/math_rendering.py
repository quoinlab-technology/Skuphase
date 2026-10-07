"""Deterministic, safe math fallback used by server-side document exports."""
from __future__ import annotations

import html
import re

_DISPLAY_RE = re.compile(r"(?:\$\$(.+?)\$\$|\\\[(.+?)\\\])", re.DOTALL)
_CHEM_RE = re.compile(r"\\ce\{([^{}]*)\}")


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
    value = _readable_formula(formula)
    escaped = html.escape(value, quote=True)
    estimated = max(180, min(width, 18 + len(value) * 10))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{estimated}" height="44" viewBox="0 0 {estimated} 44" role="img" aria-label="{escaped}">
<rect x="1" y="1" width="{estimated - 2}" height="42" rx="5" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="{estimated / 2:g}" y="29" text-anchor="middle" font-family="Arial, sans-serif" font-size="18">{escaped}</text></svg>'''
