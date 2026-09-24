"""Column arithmetic (place-value) formatter for H T U style exam questions.

Detects the canonical H T U column-math block that appears in primary school
exam papers and notebook exercises, then renders it as an SVG table that can
be embedded directly in the FastStrap web UI (HTML) and piped through
``_svg_to_flowable()`` for PDF (ReportLab).

Supported input patterns (flexible whitespace):
    H  T  U
    3  4  8
 +  4  3  1
 ──────────
or:
    H   T   U
    2   5   6
 -  1   3   2
 __________

The detector also accepts:
    Th  H  T  U   (thousands column)
    TH  H  T  U   (ten-thousands column)
as well as lower-case headers (h t u) or digits-only tables with an operator
row (+ / - / × / ÷) to cover partially-typed AI output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ── Constants ──────────────────────────────────────────────────────────────────
_COL_HEADERS = {"th", "h", "t", "u", "th", "tth"}  # recognisable place-value labels

_OP_SYMBOLS = {"+", "-", "−", "×", "x", "÷", "/"}

_BLOCK_RE = re.compile(
    r"""
    (?:^|\n)                      # start of line
    [ \t]*                        # optional indent
    (?:[Tt][Hh][Hh]|[Tt][Hh]|[Hh]|[Tt][Tt][Hh])?  # optional leading col (Th / TH)
    [ \t]+[Hh][ \t]+[Tt][ \t]+[Uu]  # H T U  (mandatory)
    (?:[ \t]*\n                   # rest of header line
    (?:[ \t]*[-\+\−×÷x]?[ \t]*[\dX_?]+[ \t]*)+  # digit rows
    )*
    """,
    re.VERBOSE | re.MULTILINE,
)

# Simpler fall-back: just look for a line that contains place-value header tokens
_HEADER_RE = re.compile(
    r"^[ \t]*(?:(?:[Tt][Hh][Hh]|[Tt][Hh]|[Tt][Tt][Hh])[ \t]+)?[Hh][ \t]+[Tt][ \t]+[Uu][ \t]*$",
    re.MULTILINE,
)


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class ColumnMathBlock:
    """Parsed representation of a column-arithmetic problem."""
    headers: List[str]          # e.g. ["H", "T", "U"] or ["Th", "H", "T", "U"]
    rows: List[Tuple[Optional[str], List[str]]]  # (operator | None, digit_cells)
    has_answer_line: bool = False


# ── Parser ─────────────────────────────────────────────────────────────────────

def _parse_column_block(raw: str) -> Optional[ColumnMathBlock]:
    """Parse a raw multi-line string into a ``ColumnMathBlock``.

    Returns ``None`` if the text does not look like a column-math problem.
    """
    lines = [ln.rstrip() for ln in raw.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return None

    # ── Find header row ────────────────────────────────────────────────────
    header_idx = None
    for i, ln in enumerate(lines):
        tokens = ln.upper().split()
        if "H" in tokens and "T" in tokens and "U" in tokens:
            header_idx = i
            break
    if header_idx is None:
        return None

    headers = [t.capitalize() for t in lines[header_idx].split()]
    n_cols = len(headers)

    # ── Parse digit rows ───────────────────────────────────────────────────
    rows: List[Tuple[Optional[str], List[str]]] = []
    has_answer_line = False

    for ln in lines[header_idx + 1:]:
        # Separator / answer line (─ ─ ─  or  _ _ _  or  ----)
        if re.match(r"^[ \t]*[─—_\-]{2,}", ln):
            has_answer_line = True
            continue

        tokens = ln.split()
        if not tokens:
            continue

        operator: Optional[str] = None
        digit_tokens: List[str] = []

        if tokens[0] in _OP_SYMBOLS:
            operator = tokens[0]
            digit_tokens = tokens[1:]
        else:
            digit_tokens = tokens

        # Pad / trim to n_cols columns
        while len(digit_tokens) < n_cols:
            digit_tokens.append("")
        digit_tokens = digit_tokens[:n_cols]

        rows.append((operator, digit_tokens))

    if not rows:
        return None

    return ColumnMathBlock(headers=headers, rows=rows, has_answer_line=has_answer_line)


# ── SVG renderer ───────────────────────────────────────────────────────────────

_CELL_W = 36          # pixels per column cell
_CELL_H = 30          # pixels per row
_OP_COL_W = 24        # extra left column for operator symbol
_PAD_X = 8            # horizontal inner padding
_PAD_TOP = 10         # top/bottom padding


def column_math_to_svg(block: ColumnMathBlock) -> str:
    """Render a ``ColumnMathBlock`` as a self-contained inline SVG string.

    The SVG uses absolute coordinates, a ``viewBox``, and monospace digits for
    clean alignment.  The final row after the separator line is left blank (an
    answer placeholder shown with a dashed border).
    """
    n_cols = len(block.headers)
    n_rows = len(block.rows) + 1  # +1 for the header row

    has_answer_row = block.has_answer_line  # show blank answer row at bottom

    if has_answer_row:
        n_rows += 1  # answer row

    total_w = _OP_COL_W + n_cols * _CELL_W + _PAD_X * 2
    total_h = n_rows * _CELL_H + _PAD_TOP * 2

    # Colour palette
    header_fill = "#e8f4fd"
    op_fill = "#fef9e7"
    ans_fill = "#fff9db"
    border = "#555"
    font = "Courier New, Courier, monospace"
    font_size = 14

    lines: List[str] = []

    def rect(x, y, w, h, fill, stroke=border, sw=1.2, rx=2):
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>'
        )

    def text(x, y, content, bold=False, color="#222", anchor="middle"):
        weight = "bold" if bold else "normal"
        return (
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-family="{font}" font-size="{font_size}" '
            f'font-weight="{weight}" fill="{color}">{content}</text>'
        )

    # ── SVG open ──────────────────────────────────────────────────────────
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_w} {total_h}" '
        f'width="{total_w}" height="{total_h}" '
        f'style="font-family:{font}; max-width:100%;">'
    )

    # ── Background ────────────────────────────────────────────────────────
    lines.append(f'<rect width="{total_w}" height="{total_h}" fill="#fafafa" rx="4"/>')

    origin_x = _PAD_X + _OP_COL_W
    origin_y = _PAD_TOP

    # ── Header row ────────────────────────────────────────────────────────
    row_y = origin_y
    for ci, hdr in enumerate(block.headers):
        cx = origin_x + ci * _CELL_W
        lines.append(rect(cx, row_y, _CELL_W, _CELL_H, header_fill))
        lines.append(text(cx + _CELL_W // 2, row_y + _CELL_H - 8, hdr, bold=True))

    row_y += _CELL_H

    # ── Digit rows ────────────────────────────────────────────────────────
    for ri, (op, cells) in enumerate(block.rows):
        is_last_digit_row = ri == len(block.rows) - 1

        # Operator column
        op_x = _PAD_X
        op_fill_c = op_fill if op else "#fafafa"
        lines.append(rect(op_x, row_y, _OP_COL_W, _CELL_H, op_fill_c))
        if op:
            lines.append(text(op_x + _OP_COL_W // 2, row_y + _CELL_H - 8, op, bold=True, color="#c0392b"))

        # Digit cells
        for ci, cell in enumerate(cells):
            cx = origin_x + ci * _CELL_W
            lines.append(rect(cx, row_y, _CELL_W, _CELL_H, "#fff"))
            if cell.strip():
                lines.append(text(cx + _CELL_W // 2, row_y + _CELL_H - 8, cell.strip()))

        # Draw separator line after last digit row (before answer row)
        if is_last_digit_row and has_answer_row:
            sep_y = row_y + _CELL_H
            lines.append(
                f'<line x1="{_PAD_X}" y1="{sep_y}" '
                f'x2="{origin_x + n_cols * _CELL_W}" y2="{sep_y}" '
                f'stroke="{border}" stroke-width="2"/>'
            )

        row_y += _CELL_H

    # ── Answer row (blank, dashed fill) ───────────────────────────────────
    if has_answer_row:
        lines.append(rect(_PAD_X, row_y, _OP_COL_W, _CELL_H, "#fafafa"))
        for ci in range(n_cols):
            cx = origin_x + ci * _CELL_W
            lines.append(
                f'<rect x="{cx}" y="{row_y}" width="{_CELL_W}" height="{_CELL_H}" '
                f'fill="{ans_fill}" stroke="{border}" stroke-width="1.2" '
                f'stroke-dasharray="4 2" rx="2"/>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_column_math(text: str) -> Optional[ColumnMathBlock]:
    """Return a parsed ``ColumnMathBlock`` if *text* contains a H T U block, else ``None``."""
    if not text:
        return None
    if not _HEADER_RE.search(text):
        return None
    # Find the first matching multi-line block starting from the header line
    match = _HEADER_RE.search(text)
    if match is None:
        return None
    # Grab from a few lines before through the end (or next blank block)
    start = max(0, text.rfind("\n", 0, match.start()) + 1)
    snippet = text[start:]
    return _parse_column_block(snippet)


def render_column_math_svg(text: str) -> Optional[str]:
    """High-level helper: detect + render column-math in *text* as SVG string.

    Returns ``None`` if no column-math block is found.
    """
    block = detect_column_math(text)
    if block is None:
        return None
    return column_math_to_svg(block)
