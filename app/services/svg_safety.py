"""Strict SVG sanitation for question diagrams.

Question diagrams cross several trust boundaries (teacher input, question-bank
imports, generated content, browser preview, and PDF export).  Store only a
sanitised SVG document, never the Faststrap ``Svg`` wrapper HTML.
"""

from __future__ import annotations

import re

from faststrap import render_svg

_SVG_DOCUMENT = re.compile(r"^\s*<svg\b[^>]*>.*</svg>\s*$", re.IGNORECASE | re.DOTALL)
_UNSAFE_SVG = re.compile(
    r"<\s*(?:script|style|foreignobject|iframe|object|embed)\b|\bon[a-z]+\s*=|\b(?:href|xlink:href)\s*=\s*['\"]?\s*(?:https?:|data:|javascript:)",
    re.IGNORECASE,
)
_STYLE_ATTR = re.compile(r"\s+style\s*=\s*(['\"]).*?\1", re.IGNORECASE | re.DOTALL)


def sanitize_svg(svg: str | None) -> str | None:
    """Return one safe SVG document or ``None`` when the input is invalid.

    ``render_svg`` provides Faststrap's maintained allow-list.  The explicit
    document and unsafe-token checks ensure that a HTML wrapper or a remote
    resource cannot be persisted as a diagram.
    """
    if (
        not isinstance(svg, str)
        or not svg.strip()
        or not _SVG_DOCUMENT.match(svg)
        or _UNSAFE_SVG.search(svg)
    ):
        return None

    # Inline style is unnecessary for the controlled templates and can carry
    # CSS URLs; remove it while retaining safe geometry/text attributes.
    cleaned = render_svg(_STYLE_ATTR.sub("", svg.strip()), sanitize=True).strip()
    if not _SVG_DOCUMENT.match(cleaned) or _UNSAFE_SVG.search(cleaned):
        return None
    return cleaned
