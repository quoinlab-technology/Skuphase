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

# Mermaid diagram sources must start with a known diagram keyword so that
# arbitrary text cannot reach the Mermaid.js renderer.
_MERMAID_STARTS = (
    "graph", "flowchart", "sequencediagram", "classdiagram", "statediagram",
    "statediagram-v2", "erdiagram", "journey", "gantt", "pie", "mindmap",
    "timeline", "xychart-beta", "quadrantchart", "gitgraph",
)
_MERMAID_UNSAFE = re.compile(
    r"<\s*script|javascript:|\bon[a-z]+\s*=", re.IGNORECASE
)

# Generous caps: a question never needs more than a handful of blocks.
_MAX_BLOCKS = 40
_MAX_TEXT_CHARS = 4000
_MAX_LATEX_CHARS = 2000
_MAX_TABLE_ROWS = 30
_MAX_TABLE_COLS = 12
_MAX_TABLE_CELL_CHARS = 300


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


def sanitize_mermaid(diagram: str | None) -> str | None:
    """Return a safe Mermaid diagram source or ``None``.

    Mermaid runs client-side, so the source must not carry HTML/script
    payloads, and it must start with a known diagram keyword to keep
    arbitrary prose out of the renderer.
    """
    if not isinstance(diagram, str) or not diagram.strip():
        return None
    cleaned = diagram.strip()
    if len(cleaned) > _MAX_TEXT_CHARS or _MERMAID_UNSAFE.search(cleaned):
        return None
    first_token = cleaned.split(None, 1)[0].lower()
    if not any(first_token.startswith(kw) for kw in _MERMAID_STARTS):
        return None
    return cleaned


def sanitize_content_blocks(blocks) -> list | None:
    """Validate LLM/teacher-supplied Faststrap content blocks.

    Allowed block shapes (mirrors ``render_structured_blocks``):

    * ``{"type": "text", "text": str}``
    * ``{"type": "math", "latex": str}``
    * ``{"type": "svg", "svg": str}`` — passed through :func:`sanitize_svg`
    * ``{"type": "table", "rows": [[str, ...], ...]}``
    * ``{"type": "mermaid", "diagram": str}`` — passed through
      :func:`sanitize_mermaid`

    Invalid or unsafe blocks are dropped; ``None`` is returned when nothing
    usable remains so callers can store ``NULL`` cleanly.
    """
    if isinstance(blocks, dict):
        blocks = blocks.get("blocks", [])
    if not isinstance(blocks, list):
        return None

    cleaned: list = []
    for block in blocks[:_MAX_BLOCKS]:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")

        if kind == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                cleaned.append({"type": "text", "text": text[:_MAX_TEXT_CHARS]})

        elif kind == "math":
            latex = block.get("latex")
            if isinstance(latex, str) and latex.strip():
                cleaned.append({"type": "math", "latex": latex[:_MAX_LATEX_CHARS]})

        elif kind == "svg":
            safe_svg = sanitize_svg(block.get("svg"))
            if safe_svg:
                cleaned.append({"type": "svg", "svg": safe_svg})

        elif kind == "table":
            rows = block.get("rows")
            if isinstance(rows, list) and rows:
                safe_rows = []
                for row in rows[:_MAX_TABLE_ROWS]:
                    if not isinstance(row, (list, tuple)):
                        break
                    safe_rows.append(
                        [str(cell)[:_MAX_TABLE_CELL_CHARS] for cell in row[:_MAX_TABLE_COLS]]
                    )
                if safe_rows:
                    cleaned.append({"type": "table", "rows": safe_rows})

        elif kind == "mermaid":
            safe_diagram = sanitize_mermaid(block.get("diagram"))
            if safe_diagram:
                cleaned.append({"type": "mermaid", "diagram": safe_diagram})

    return cleaned or None
