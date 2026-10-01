"""Standardized SVG Diagram Templates for Quantitative & Visual Reasoning.

Covers Nigerian Primary & Junior Secondary curriculum archetypes:
  A1. Horizontal Y-Fork: Circle parent branching to two boxes (img_2, img_6)
  A2. Fraction Branch Tree: Two fraction boxes branching to sum box (img_2, img_3)
  B.   M-Shape Network: 5-node M-path cross-relationship (img_2, img_4)
  C.   Power-Circle + Box + Fork: Base^exp -> middle box -> 2 forks (img_2, img_5)
  D.   4-Way Compass Cross: Center hub with 4 arms and operators (img_1)
  E1.  Horseshoe (U-Shape): Top-left, top-right, bottom trough (img_1)
  E2.  Arc (C-Shape): Top node, bottom node, inner value box (img_1)
  F.   2x2 Grid with Ear Bubble: 4 cells with result ear on the right (img_1)
  G.   T-Bar Multiplier: 2 top boxes on a beam hanging down to product box (img_1)
  H.   Triangle Puzzle: Triangle with 3 vertex numbers and center value (WA0063)
"""

from __future__ import annotations
import html
from typing import Tuple, List, Optional


def _esc(val: str | int | float | None) -> str:
    """Safely escape and format slot values."""
    if val is None or str(val).strip() in ("", "?", "[]", "[ ]", "box"):
        return ""
    return html.escape(str(val).strip())


def _is_missing(val: str | int | float | None, slot_name: str, target: str, callouts: Optional[dict[str, str]] = None) -> bool:
    """Return True if this node is the missing question target or a callout."""
    if callouts and slot_name in callouts:
        return True
    if slot_name == target:
        return True
    s = str(val or "").strip()
    return s in ("?", "[]", "[ ]", "")


def _slot_val(val: str | int | float | None, slot_name: str, target: str, callouts: Optional[dict[str, str]] = None) -> tuple[str, bool]:
    """Return (display_text, is_highlighted) taking callouts into account."""
    if callouts and slot_name in callouts:
        return (str(callouts[slot_name]), True)
    if slot_name == target or str(val or "").strip() in ("?", "[]", "[ ]", ""):
        return ("?", True)
    return (_esc(val), False)


def _callout_label(
    part_key: str,
    default_text: str,
    callouts: Optional[dict[str, str]],
    x: int | str,
    y: int | str,
    font_size: int = 13,
    anchor: str = "middle",
    fill: str = "#1e293b",
    font_weight: str = "bold",
) -> str:
    """Return an SVG text element (or highlighted badge group) for a label slot.

    When `part_key` is in `callouts`, renders a yellow pill-badge around the
    callout symbol so hidden parts are visually distinct in exam mode.
    Otherwise renders a plain <text> element with the given fill color.
    """
    if callouts and part_key in callouts:
        sym = html.escape(str(callouts[part_key]))
        sym_w = max(22, len(sym) * 10 + 12)
        rx_val = sym_w // 2
        x_val = int(x) if str(x).lstrip('-').isdigit() else 0
        y_val = int(y) if str(y).lstrip('-').isdigit() else 0
        rect_x = x_val - rx_val
        rect_y = y_val - font_size - 2
        rect_h = font_size + 8
        return (
            f'<rect x="{rect_x}" y="{rect_y}" width="{sym_w}" height="{rect_h}" '
            f'rx="4" fill="#fef08a" stroke="#ca8a04" stroke-width="1.5"/>'
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-family="Arial" font-size="{font_size}" font-weight="bold" '
            f'fill="#92400e">{sym}</text>'
        )
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-family="Arial" font-size="{font_size}" font-weight="{font_weight}" '
        f'fill="{fill}">{html.escape(str(default_text))}</text>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Archetype A1: Horizontal Y-Fork (Circle -> 2 Rectangles)
# ─────────────────────────────────────────────────────────────────────────────

def render_horizontal_y_fork(
    parent: str | int,
    child_top: str | int,
    child_bottom: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: Optional[dict[str, str]] = None,
) -> str:
    """Render horizontal Y-fork: Circle on left branching right to 2 boxes."""
    p_txt, p_miss = _slot_val(parent, "parent", missing, _callouts)
    ct_txt, ct_miss = _slot_val(child_top, "child_top", missing, _callouts)
    cb_txt, cb_miss = _slot_val(child_bottom, "child_bottom", missing, _callouts)

    badge = f'<text x="10" y="20" font-size="12" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="220" height="120" viewBox="0 0 220 120" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Connector lines -->
  <line x1="72" y1="60" x2="135" y2="35" stroke="#222" stroke-width="2.5" />
  <line x1="72" y1="60" x2="135" y2="85" stroke="#222" stroke-width="2.5" />

  <!-- Parent Node (Circle) -->
  <circle cx="48" cy="60" r="26" stroke="#222" stroke-width="2.5" fill="{"#fff9db" if p_miss else "#ffffff"}" />
  <text x="48" y="65" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif" fill="#111">{p_txt}</text>

  <!-- Top Child (Box) -->
  <rect x="135" y="18" width="56" height="34" rx="4" stroke="#222" stroke-width="2.5" fill="{"#fff9db" if ct_miss else "#ffffff"}" />
  <text x="163" y="40" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif" fill="#111">{ct_txt}</text>

  <!-- Bottom Child (Box) -->
  <rect x="135" y="68" width="56" height="34" rx="4" stroke="#222" stroke-width="2.5" fill="{"#fff9db" if cb_miss else "#ffffff"}" />
  <text x="163" y="90" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif" fill="#111">{cb_txt}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype A2: Fraction Branch Tree (2 Top Fraction Boxes -> Bottom Fraction Box)
# ─────────────────────────────────────────────────────────────────────────────

def render_fraction_branch(
    frac_left: Tuple[str | int, str | int],
    frac_right: Tuple[str | int, str | int],
    frac_bottom: Tuple[str | int, str | int],
    missing: str = "",
    sample_label: str = "",
    _callouts: Optional[dict[str, str]] = None,
) -> str:
    """Render two top fraction boxes joining into a bottom fraction box."""
    nl_txt, nl_miss = _slot_val(frac_left[0], "frac_left_num", missing, _callouts)
    dl_txt, dl_miss = _slot_val(frac_left[1], "frac_left_den", missing, _callouts)
    nr_txt, nr_miss = _slot_val(frac_right[0], "frac_right_num", missing, _callouts)
    dr_txt, dr_miss = _slot_val(frac_right[1], "frac_right_den", missing, _callouts)
    nb_txt, nb_miss = _slot_val(frac_bottom[0], "frac_bottom_num", missing, _callouts)
    db_txt, db_miss = _slot_val(frac_bottom[1], "frac_bottom_den", missing, _callouts)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="220" height="150" viewBox="0 0 220 150" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Connector lines -->
  <line x1="58" y1="65" x2="110" y2="86" stroke="#222" stroke-width="2" />
  <line x1="162" y1="65" x2="110" y2="86" stroke="#222" stroke-width="2" />

  <!-- Left Fraction Box -->
  <rect x="36" y="18" width="44" height="46" rx="4" stroke="#222" stroke-width="2" fill="white" />
  <line x1="38" y1="41" x2="78" y2="41" stroke="#222" stroke-width="1.8" />
  <text x="58" y="35" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{nl_txt}</text>
  <text x="58" y="58" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{dl_txt}</text>

  <!-- Right Fraction Box -->
  <rect x="140" y="18" width="44" height="46" rx="4" stroke="#222" stroke-width="2" fill="white" />
  <line x1="142" y1="41" x2="182" y2="41" stroke="#222" stroke-width="1.8" />
  <text x="162" y="35" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{nr_txt}</text>
  <text x="162" y="58" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{dr_txt}</text>

  <!-- Bottom Fraction Box -->
  <rect x="88" y="86" width="44" height="46" rx="4" stroke="#222" stroke-width="2" fill="white" />
  <line x1="90" y1="109" x2="130" y2="109" stroke="#222" stroke-width="1.8" />
  <text x="110" y="103" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{nb_txt}</text>
  <text x="110" y="126" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{db_txt}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype B: M-Shape / W-Shape Network
# ─────────────────────────────────────────────────────────────────────────────

def render_m_network(
    tl: str | int,
    bl: str | int,
    center: str | int,
    tr: str | int,
    br: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render 5-node M-path: (TL, BL, Center, TR, BR)."""
    tl_m = _is_missing(tl, "tl", missing)
    bl_m = _is_missing(bl, "bl", missing)
    c_m = _is_missing(center, "center", missing)
    tr_m = _is_missing(tr, "tr", missing)
    br_m = _is_missing(br, "br", missing)

    badge = f'<text x="10" y="18" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    def _node(x: int, y: int, val: Any, key: str, is_box: bool = False):
        t, is_hi = _slot_val(val, key, missing, _callouts)
        bg = "#fff9db" if is_hi else "#ffffff"
        if is_box:
            return f'<rect x="{x-18}" y="{y-14}" width="36" height="28" rx="3" stroke="#222" stroke-width="2" fill="{bg}" />' \
                   f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{t}</text>'
        return f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif" fill="#111">{t}</text>'

    return f"""<svg width="220" height="150" viewBox="0 0 220 150" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- M-Path connecting lines -->
  <line x1="45" y1="100" x2="45" y2="40" stroke="#222" stroke-width="2.5" />
  <line x1="45" y1="40" x2="110" y2="78" stroke="#222" stroke-width="2.5" />
  <line x1="110" y1="78" x2="175" y2="40" stroke="#222" stroke-width="2.5" />
  <line x1="175" y1="40" x2="175" y2="100" stroke="#222" stroke-width="2.5" />

  <!-- Nodes -->
  {_node(45, 30, tl, "tl", bool(_callouts and "tl" in _callouts))}
  {_node(45, 115, bl, "bl", bool(_callouts and "bl" in _callouts))}
  {_node(110, 78, center, "center", True)}
  {_node(175, 30, tr, "tr", bool(_callouts and "tr" in _callouts))}
  {_node(175, 115, br, "br", bool(_callouts and "br" in _callouts))}
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype C: Power-Circle + Mid Box + Fork
# ─────────────────────────────────────────────────────────────────────────────

def render_power_fork(
    base: str | int,
    exp: str | int,
    mid_box: str | int,
    fork1: str | int,
    fork2: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render (base^exp) --- [mid_box] < (fork1, fork2)."""
    p_m = _is_missing(base, "base", missing)
    m_m = _is_missing(mid_box, "mid_box", missing)
    f1_m = _is_missing(fork1, "fork1", missing)
    f2_m = _is_missing(fork2, "fork2", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    p_content = f'{_esc(base)}<tspan dy="-6" font-size="10">{_esc(exp)}</tspan>'
    p_t, p_hi = _slot_val(p_content, "base", missing, _callouts)
    m_t, m_hi = _slot_val(mid_box, "mid_box", missing, _callouts)
    f1_t, f1_hi = _slot_val(fork1, "fork1", missing, _callouts)
    f2_t, f2_hi = _slot_val(fork2, "fork2", missing, _callouts)

    return f"""<svg width="250" height="110" viewBox="0 0 250 110" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Connector lines -->
  <line x1="68" y1="55" x2="100" y2="55" stroke="#222" stroke-width="2" />
  <line x1="148" y1="55" x2="195" y2="30" stroke="#222" stroke-width="2" />
  <line x1="148" y1="55" x2="195" y2="80" stroke="#222" stroke-width="2" />

  <!-- Power Circle -->
  <circle cx="44" cy="55" r="24" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if p_hi else "#ffffff"}" />
  <text x="44" y="60" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif">{p_t}</text>

  <!-- Mid Box -->
  <rect x="100" y="38" width="48" height="34" rx="4" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if m_hi else "#ffffff"}" />
  <text x="124" y="60" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif">{m_t}</text>

  <!-- Fork 1 (Top) -->
  <rect x="195" y="15" width="40" height="28" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if f1_hi else "#ffffff"}" />
  <text x="215" y="34" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{f1_t}</text>

  <!-- Fork 2 (Bottom) -->
  <rect x="195" y="68" width="40" height="28" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if f2_hi else "#ffffff"}" />
  <text x="215" y="87" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{f2_t}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype D: 4-Way Compass Cross
# ─────────────────────────────────────────────────────────────────────────────

def render_compass_cross(
    center: str | int,
    top: str | int,
    bottom: str | int,
    left: str | int,
    right: str | int,
    op_top: str = "+",
    op_bot: str = "×",
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render center hub with 4 peripheral arms."""
    c_m = _is_missing(center, "center", missing)
    t_m = _is_missing(top, "top", missing)
    b_m = _is_missing(bottom, "bottom", missing)
    l_m = _is_missing(left, "left", missing)
    r_m = _is_missing(right, "right", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    c_t, c_hi = _slot_val(center, "center", missing, _callouts)
    t_t, t_hi = _slot_val(top, "top", missing, _callouts)
    b_t, b_hi = _slot_val(bottom, "bottom", missing, _callouts)
    l_t, l_hi = _slot_val(left, "left", missing, _callouts)
    r_t, r_hi = _slot_val(right, "right", missing, _callouts)

    return f"""<svg width="200" height="170" viewBox="0 0 200 170" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Cross arm lines -->
  <line x1="100" y1="36" x2="100" y2="134" stroke="#222" stroke-width="2.5" />
  <line x1="36" y1="85" x2="164" y2="85" stroke="#222" stroke-width="2.5" />

  <!-- Center Circle -->
  <circle cx="100" cy="85" r="22" stroke="#222" stroke-width="2.5" fill="{"#fff9db" if c_hi else "#ffffff"}" />
  <text x="100" y="90" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{c_t}</text>

  <!-- Top Box -->
  <rect x="78" y="10" width="44" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if t_hi else "#ffffff"}" />
  <text x="100" y="28" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{t_t}</text>
  <text x="100" y="52" text-anchor="middle" font-size="12" font-weight="bold" fill="#444">{html.escape(op_top)}</text>

  <!-- Bottom Box -->
  <rect x="78" y="134" width="44" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if b_hi else "#ffffff"}" />
  <text x="100" y="152" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{b_t}</text>
  <text x="100" y="125" text-anchor="middle" font-size="12" font-weight="bold" fill="#444">{html.escape(op_bot)}</text>

  <!-- Left Box -->
  <rect x="10" y="72" width="40" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if l_hi else "#ffffff"}" />
  <text x="30" y="90" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{l_t}</text>

  <!-- Right Box -->
  <rect x="150" y="72" width="40" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if r_hi else "#ffffff"}" />
  <text x="170" y="90" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{r_t}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype E: Horseshoe (U-Shape) and Arc (C-Shape)
# ─────────────────────────────────────────────────────────────────────────────

def render_horseshoe(
    left: str | int,
    right: str | int,
    bottom: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render U-shape curve with Left, Right and Bottom trough circles."""
    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    l_t, l_hi = _slot_val(left, "left", missing, _callouts)
    r_t, r_hi = _slot_val(right, "right", missing, _callouts)
    b_t, b_hi = _slot_val(bottom, "bottom", missing, _callouts)

    return f"""<svg width="200" height="130" viewBox="0 0 200 130" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- U-path -->
  <path d="M 45 40 C 45 110, 155 110, 155 40" stroke="#222" stroke-width="3" fill="none" />

  <!-- Left circle -->
  <circle cx="45" cy="40" r="22" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if l_hi else "#ffffff"}" />
  <text x="45" y="45" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{l_t}</text>

  <!-- Right circle -->
  <circle cx="155" cy="40" r="22" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if r_hi else "#ffffff"}" />
  <text x="155" y="45" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{r_t}</text>

  <!-- Bottom trough circle -->
  <circle cx="100" cy="98" r="20" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if b_hi else "#ffffff"}" />
  <text x="100" y="103" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{b_t}</text>
</svg>"""


def render_arc_c(
    top: str | int,
    bottom: str | int,
    inside: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render C-shape curve with Top, Bottom and Inner box."""
    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    t_t, t_hi = _slot_val(top, "top", missing, _callouts)
    b_t, b_hi = _slot_val(bottom, "bottom", missing, _callouts)
    i_t, i_hi = _slot_val(inside, "inside", missing, _callouts)

    return f"""<svg width="180" height="150" viewBox="0 0 180 150" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- C-path -->
  <path d="M 110 35 C 30 35, 30 115, 110 115" stroke="#222" stroke-width="3" fill="none" />

  <!-- Top circle -->
  <circle cx="110" cy="35" r="20" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if t_hi else "#ffffff"}" />
  <text x="110" y="40" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{t_t}</text>

  <!-- Bottom circle -->
  <circle cx="110" cy="115" r="20" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if b_hi else "#ffffff"}" />
  <text x="110" y="120" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{b_t}</text>

  <!-- Inner box -->
  <rect x="42" y="60" width="46" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if i_hi else "#ffffff"}" />
  <text x="65" y="80" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{i_t}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype F: 2x2 Grid with Side "Ear" Bubble
# ─────────────────────────────────────────────────────────────────────────────

def render_grid_with_ear(
    r1c1: str | int,
    r1c2: str | int,
    r2c1: str | int,
    r2c2: str | int,
    ear: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render 2x2 grid with an attached circular result ear on right."""
    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    c11_t, c11_hi = _slot_val(r1c1, "r1c1", missing, _callouts)
    c12_t, c12_hi = _slot_val(r1c2, "r1c2", missing, _callouts)
    c21_t, c21_hi = _slot_val(r2c1, "r2c1", missing, _callouts)
    c22_t, c22_hi = _slot_val(r2c2, "r2c2", missing, _callouts)
    ear_t, ear_hi = _slot_val(ear, "ear", missing, _callouts)

    return f"""<svg width="220" height="130" viewBox="0 0 220 130" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- 2x2 outer box -->
  <rect x="30" y="25" width="90" height="90" stroke="#222" stroke-width="2.5" fill="#ffffff" />
  <!-- Grid dividers -->
  <line x1="75" y1="25" x2="75" y2="115" stroke="#222" stroke-width="2" />
  <line x1="30" y1="70" x2="120" y2="70" stroke="#222" stroke-width="2" />

  <!-- Cells -->
  <text x="52" y="52" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{c11_t}</text>
  <text x="97" y="52" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{c12_t}</text>
  <text x="52" y="97" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{c21_t}</text>
  <text x="97" y="97" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{c22_t}</text>

  <!-- Ear connector -->
  <line x1="120" y1="70" x2="145" y2="70" stroke="#222" stroke-width="2" />

  <!-- Side Ear Bubble -->
  <circle cx="168" cy="70" r="22" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if ear_hi else "#ffffff"}" />
  <text x="168" y="75" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{ear_t}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype G: T-Bar / H-Bar Multiplier
# ─────────────────────────────────────────────────────────────────────────────

def render_t_bar(
    left_top: str | int,
    right_top: str | int,
    bottom: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render two top boxes on a T-bar beam hanging to bottom product box."""
    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    lt_t, lt_hi = _slot_val(left_top, "left_top", missing, _callouts)
    rt_t, rt_hi = _slot_val(right_top, "right_top", missing, _callouts)
    b_t, b_hi = _slot_val(bottom, "bottom", missing, _callouts)

    return f"""<svg width="200" height="140" viewBox="0 0 200 140" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- T-Bar lines -->
  <line x1="58" y1="50" x2="142" y2="50" stroke="#222" stroke-width="2.5" />
  <line x1="100" y1="50" x2="100" y2="92" stroke="#222" stroke-width="2.5" />

  <!-- Left Top Box -->
  <rect x="36" y="20" width="44" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if lt_hi else "#ffffff"}" />
  <text x="58" y="40" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{lt_t}</text>

  <!-- Right Top Box -->
  <rect x="120" y="20" width="44" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if rt_hi else "#ffffff"}" />
  <text x="142" y="40" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{rt_t}</text>

  <!-- Bottom Box -->
  <rect x="78" y="92" width="44" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if b_hi else "#ffffff"}" />
  <text x="100" y="112" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{b_t}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetype H: Triangle Vertex & Center Logic
# ─────────────────────────────────────────────────────────────────────────────

def render_triangle_puzzle(
    top: str | int,
    left: str | int,
    right: str | int,
    center: str | int,
    missing: str = "",
    sample_label: str = "",
    _callouts: dict[str, str] | None = None,
) -> str:
    """Render triangle with numbers at 3 vertices and center value."""
    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    t_t, t_hi = _slot_val(top, "top", missing, _callouts)
    l_t, l_hi = _slot_val(left, "left", missing, _callouts)
    r_t, r_hi = _slot_val(right, "right", missing, _callouts)
    c_t, c_hi = _slot_val(center, "center", missing, _callouts)

    return f"""<svg width="200" height="150" viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Triangle path -->
  <polygon points="100,24 35,124 165,124" stroke="#222" stroke-width="2.5" fill="none" />

  <!-- Top Vertex Circle -->
  <circle cx="100" cy="24" r="18" stroke="#222" stroke-width="2" fill="{"#fff9db" if t_hi else "#ffffff"}" />
  <text x="100" y="29" text-anchor="middle" font-size="12" font-weight="bold" font-family="Arial, sans-serif">{t_t}</text>

  <!-- Left Vertex Circle -->
  <circle cx="35" cy="124" r="18" stroke="#222" stroke-width="2" fill="{"#fff9db" if l_hi else "#ffffff"}" />
  <text x="35" y="129" text-anchor="middle" font-size="12" font-weight="bold" font-family="Arial, sans-serif">{l_t}</text>

  <!-- Right Vertex Circle -->
  <circle cx="165" cy="124" r="18" stroke="#222" stroke-width="2" fill="{"#fff9db" if r_hi else "#ffffff"}" />
  <text x="165" y="129" text-anchor="middle" font-size="12" font-weight="bold" font-family="Arial, sans-serif">{r_t}</text>

  <!-- Center Box/Value -->
  <rect x="80" y="75" width="40" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if c_hi else "#ffffff"}" />
  <text x="100" y="93" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{c_t}</text>
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Archetypes Metadata & Universal Dispatcher for Parametric UI Pickers
# ─────────────────────────────────────────────────────────────────────────────

def _science_svg(body: str, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="300" viewBox="0 0 640 300" role="img" aria-label="{_esc(title)}">
<rect x="1" y="1" width="638" height="298" rx="8" fill="#ffffff" stroke="#334155" stroke-width="2"/>
<text x="320" y="26" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold">{_esc(title)}</text>{body}</svg>'''


def render_electric_circuit(battery="12 V", resistor="R", current="I", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    battery_svg = _callout_label("battery", callouts.get("battery", battery), callouts, 175, 215, anchor="middle")
    resistor_fill = "#fef08a" if (callouts and "resistor" in callouts) else "#eff6ff"
    resistor_svg = _callout_label("resistor", callouts.get("resistor", resistor), callouts, 320, 156, anchor="middle")
    current_svg = _callout_label("meter", callouts.get("meter", current), callouts, 400, 82, anchor="start")
    return _science_svg(f'''<path d="M80 150H145M205 150H290M350 150H560V90H80V150" fill="none" stroke="#111827" stroke-width="3"/>
<line x1="165" y1="126" x2="165" y2="174" stroke="#111827" stroke-width="4"/><line x1="185" y1="116" x2="185" y2="184" stroke="#111827" stroke-width="4"/>
<circle cx="320" cy="150" r="30" fill="{resistor_fill}" stroke="#111827" stroke-width="2"/>
{resistor_svg}
{battery_svg}{current_svg}
<text x="320" y="245" text-anchor="middle" font-family="Arial">{_esc(sample_label or ('?' if missing else 'Series circuit'))}</text>''', "Series Electric Circuit")


def render_optical_ray(object_label="Object", image_label="Image", focal_length="f", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    o_svg = _callout_label("object", callouts.get("object", object_label), callouts, 190, 78, anchor="middle")
    i_svg = _callout_label("image", callouts.get("image", image_label), callouts, 450, 100, anchor="middle")
    l_svg = _callout_label("lens", callouts.get("lens", sample_label or focal_length), callouts, 320, 265, anchor="middle")
    return _science_svg(f'''<line x1="80" y1="150" x2="560" y2="150" stroke="#64748b" stroke-width="2"/><line x1="320" y1="55" x2="320" y2="245" stroke="#111827" stroke-width="4"/>
<path d="M190 150L320 85L450 150" fill="none" stroke="#dc2626" stroke-width="3"/>
<line x1="190" y1="150" x2="190" y2="90" stroke="#2563eb" stroke-width="5"/>
<line x1="450" y1="150" x2="450" y2="110" stroke="#16a34a" stroke-width="5"/>
{o_svg}{i_svg}{l_svg}''', "Optical Ray Diagram")


def render_burette(volume="25.0 mL", titre="Titre", indicator="Indicator", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    b_svg = _callout_label("burette", callouts.get("burette", volume), callouts, 360, 90, anchor="start")
    s_svg = _callout_label("stopcock", callouts.get("stopcock", indicator), callouts, 360, 125, anchor="start")
    f_svg = _callout_label("flask", callouts.get("flask", sample_label or titre), callouts, 320, 290, anchor="middle")
    return _science_svg(f'''<rect x="285" y="48" width="26" height="190" fill="#dbeafe" stroke="#111827" stroke-width="2"/><line x1="298" y1="48" x2="298" y2="238" stroke="#111827"/>
<path d="M298 238V258h-28M298 258h28" fill="none" stroke="#111827" stroke-width="3"/><path d="M245 270h110" stroke="#111827" stroke-width="3"/>
<line x1="311" y1="85" x2="333" y2="85" stroke="#111827"/><line x1="311" y1="120" x2="333" y2="120" stroke="#111827"/><line x1="311" y1="155" x2="333" y2="155" stroke="#111827"/>
{b_svg}{s_svg}{f_svg}''', "Burette Titration Setup")


def render_liebig_condenser(water_in="Water in", water_out="Water out", vapour="Vapour", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    wi_svg = _callout_label("water_in", callouts.get("water_in", water_in), callouts, 80, 105, anchor="middle")
    wo_svg = _callout_label("water_out", callouts.get("water_out", water_out), callouts, 560, 105, anchor="middle")
    vp_svg = _callout_label("vapour", callouts.get("vapour", vapour), callouts, 320, 95, anchor="middle")
    return _science_svg(f'''<rect x="130" y="105" width="380" height="70" rx="34" fill="#fef3c7" stroke="#111827" stroke-width="3"/><path d="M130 120H80v40h50M510 120h50v40h-50" fill="none" stroke="#2563eb" stroke-width="6"/>
<path d="M160 140H480" stroke="#dc2626" stroke-width="4"/>
{wi_svg}{wo_svg}{vp_svg}
<text x="320" y="220" text-anchor="middle" font-family="Arial">{_esc(sample_label or 'Liebig condenser')}</text>''', "Liebig Condenser")


def render_biology_cell(cell_type="Plant cell", nucleus="Nucleus", vacuole="Vacuole", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    cw_svg = _callout_label("cell_wall", callouts.get("cell_wall", "Cell Wall"), callouts, 100, 80, anchor="end", fill="#166534")
    nucleus_svg = _callout_label("nucleus", callouts.get("nucleus", nucleus), callouts, 320, 155, anchor="middle", fill="#fff")
    vacuole_svg = _callout_label("vacuole", callouts.get("vacuole", vacuole), callouts, 320, 215, anchor="middle", fill="#1e40af")
    return _science_svg(f'''<rect x="145" y="55" width="350" height="190" rx="42" fill="#dcfce7" stroke="#166534" stroke-width="6"/><rect x="160" y="70" width="320" height="160" rx="32" fill="#f0fdf4" stroke="#65a30d" stroke-width="2"/><ellipse cx="320" cy="150" rx="65" ry="45" fill="#bfdbfe" stroke="#1d4ed8" stroke-width="2"/><circle cx="320" cy="150" r="18" fill="#1e40af"/>
<line x1="145" y1="75" x2="105" y2="75" stroke="#166534" stroke-width="2"/>
{cw_svg}
{nucleus_svg}{vacuole_svg}
<text x="320" y="35" text-anchor="middle" font-family="Arial" font-weight="bold">{_esc(sample_label or cell_type)}</text>''', "Biology Cell Diagram")


def render_right_triangle(base_label="4 cm", height_label="3 cm", hypotenuse_label="5 cm", angle_theta="θ", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    h_text = callouts.get("hypotenuse", hypotenuse_label)
    b_text = callouts.get("base", base_label)
    ht_text = callouts.get("height", height_label)
    th_text = callouts.get("angle_theta", angle_theta)
    return _science_svg(f'''
<polygon points="120,240 480,240 480,60" fill="#f8fafc" stroke="#1e293b" stroke-width="3"/>
<rect x="456" y="216" width="24" height="24" fill="none" stroke="#1e293b" stroke-width="2"/>
<path d="M160,240 A40,40 0 0,0 152,223" fill="none" stroke="#dc2626" stroke-width="2"/>
<text x="175" y="232" font-family="Arial" font-size="14" fill="#dc2626">{_esc(th_text)}</text>
<text x="300" y="265" text-anchor="middle" font-family="Arial" font-size="15" font-weight="bold">{_esc(b_text)}</text>
<text x="510" y="155" text-anchor="start" font-family="Arial" font-size="15" font-weight="bold">{_esc(ht_text)}</text>
<text x="280" y="140" text-anchor="middle" font-family="Arial" font-size="15" font-weight="bold" fill="#2563eb">{_esc(h_text)}</text>
<text x="320" y="285" text-anchor="middle" font-family="Arial" font-size="12" fill="#64748b">{_esc(sample_label)}</text>
''', "Right-Angled Triangle")


def render_venn_2set(set_a_label="A", set_b_label="B", only_a="12", intersection="5", only_b="8", neither="3", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    a_txt = callouts.get("only_a", only_a)
    ab_txt = callouts.get("intersection", intersection)
    b_txt = callouts.get("only_b", only_b)
    n_txt = callouts.get("neither", neither)
    return _science_svg(f'''
<rect x="80" y="50" width="480" height="210" rx="6" fill="#f8fafc" stroke="#334155" stroke-width="2"/>
<text x="100" y="75" font-family="Arial" font-size="16" font-weight="bold">ξ (Universal Set)</text>
<circle cx="260" cy="155" r="75" fill="#dbeafe" fill-opacity="0.6" stroke="#2563eb" stroke-width="2.5"/>
<circle cx="380" cy="155" r="75" fill="#fef3c7" fill-opacity="0.6" stroke="#d97706" stroke-width="2.5"/>
<text x="230" y="95" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#1d4ed8">{_esc(set_a_label)}</text>
<text x="410" y="95" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#b45309">{_esc(set_b_label)}</text>
<text x="230" y="160" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">{_esc(a_txt)}</text>
<text x="320" y="160" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#b91c1c">{_esc(ab_txt)}</text>
<text x="410" y="160" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">{_esc(b_txt)}</text>
<text x="530" y="240" text-anchor="end" font-family="Arial" font-size="14" fill="#64748b">{_esc(n_txt)}</text>
''', "2-Set Venn Diagram")


def render_pulley_system(load_label="L = 100 N", effort_label="E", system_type="Single Movable", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    l_txt = callouts.get("load", load_label)
    e_txt = callouts.get("effort", effort_label)
    return _science_svg(f'''
<!-- Ceiling support -->
<rect x="220" y="45" width="200" height="8" fill="#475569"/>
<!-- Fixed top pulley -->
<circle cx="320" cy="85" r="28" fill="#e2e8f0" stroke="#1e293b" stroke-width="2.5"/>
<line x1="320" y1="53" x2="320" y2="85" stroke="#1e293b" stroke-width="3"/>
<!-- Movable pulley -->
<circle cx="320" cy="180" r="28" fill="#e2e8f0" stroke="#1e293b" stroke-width="2.5"/>
<!-- Rope lines -->
<line x1="292" y1="85" x2="292" y2="180" stroke="#0f172a" stroke-width="2.5"/>
<line x1="348" y1="85" x2="348" y2="180" stroke="#0f172a" stroke-width="2.5"/>
<!-- Effort rope -->
<line x1="348" y1="85" x2="420" y2="170" stroke="#0f172a" stroke-width="2.5"/>
<line x1="420" y1="170" x2="420" y2="210" stroke="#dc2626" stroke-width="2.5"/>
<polygon points="420,218 415,206 425,206" fill="#dc2626"/>
<text x="435" y="200" font-family="Arial" font-size="14" font-weight="bold" fill="#dc2626">{_esc(e_txt)}</text>
<!-- Hanging Load block -->
<line x1="320" y1="208" x2="320" y2="230" stroke="#1e293b" stroke-width="3"/>
<rect x="285" y="230" width="70" height="38" rx="4" fill="#cbd5e1" stroke="#1e293b" stroke-width="2"/>
<text x="320" y="254" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold">{_esc(l_txt)}</text>
<text x="140" y="85" font-family="Arial" font-size="13" fill="#64748b">{_esc(sample_label or system_type)}</text>
''', "Pulley System")


def render_inclined_plane(angle="30°", mass="W = mg", friction="F_r", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    r_txt = callouts.get("normal_reaction", "R")
    w_txt = callouts.get("parallel_weight", mass)
    f_txt = callouts.get("friction", friction)
    return _science_svg(f'''
<!-- Wedge plane -->
<polygon points="100,240 500,240 500,100" fill="#f1f5f9" stroke="#1e293b" stroke-width="3"/>
<!-- Incline Angle -->
<path d="M150,240 A50,50 0 0,0 144,222" fill="none" stroke="#dc2626" stroke-width="2"/>
<text x="165" y="232" font-family="Arial" font-size="14" fill="#dc2626">{_esc(angle)}</text>
<!-- Mass Block resting on slope -->
<g transform="translate(320, 160) rotate(-19.3)">
  <rect x="-35" y="-25" width="70" height="50" rx="3" fill="#bfdbfe" stroke="#1e40af" stroke-width="2"/>
  <text x="0" y="5" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">m</text>
  <!-- Normal Reaction R -->
  <line x1="0" y1="-25" x2="0" y2="-75" stroke="#16a34a" stroke-width="2.5"/>
  <polygon points="0,-82 -4,-70 4,-70" fill="#16a34a"/>
  <text x="10" y="-65" font-family="Arial" font-size="13" font-weight="bold" fill="#16a34a">{_esc(r_txt)}</text>
  <!-- Friction F_r up slope -->
  <line x1="-35" y1="25" x2="-80" y2="25" stroke="#d97706" stroke-width="2.5"/>
  <polygon points="-87,25 -75,21 -75,29" fill="#d97706"/>
  <text x="-85" y="15" font-family="Arial" font-size="13" font-weight="bold" fill="#d97706">{_esc(f_txt)}</text>
</g>
<!-- Downward gravity W = mg -->
<line x1="320" y1="160" x2="320" y2="230" stroke="#dc2626" stroke-width="2.5"/>
<polygon points="320,238 316,226 324,226" fill="#dc2626"/>
<text x="330" y="215" font-family="Arial" font-size="13" font-weight="bold" fill="#dc2626">{_esc(w_txt)}</text>
''', "Inclined Plane Forces")


def render_simple_pendulum(length="L = 1.0 m", bob_label="Bob (m)", angle="θ", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    l_txt = callouts.get("length", length)
    b_txt = callouts.get("bob", bob_label)
    th_txt = callouts.get("angle", angle)
    return _science_svg(f'''
<!-- Rigid support -->
<rect x="250" y="45" width="140" height="8" fill="#334155"/>
<!-- Vertical equilibrium dashed line -->
<line x1="320" y1="53" x2="320" y2="250" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4,4"/>
<!-- Displaced string -->
<line x1="320" y1="53" x2="410" y2="215" stroke="#0f172a" stroke-width="2.5"/>
<!-- String angle -->
<path d="M320,100 A47,47 0 0,1 338,96" fill="none" stroke="#dc2626" stroke-width="2"/>
<text x="345" y="90" font-family="Arial" font-size="13" fill="#dc2626">{_esc(th_txt)}</text>
<text x="385" y="130" font-family="Arial" font-size="13" font-weight="bold">{_esc(l_txt)}</text>
<!-- Suspended Bob -->
<circle cx="410" cy="215" r="20" fill="#f59e0b" stroke="#b45309" stroke-width="2.5"/>
<text x="410" y="220" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#fff">m</text>
<text x="440" y="220" font-family="Arial" font-size="13">{_esc(b_txt)}</text>
<text x="320" y="270" text-anchor="middle" font-family="Arial" font-size="12" fill="#64748b">Mean Position</text>
''', "Simple Pendulum")


def render_electrolysis_cell(anode_label="Anode (+)", cathode_label="Cathode (-)", electrolyte="CuSO4 (aq)", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    an_txt = callouts.get("anode", anode_label)
    cat_txt = callouts.get("cathode", cathode_label)
    el_txt = callouts.get("electrolyte", electrolyte)
    return _science_svg(f'''
<!-- Beaker -->
<rect x="180" y="90" width="280" height="170" rx="8" fill="#f0f9ff" stroke="#0284c7" stroke-width="3"/>
<!-- Electrolyte Liquid Level -->
<rect x="185" y="135" width="270" height="120" rx="4" fill="#bae6fd" opacity="0.6"/>
<!-- Left Electrode (Anode) -->
<rect x="225" y="70" width="24" height="160" fill="#334155" stroke="#0f172a" stroke-width="2"/>
<text x="210" y="55" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#dc2626">{_esc(an_txt)}</text>
<!-- Right Electrode (Cathode) -->
<rect x="390" y="70" width="24" height="160" fill="#334155" stroke="#0f172a" stroke-width="2"/>
<text x="430" y="55" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#2563eb">{_esc(cat_txt)}</text>
<!-- Wire circuit on top -->
<path d="M237,70 V38 H300 M340,38 H402 V70" fill="none" stroke="#0f172a" stroke-width="2.5"/>
<line x1="310" y1="28" x2="310" y2="48" stroke="#dc2626" stroke-width="3"/>
<line x1="326" y1="20" x2="326" y2="56" stroke="#2563eb" stroke-width="3"/>
<text x="320" y="210" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#0369a1">{_esc(el_txt)}</text>
''', "Electrolytic Cell")


def render_flower_structure(flower_title="Dicotyledonous Flower", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    pet_txt = callouts.get("petal", "Petal (Corolla)")
    ant_txt = callouts.get("anther", "Anther (Stamen)")
    stg_txt = callouts.get("stigma", "Stigma (Carpel)")
    ov_txt = callouts.get("ovary", "Ovary (with Ovules)")
    sep_txt = callouts.get("sepal", "Sepal (Calyx)")
    return _science_svg(f'''
<!-- Receptacle & Stem -->
<rect x="312" y="235" width="16" height="50" fill="#15803d"/>
<ellipse cx="320" cy="235" rx="30" ry="12" fill="#166534"/>
<!-- Sepals -->
<path d="M290,235 C270,225 240,240 230,225" fill="none" stroke="#15803d" stroke-width="4"/>
<path d="M350,235 C370,225 400,240 410,225" fill="none" stroke="#15803d" stroke-width="4"/>
<!-- Petals -->
<path d="M290,230 C220,180 180,80 230,60 C270,40 300,140 310,210" fill="#fbcfe8" stroke="#db2777" stroke-width="2.5"/>
<path d="M350,230 C420,180 460,80 410,60 C370,40 340,140 330,210" fill="#fbcfe8" stroke="#db2777" stroke-width="2.5"/>
<!-- Stamen (Left & Right) -->
<path d="M305,215 Q260,140 260,95" fill="none" stroke="#ca8a04" stroke-width="2"/>
<ellipse cx="260" cy="90" rx="8" ry="6" fill="#eab308" stroke="#a16207" stroke-width="1.5"/>
<path d="M335,215 Q380,140 380,95" fill="none" stroke="#ca8a04" stroke-width="2"/>
<ellipse cx="380" cy="90" rx="8" ry="6" fill="#eab308" stroke="#a16207" stroke-width="1.5"/>
<!-- Carpel (Center: Ovary, Style, Stigma) -->
<path d="M312,210 Q316,140 316,90 H324 Q324,140 328,210" fill="#86efac" stroke="#16a34a" stroke-width="2"/>
<ellipse cx="320" cy="85" rx="10" ry="6" fill="#4ade80" stroke="#15803d" stroke-width="1.5"/>
<ellipse cx="320" cy="205" rx="18" ry="22" fill="#bbf7d0" stroke="#16a34a" stroke-width="2"/>
<!-- Leader lines & text -->
<line x1="260" y1="90" x2="160" y2="75" stroke="#334155" stroke-dasharray="2,2"/>
<text x="150" y="79" text-anchor="end" font-family="Arial" font-size="12" font-weight="bold">{_esc(ant_txt)}</text>
<line x1="320" y1="85" x2="320" y2="50" stroke="#334155" stroke-dasharray="2,2"/>
<text x="320" y="44" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">{_esc(stg_txt)}</text>
<line x1="205" y1="70" x2="140" y2="120" stroke="#334155" stroke-dasharray="2,2"/>
<text x="135" y="125" text-anchor="end" font-family="Arial" font-size="12" font-weight="bold" fill="#db2777">{_esc(pet_txt)}</text>
<line x1="338" y1="205" x2="480" y2="205" stroke="#334155" stroke-dasharray="2,2"/>
<text x="485" y="209" font-family="Arial" font-size="12" font-weight="bold">{_esc(ov_txt)}</text>
<line x1="400" y1="230" x2="480" y2="245" stroke="#334155" stroke-dasharray="2,2"/>
<text x="485" y="249" font-family="Arial" font-size="12" font-weight="bold" fill="#15803d">{_esc(sep_txt)}</text>
''', "Flower Longitudinal Section")


def render_nephron_unit(organ="Nephron Structure", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    bow_txt = callouts.get("bowmans_capsule", "Bowman's Capsule")
    glom_txt = callouts.get("glomerulus", "Glomerulus")
    loop_txt = callouts.get("loop_of_henle", "Loop of Henle")
    duct_txt = callouts.get("collecting_duct", "Collecting Duct")
    return _science_svg(f'''
<!-- Bowman\'s capsule cup -->
<path d="M180,85 C140,85 140,155 180,155 C200,155 210,135 210,120 C210,105 200,85 180,85 Z" fill="#fef08a" stroke="#ca8a04" stroke-width="2.5"/>
<!-- Glomerulus inside -->
<circle cx="175" cy="120" r="14" fill="#fca5a5" stroke="#dc2626" stroke-width="2"/>
<!-- Proximal Tubule convolution -->
<path d="M210,120 Q240,90 270,120 T330,120" fill="none" stroke="#ca8a04" stroke-width="4"/>
<!-- Loop of Henle hairpin -->
<path d="M330,120 V240 C330,265 370,265 370,240 V120" fill="none" stroke="#eab308" stroke-width="4"/>
<!-- Distal tubule into collecting duct -->
<path d="M370,120 Q400,90 440,120 H470" fill="none" stroke="#ca8a04" stroke-width="4"/>
<!-- Collecting duct trunk -->
<rect x="470" y="60" width="16" height="210" fill="#fed7aa" stroke="#ea580c" stroke-width="2.5"/>
<!-- Leaders & Labels -->
<line x1="175" y1="106" x2="175" y2="55" stroke="#334155" stroke-dasharray="2,2"/>
<text x="175" y="48" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#dc2626">{_esc(glom_txt)}</text>
<line x1="150" y1="150" x2="100" y2="180" stroke="#334155" stroke-dasharray="2,2"/>
<text x="95" y="184" text-anchor="end" font-family="Arial" font-size="12" font-weight="bold">{_esc(bow_txt)}</text>
<line x1="350" y1="260" x2="350" y2="285" stroke="#334155" stroke-dasharray="2,2"/>
<text x="350" y="297" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">{_esc(loop_txt)}</text>
<line x1="486" y1="120" x2="550" y2="120" stroke="#334155" stroke-dasharray="2,2"/>
<text x="555" y="124" font-family="Arial" font-size="12" font-weight="bold" fill="#ea580c">{_esc(duct_txt)}</text>
''', "Mammalian Nephron")


def render_knapsack_sprayer(tool_name="Knapsack Sprayer", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    tk_txt = callouts.get("tank", "Chemical Tank")
    nozz_txt = callouts.get("nozzle", "Atomizing Nozzle")
    ln_txt = callouts.get("lance", "Trigger Lance")
    lv_txt = callouts.get("pump_lever", "Pump Operating Lever")
    return _science_svg(f'''
<!-- Tank body -->
<rect x="220" y="70" width="140" height="170" rx="28" fill="#38bdf8" stroke="#0284c7" stroke-width="3"/>
<rect x="260" y="52" width="60" height="20" rx="4" fill="#0369a1"/>
<!-- Shoulder straps -->
<path d="M240,75 C210,120 210,180 240,225" fill="none" stroke="#334155" stroke-width="4"/>
<!-- Pump handle / lever -->
<line x1="205" y1="220" x2="175" y2="140" stroke="#1e293b" stroke-width="5"/>
<circle cx="175" cy="140" r="7" fill="#1e293b"/>
<!-- Flexible hose -->
<path d="M330,230 C360,260 410,240 430,210 L480,140" fill="none" stroke="#1e293b" stroke-width="4"/>
<!-- Trigger lance -->
<line x1="480" y1="140" x2="550" y2="80" stroke="#64748b" stroke-width="4"/>
<line x1="550" y1="80" x2="570" y2="62" stroke="#e11d48" stroke-width="3"/>
<polygon points="570,62 585,55 580,72" fill="#e11d48"/>
<!-- Spray cone droplets -->
<path d="M580,60 L610,40 M582,65 L615,65 M580,70 L610,85" stroke="#38bdf8" stroke-width="2" stroke-dasharray="3,3"/>
<!-- Labels -->
<text x="290" y="155" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#0369a1">{_esc(tk_txt)}</text>
<text x="160" y="130" text-anchor="end" font-family="Arial" font-size="12" font-weight="bold">{_esc(lv_txt)}</text>
<text x="500" y="170" font-family="Arial" font-size="12" font-weight="bold">{_esc(ln_txt)}</text>
<text x="585" y="100" font-family="Arial" font-size="12" font-weight="bold" fill="#e11d48">{_esc(nozz_txt)}</text>
''', "Knapsack Sprayer")


def render_soil_profile(profile_title="Ideal Soil Profile", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    ho_txt = callouts.get("horizon_o", "Horizon O (Humus Layer)")
    ha_txt = callouts.get("horizon_a", "Horizon A (Topsoil)")
    hb_txt = callouts.get("horizon_b", "Horizon B (Subsoil)")
    hc_txt = callouts.get("horizon_c", "Horizon C (Weathered Rock)")
    hr_txt = callouts.get("horizon_r", "Horizon R (Bedrock)")
    return _science_svg(f'''
<!-- Soil Column Container -->
<rect x="180" y="48" width="160" height="235" fill="none" stroke="#1e293b" stroke-width="2.5"/>
<!-- Horizon O (Humus) -->
<rect x="181" y="49" width="158" height="25" fill="#451a03"/>
<!-- Horizon A (Topsoil) -->
<rect x="181" y="74" width="158" height="50" fill="#78350f"/>
<!-- Horizon B (Subsoil) -->
<rect x="181" y="124" width="158" height="60" fill="#b45309"/>
<!-- Horizon C (Weathered Rock) -->
<rect x="181" y="184" width="158" height="50" fill="#d97706"/>
<!-- Horizon R (Bedrock) -->
<rect x="181" y="234" width="158" height="48" fill="#64748b"/>
<!-- Text Labels on right -->
<line x1="339" y1="62" x2="380" y2="62" stroke="#334155" stroke-dasharray="2,2"/>
<text x="388" y="66" font-family="Arial" font-size="13" font-weight="bold" fill="#451a03">{_esc(ho_txt)}</text>
<line x1="339" y1="99" x2="380" y2="99" stroke="#334155" stroke-dasharray="2,2"/>
<text x="388" y="103" font-family="Arial" font-size="13" font-weight="bold" fill="#78350f">{_esc(ha_txt)}</text>
<line x1="339" y1="154" x2="380" y2="154" stroke="#334155" stroke-dasharray="2,2"/>
<text x="388" y="158" font-family="Arial" font-size="13" font-weight="bold" fill="#b45309">{_esc(hb_txt)}</text>
<line x1="339" y1="209" x2="380" y2="209" stroke="#334155" stroke-dasharray="2,2"/>
<text x="388" y="213" font-family="Arial" font-size="13" font-weight="bold" fill="#d97706">{_esc(hc_txt)}</text>
<line x1="339" y1="258" x2="380" y2="258" stroke="#334155" stroke-dasharray="2,2"/>
<text x="388" y="262" font-family="Arial" font-size="13" font-weight="bold" fill="#475569">{_esc(hr_txt)}</text>
''', "Soil Profile Horizons")


def render_ruminant_stomach(animal="Ruminant (Cow/Sheep)", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    rum_txt = callouts.get("rumen", "Rumen (Paunch)")
    ret_txt = callouts.get("reticulum", "Reticulum (Honeycomb)")
    oma_txt = callouts.get("omasum", "Omasum (Manyplies)")
    abo_txt = callouts.get("abomasum", "Abomasum (True Stomach)")
    return _science_svg(f'''
<!-- Esophagus -->
<path d="M120,70 Q180,85 240,110" fill="none" stroke="#64748b" stroke-width="8"/>
<!-- Rumen (Large lower left) -->
<ellipse cx="260" cy="190" rx="90" ry="65" fill="#fef3c7" stroke="#d97706" stroke-width="3"/>
<!-- Reticulum (Small front) -->
<circle cx="340" cy="120" r="35" fill="#fed7aa" stroke="#ea580c" stroke-width="3"/>
<!-- Omasum (Round third compartment) -->
<circle cx="410" cy="150" r="32" fill="#e0e7ff" stroke="#4f46e5" stroke-width="3"/>
<!-- Abomasum (Elongated fourth compartment) -->
<path d="M410,182 C440,210 470,240 510,210 C530,195 510,165 470,175 Z" fill="#dcfce7" stroke="#16a34a" stroke-width="3"/>
<!-- Duodenum out -->
<path d="M510,210 Q540,230 570,225" fill="none" stroke="#64748b" stroke-width="6"/>
<!-- Labels -->
<text x="240" y="195" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#b45309">{_esc(rum_txt)}</text>
<text x="340" y="125" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#c2410c">{_esc(ret_txt)}</text>
<text x="410" y="154" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#4338ca">{_esc(oma_txt)}</text>
<text x="490" y="245" font-family="Arial" font-size="12" font-weight="bold" fill="#15803d">{_esc(abo_txt)}</text>
''', "Ruminant Digestive System")

ARCHETYPES_META = {
    "horizontal_y_fork": {
        "title": "Horizontal Y-Fork (Circle → 2 Boxes)",
        "fields": [
            {"name": "parent", "label": "Parent (Circle)", "default": "12"},
            {"name": "child_top", "label": "Top Child (Box)", "default": "4"},
            {"name": "child_bottom", "label": "Bottom Child (Box)", "default": "8"},
        ],
        "missing_options": ["", "parent", "child_top", "child_bottom"],
    },
    "fraction_branch": {
        "title": "Fraction Branch (2 Fractions → 1 Fraction)",
        "fields": [
            {"name": "frac_left_num", "label": "Left Numerator", "default": "1"},
            {"name": "frac_left_den", "label": "Left Denominator", "default": "2"},
            {"name": "frac_right_num", "label": "Right Numerator", "default": "1"},
            {"name": "frac_right_den", "label": "Right Denominator", "default": "4"},
            {"name": "frac_bottom_num", "label": "Bottom Numerator", "default": "3"},
            {"name": "frac_bottom_den", "label": "Bottom Denominator", "default": "4"},
        ],
        "missing_options": ["", "frac_left_num", "frac_left_den", "frac_right_num", "frac_right_den", "frac_bottom_num", "frac_bottom_den"],
    },
    "m_network": {
        "title": "M-Shape / W-Shape Network (5 Nodes)",
        "fields": [
            {"name": "tl", "label": "Top Left", "default": "3"},
            {"name": "bl", "label": "Bottom Left", "default": "9"},
            {"name": "center", "label": "Center Hub", "default": "15"},
            {"name": "tr", "label": "Top Right", "default": "6"},
            {"name": "br", "label": "Bottom Right", "default": "18"},
        ],
        "missing_options": ["", "tl", "bl", "center", "tr", "br"],
    },
    "power_fork": {
        "title": "Power Circle + Fork (Base^Exp → Mid → 2 Forks)",
        "fields": [
            {"name": "base", "label": "Base (Circle)", "default": "2"},
            {"name": "exp", "label": "Exponent (Small)", "default": "3"},
            {"name": "mid_box", "label": "Middle Box", "default": "8"},
            {"name": "fork1", "label": "Top Fork", "default": "4"},
            {"name": "fork2", "label": "Bottom Fork", "default": "2"},
        ],
        "missing_options": ["", "base", "mid_box", "fork1", "fork2"],
    },
    "compass_cross": {
        "title": "4-Way Compass Cross (Hub + 4 Arms)",
        "fields": [
            {"name": "center", "label": "Center Hub", "default": "20"},
            {"name": "top", "label": "North Arm", "default": "5"},
            {"name": "bottom", "label": "South Arm", "default": "10"},
            {"name": "left", "label": "West Arm", "default": "2"},
            {"name": "right", "label": "East Arm", "default": "4"},
            {"name": "op_top", "label": "Top Operator", "default": "+"},
            {"name": "op_bot", "label": "Bottom Operator", "default": "×"},
        ],
        "missing_options": ["", "center", "top", "bottom", "left", "right"],
    },
    "horseshoe": {
        "title": "Horseshoe U-Shape (Top-L, Top-R, Trough)",
        "fields": [
            {"name": "left", "label": "Left Circle", "default": "7"},
            {"name": "right", "label": "Right Circle", "default": "9"},
            {"name": "bottom", "label": "Bottom Trough", "default": "63"},
        ],
        "missing_options": ["", "left", "right", "bottom"],
    },
    "arc_c": {
        "title": "Arc C-Shape (Top, Bottom, Inner Box)",
        "fields": [
            {"name": "top", "label": "Top Node", "default": "15"},
            {"name": "bottom", "label": "Bottom Node", "default": "5"},
            {"name": "inside", "label": "Inner Box", "default": "3"},
        ],
        "missing_options": ["", "top", "bottom", "inside"],
    },
    "grid_with_ear": {
        "title": "2x2 Grid with Result Ear",
        "fields": [
            {"name": "r1c1", "label": "Row 1, Col 1", "default": "2"},
            {"name": "r1c2", "label": "Row 1, Col 2", "default": "4"},
            {"name": "r2c1", "label": "Row 2, Col 1", "default": "3"},
            {"name": "r2c2", "label": "Row 2, Col 2", "default": "6"},
            {"name": "ear", "label": "Result Ear", "default": "24"},
        ],
        "missing_options": ["", "r1c1", "r1c2", "r2c1", "r2c2", "ear"],
    },
    "tbar_multiplier": {
        "title": "T-Bar Multiplier (2 Top Boxes → Beam to Product)",
        "fields": [
            {"name": "left_top", "label": "Left Top Box", "default": "6"},
            {"name": "right_top", "label": "Right Top Box", "default": "7"},
            {"name": "bottom", "label": "Bottom Product", "default": "42"},
        ],
        "missing_options": ["", "left_top", "right_top", "bottom"],
    },
    "triangle_puzzle": {
        "title": "Triangle Puzzle (3 Vertices + Center)",
        "fields": [
            {"name": "top", "label": "Top Vertex", "default": "4"},
            {"name": "left", "label": "Left Vertex", "default": "6"},
            {"name": "right", "label": "Right Vertex", "default": "8"},
            {"name": "center", "label": "Center Value", "default": "24"},
        ],
        "missing_options": ["", "top", "left", "right", "center"],
    },
    "electric_circuit": {"title": "Series Electric Circuit", "fields": [{"name": "battery", "label": "Battery", "default": "12 V"}, {"name": "resistor", "label": "Resistor", "default": "R"}, {"name": "current", "label": "Current", "default": "I"}], "missing_options": ["", "battery", "resistor"]},
    "optical_ray": {"title": "Optical Ray Diagram", "fields": [{"name": "object_label", "label": "Object", "default": "Object"}, {"name": "image_label", "label": "Image", "default": "Image"}, {"name": "focal_length", "label": "Focal length", "default": "f"}], "missing_options": ["", "object_label", "image_label"]},
    "burette": {"title": "Burette Titration Setup", "fields": [{"name": "volume", "label": "Volume", "default": "25.0 mL"}, {"name": "titre", "label": "Titre", "default": "Titre"}, {"name": "indicator", "label": "Indicator", "default": "Indicator"}], "missing_options": ["", "volume", "indicator"]},
    "liebig_condenser": {"title": "Liebig Condenser", "fields": [{"name": "water_in", "label": "Water in", "default": "Water in"}, {"name": "water_out", "label": "Water out", "default": "Water out"}, {"name": "vapour", "label": "Vapour", "default": "Vapour"}], "missing_options": ["", "water_in", "water_out"]},
    "biology_cell": {"title": "Biology Cell Diagram", "fields": [{"name": "cell_type", "label": "Cell type", "default": "Plant cell"}, {"name": "nucleus", "label": "Nucleus", "default": "Nucleus"}, {"name": "vacuole", "label": "Vacuole", "default": "Vacuole"}], "missing_options": ["", "cell_type", "nucleus", "vacuole"]},
}


def render_triangular_prism(base_angle="60°", apex_angle="60°", ray_color="#dc2626", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    ir_txt = callouts.get("incident_ray", "Incident Ray")
    norm_txt = callouts.get("normal", "Normal")
    rr_txt = callouts.get("refracted_ray", "Refracted Ray")
    er_txt = callouts.get("emergent_ray", "Emergent Ray")
    dev_txt = callouts.get("deviation_angle", "Deviation (D)")
    return _science_svg(f'''
<!-- Glass Prism -->
<polygon points="320,55 170,245 470,245" fill="#f0f9ff" stroke="#0284c7" stroke-width="3"/>
<text x="320" y="80" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#0369a1">{_esc(apex_angle)}</text>
<!-- Normal Lines -->
<line x1="210" y1="130" x2="275" y2="185" stroke="#64748b" stroke-width="1.8" stroke-dasharray="4,3"/>
<text x="195" y="125" font-family="Arial" font-size="12" fill="#64748b">{_esc(norm_txt)}</text>
<line x1="365" y1="185" x2="430" y2="130" stroke="#64748b" stroke-width="1.8" stroke-dasharray="4,3"/>
<!-- Incident Ray -->
<line x1="100" y1="200" x2="245" y2="160" stroke="{_esc(ray_color)}" stroke-width="3"/>
<polygon points="180,181 170,175 174,185" fill="{_esc(ray_color)}"/>
<text x="140" y="165" font-family="Arial" font-size="13" font-weight="bold" fill="{_esc(ray_color)}">{_esc(ir_txt)}</text>
<!-- Refracted Ray inside prism -->
<line x1="245" y1="160" x2="395" y2="160" stroke="{_esc(ray_color)}" stroke-width="3"/>
<polygon points="325,160 315,155 315,165" fill="{_esc(ray_color)}"/>
<text x="320" y="150" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="{_esc(ray_color)}">{_esc(rr_txt)}</text>
<!-- Emergent Ray -->
<line x1="395" y1="160" x2="540" y2="200" stroke="{_esc(ray_color)}" stroke-width="3"/>
<polygon points="475,185 465,178 470,189" fill="{_esc(ray_color)}"/>
<text x="490" y="165" font-family="Arial" font-size="13" font-weight="bold" fill="{_esc(ray_color)}">{_esc(er_txt)}</text>
<!-- Angle of Deviation guide -->
<line x1="245" y1="160" x2="380" y2="123" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="3,3"/>
<text x="420" y="115" font-family="Arial" font-size="12" font-weight="bold" fill="#7c3aed">{_esc(dev_txt)}</text>
<text x="320" y="275" text-anchor="middle" font-family="Arial" font-size="12" fill="#64748b">{_esc(sample_label or 'Light Refraction through Triangular Prism')}</text>
''', "Triangular Prism (Refraction & Dispersion)")


def render_separating_funnel(upper_liquid="Oil", lower_liquid="Water", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    stop_txt = callouts.get("stopper", "Stopper")
    up_txt = callouts.get("upper_layer", upper_liquid)
    if_txt = callouts.get("interface", "Meniscus / Interface")
    low_txt = callouts.get("lower_layer", lower_liquid)
    tap_txt = callouts.get("stopcock", "Stopcock Tap")
    return _science_svg(f'''
<!-- Retort Ring Clamp -->
<rect x="180" y="130" width="80" height="8" fill="#475569"/>
<!-- Funnel Body -->
<path d="M260,70 L380,70 L370,150 L330,210 L330,250 L310,250 L310,210 L270,150 Z" fill="#f8fafc" stroke="#1e293b" stroke-width="3"/>
<!-- Lower Liquid (Water / Blue) -->
<path d="M280,165 L360,165 L330,210 L330,235 L310,235 L310,210 Z" fill="#bfdbfe" fill-opacity="0.85"/>
<!-- Upper Liquid (Oil / Amber) -->
<path d="M265,90 L375,90 L360,165 L280,165 Z" fill="#fef08a" fill-opacity="0.85"/>
<!-- Meniscus Line -->
<line x1="280" y1="165" x2="360" y2="165" stroke="#0284c7" stroke-width="2.5"/>
<!-- Glass Stopper -->
<polygon points="305,45 335,45 330,70 310,70" fill="#e2e8f0" stroke="#1e293b" stroke-width="2"/>
<text x="320" y="40" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">{_esc(stop_txt)}</text>
<!-- Stopcock Tap -->
<rect x="300" y="222" width="40" height="12" rx="3" fill="#dc2626" stroke="#1e293b" stroke-width="2"/>
<text x="365" y="232" font-family="Arial" font-size="12" font-weight="bold" fill="#dc2626">{_esc(tap_txt)}</text>
<!-- Labels -->
<line x1="365" y1="125" x2="430" y2="125" stroke="#d97706" stroke-width="1.8"/>
<text x="435" y="130" font-family="Arial" font-size="13" font-weight="bold" fill="#d97706">{_esc(up_txt)}</text>
<line x1="355" y1="165" x2="430" y2="165" stroke="#0284c7" stroke-width="1.8"/>
<text x="435" y="170" font-family="Arial" font-size="12" font-weight="bold" fill="#0284c7">{_esc(if_txt)}</text>
<line x1="330" y1="190" x2="430" y2="190" stroke="#1d4ed8" stroke-width="1.8"/>
<text x="435" y="195" font-family="Arial" font-size="13" font-weight="bold" fill="#1d4ed8">{_esc(low_txt)}</text>
<!-- Receiving Beaker -->
<path d="M295,260 L295,290 L345,290 L345,260" fill="none" stroke="#64748b" stroke-width="2"/>
<text x="320" y="282" text-anchor="middle" font-family="Arial" font-size="11" fill="#64748b">Beaker</text>
<text x="140" y="90" font-family="Arial" font-size="12" fill="#64748b">{_esc(sample_label or 'Separation of Immiscible Liquids')}</text>
''', "Separating Funnel Setup")


def render_heart_structure(organ_title="Mammalian Heart", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    ra_txt = callouts.get("right_atrium", "Right Atrium")
    la_txt = callouts.get("left_atrium", "Left Atrium")
    rv_txt = callouts.get("right_ventricle", "Right Ventricle")
    lv_txt = callouts.get("left_ventricle", "Left Ventricle")
    sep_txt = callouts.get("septum", "Septum")
    return _science_svg(f'''
<!-- Outer Heart Muscle Contour -->
<path d="M320,80 C260,35 170,85 180,165 C190,225 280,265 320,285 C360,265 450,225 460,165 C470,85 380,35 320,80 Z" fill="#fee2e2" stroke="#b91c1c" stroke-width="4"/>
<!-- Central Dividing Septum -->
<path d="M312,120 L312,275 L328,275 L328,120 Z" fill="#ef4444" stroke="#991b1b" stroke-width="2"/>
<text x="320" y="200" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#ffffff" transform="rotate(-90 320 200)">{_esc(sep_txt)}</text>
<!-- Right Atrium (Anatomical Right = Viewer Left) -->
<rect x="205" y="100" width="90" height="50" rx="8" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>
<text x="250" y="130" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#1e40af">{_esc(ra_txt)}</text>
<!-- Left Atrium (Anatomical Left = Viewer Right) -->
<rect x="345" y="100" width="90" height="50" rx="8" fill="#ffedd5" stroke="#ea580c" stroke-width="2"/>
<text x="390" y="130" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#9a3412">{_esc(la_txt)}</text>
<!-- Right Ventricle -->
<rect x="205" y="175" width="90" height="60" rx="8" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>
<text x="250" y="210" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#1e40af">{_esc(rv_txt)}</text>
<!-- Left Ventricle (Thick walled) -->
<rect x="345" y="175" width="90" height="60" rx="8" fill="#fee2e2" stroke="#dc2626" stroke-width="3"/>
<text x="390" y="210" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#991b1b">{_esc(lv_txt)}</text>
<!-- Pulmonary & Aortic Arches -->
<path d="M260,100 C260,50 300,45 315,65" fill="none" stroke="#2563eb" stroke-width="6"/>
<path d="M380,100 C380,40 330,35 325,65" fill="none" stroke="#dc2626" stroke-width="6"/>
<text x="320" y="295" text-anchor="middle" font-family="Arial" font-size="11" fill="#64748b">{_esc(sample_label or organ_title)}</text>
''', "Human Heart (4 Chambers)")


def render_food_web(ecosystem_name="Terrestrial Food Web", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    p_txt = callouts.get("producer", "Green Plants (Producers)")
    c1_txt = callouts.get("primary_consumer", "Grasshopper / Herbivore")
    c2_txt = callouts.get("secondary_consumer", "Toad / Carnivore")
    c3_txt = callouts.get("apex_predator", "Hawk / Apex Predator")
    return _science_svg(f'''
<!-- Trophic Level 4: Apex Predator (Top) -->
<rect x="230" y="45" width="180" height="38" rx="6" fill="#fee2e2" stroke="#dc2626" stroke-width="2.5"/>
<text x="320" y="69" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#991b1b">{_esc(c3_txt)}</text>
<!-- Arrow 3 -> 4 -->
<line x1="320" y1="105" x2="320" y2="87" stroke="#b91c1c" stroke-width="2.5"/>
<polygon points="320,83 315,93 325,93" fill="#b91c1c"/>
<!-- Trophic Level 3: Secondary Consumer -->
<rect x="230" y="105" width="180" height="38" rx="6" fill="#ffedd5" stroke="#ea580c" stroke-width="2.5"/>
<text x="320" y="129" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#9a3412">{_esc(c2_txt)}</text>
<!-- Arrow 2 -> 3 -->
<line x1="320" y1="165" x2="320" y2="147" stroke="#ea580c" stroke-width="2.5"/>
<polygon points="320,143 315,153 325,153" fill="#ea580c"/>
<!-- Trophic Level 2: Primary Consumer -->
<rect x="230" y="165" width="180" height="38" rx="6" fill="#fef9c3" stroke="#ca8a04" stroke-width="2.5"/>
<text x="320" y="189" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#854d0e">{_esc(c1_txt)}</text>
<!-- Arrow 1 -> 2 -->
<line x1="320" y1="225" x2="320" y2="207" stroke="#16a34a" stroke-width="2.5"/>
<polygon points="320,203 315,213 325,213" fill="#16a34a"/>
<!-- Trophic Level 1: Primary Producer (Base) -->
<rect x="200" y="225" width="240" height="42" rx="6" fill="#dcfce7" stroke="#16a34a" stroke-width="2.5"/>
<text x="320" y="251" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#14532d">{_esc(p_txt)}</text>
<!-- Energy Flow Label -->
<text x="110" y="160" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#64748b" transform="rotate(-90 110 160)">ENERGY FLOW ↑</text>
<text x="530" y="260" font-family="Arial" font-size="11" fill="#64748b">{_esc(sample_label or ecosystem_name)}</text>
''', "Ecosystem Food Chain & Trophic Levels")


def render_wheelbarrow(tool_name="Farm Wheelbarrow", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    w_txt = callouts.get("wheel", "Wheel (Fulcrum)")
    t_txt = callouts.get("tray", "Tray (Load)")
    h_txt = callouts.get("handles", "Handles (Effort)")
    l_txt = callouts.get("legs", "Legs / Stand")
    return _science_svg(f'''
<!-- Ground Line -->
<line x1="80" y1="250" x2="560" y2="250" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6,4"/>
<!-- Wheel (Fulcrum at Front) -->
<circle cx="170" cy="225" r="25" fill="#e2e8f0" stroke="#1e293b" stroke-width="3"/>
<circle cx="170" cy="225" r="6" fill="#1e293b"/>
<line x1="170" y1="200" x2="170" y2="250" stroke="#64748b" stroke-width="2"/>
<line x1="145" y1="225" x2="195" y2="225" stroke="#64748b" stroke-width="2"/>
<text x="170" y="272" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#1e293b">{_esc(w_txt)}</text>
<!-- Frame connecting wheel to handle -->
<line x1="170" y1="225" x2="500" y2="125" stroke="#1e293b" stroke-width="5"/>
<!-- Handle Grip -->
<rect x="490" y="118" width="35" height="14" rx="4" fill="#dc2626"/>
<text x="525" y="112" font-family="Arial" font-size="13" font-weight="bold" fill="#dc2626">{_esc(h_txt)}</text>
<!-- Load Tray / Hopper -->
<polygon points="210,130 380,110 350,195 240,195" fill="#fde047" stroke="#ca8a04" stroke-width="3"/>
<text x="295" y="160" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#854d0e">{_esc(t_txt)}</text>
<!-- Resting Leg / Stand -->
<line x1="330" y1="180" x2="350" y2="250" stroke="#1e293b" stroke-width="4"/>
<line x1="350" y1="250" x2="365" y2="250" stroke="#1e293b" stroke-width="4"/>
<text x="375" y="245" font-family="Arial" font-size="12" font-weight="bold" fill="#475569">{_esc(l_txt)}</text>
<text x="320" y="60" text-anchor="middle" font-family="Arial" font-size="13" fill="#64748b">{_esc(sample_label or 'Class II Lever System (Load between Fulcrum & Effort)')}</text>
''', "Farm Wheelbarrow (Second-Class Lever)")


def render_egg_structure(egg_type="Avian Egg Structure", missing="", sample_label="", _callouts=None) -> str:
    callouts = _callouts or {}
    s_txt = callouts.get("shell", "Hard Shell")
    ac_txt = callouts.get("air_cell", "Air Cell")
    alb_txt = callouts.get("albumen", "Albumen (White)")
    y_txt = callouts.get("yolk", "Yolk")
    ch_txt = callouts.get("chalaza", "Chalaza")
    return _science_svg(f'''
<!-- Outer Shell (Oval egg shape) -->
<ellipse cx="320" cy="155" rx="190" ry="110" fill="#fefce8" stroke="#78350f" stroke-width="4"/>
<text x="320" y="38" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#78350f">{_esc(s_txt)}</text>
<!-- Air Cell at blunt end (Right) -->
<path d="M475,115 A110,110 0 0,1 475,195 A140,110 0 0,0 475,115 Z" fill="#e0f2fe" stroke="#0284c7" stroke-width="2"/>
<text x="500" y="160" text-anchor="start" font-family="Arial" font-size="12" font-weight="bold" fill="#0369a1">{_esc(ac_txt)}</text>
<!-- Translucent Albumen (Egg White) -->
<ellipse cx="305" cy="155" rx="145" ry="85" fill="#f0fdf4" fill-opacity="0.8" stroke="#86efac" stroke-width="1.5"/>
<text x="305" y="95" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#16a34a">{_esc(alb_txt)}</text>
<!-- Coiled Chalaza Cords -->
<path d="M195,155 Q210,145 225,155 T255,155" fill="none" stroke="#ca8a04" stroke-width="3"/>
<path d="M355,155 Q370,145 385,155 T415,155" fill="none" stroke="#ca8a04" stroke-width="3"/>
<text x="210" y="140" font-family="Arial" font-size="12" font-weight="bold" fill="#ca8a04">{_esc(ch_txt)}</text>
<!-- Rich Yellow Yolk (Center) -->
<circle cx="305" cy="155" r="50" fill="#facc15" stroke="#eab308" stroke-width="3"/>
<circle cx="305" cy="135" r="7" fill="#ffffff" stroke="#ca8a04" stroke-width="1.5"/>
<text x="305" y="162" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#713f12">{_esc(y_txt)}</text>
<text x="320" y="285" text-anchor="middle" font-family="Arial" font-size="12" fill="#64748b">{_esc(sample_label or egg_type)}</text>
''', "Internal Structure of an Egg")


def render_archetype(archetype: str, params: dict) -> str:
    """Render an SVG diagram archetype from a dictionary of parameters."""
    missing = str(params.get("missing") or "").strip()
    sample_label = str(params.get("sample_label") or "").strip()
    callouts = params.get("_callouts")

    if archetype == "horizontal_y_fork":
        return render_horizontal_y_fork(
            parent=params.get("parent", 12),
            child_top=params.get("child_top", 4),
            child_bottom=params.get("child_bottom", 8),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "fraction_branch":
        return render_fraction_branch(
            frac_left=(params.get("frac_left_num", 1), params.get("frac_left_den", 2)),
            frac_right=(params.get("frac_right_num", 1), params.get("frac_right_den", 4)),
            frac_bottom=(params.get("frac_bottom_num", 3), params.get("frac_bottom_den", 4)),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "m_network":
        return render_m_network(
            tl=params.get("tl", 3),
            bl=params.get("bl", 9),
            center=params.get("center", 15),
            tr=params.get("tr", 6),
            br=params.get("br", 18),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "power_fork":
        return render_power_fork(
            base=params.get("base", 2),
            exp=params.get("exp", 3),
            mid_box=params.get("mid_box", 8),
            fork1=params.get("fork1", 4),
            fork2=params.get("fork2", 2),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "compass_cross":
        return render_compass_cross(
            center=params.get("center", 20),
            top=params.get("top", 5),
            bottom=params.get("bottom", 10),
            left=params.get("left", 2),
            right=params.get("right", 4),
            op_top=str(params.get("op_top", "+")),
            op_bot=str(params.get("op_bot", "×")),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "horseshoe":
        return render_horseshoe(
            left=params.get("left", 7),
            right=params.get("right", 9),
            bottom=params.get("bottom", 63),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "arc_c":
        return render_arc_c(
            top=params.get("top", 15),
            bottom=params.get("bottom", 5),
            inside=params.get("inside", 3),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "grid_with_ear":
        return render_grid_with_ear(
            r1c1=params.get("r1c1", 2),
            r1c2=params.get("r1c2", 4),
            r2c1=params.get("r2c1", 3),
            r2c2=params.get("r2c2", 6),
            ear=params.get("ear", 24),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "tbar_multiplier":
        return render_t_bar(
            left_top=params.get("left_top", 6),
            right_top=params.get("right_top", 7),
            bottom=params.get("bottom", 42),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "triangle_puzzle":
        return render_triangle_puzzle(
            top=params.get("top", 4),
            left=params.get("left", 6),
            right=params.get("right", 8),
            center=params.get("center", 24),
            missing=missing,
            sample_label=sample_label,
            _callouts=callouts,
        )
    elif archetype == "electric_circuit":
        return render_electric_circuit(params.get("battery", "12 V"), params.get("resistor", "R"), params.get("current", "I"), missing, sample_label, callouts)
    elif archetype == "optical_ray":
        return render_optical_ray(params.get("object_label", "Object"), params.get("image_label", "Image"), params.get("focal_length", "f"), missing, sample_label, callouts)
    elif archetype == "burette":
        return render_burette(params.get("volume", "25.0 mL"), params.get("titre", "Titre"), params.get("indicator", "Indicator"), missing, sample_label, callouts)
    elif archetype == "liebig_condenser":
        return render_liebig_condenser(params.get("water_in", "Water in"), params.get("water_out", "Water out"), params.get("vapour", "Vapour"), missing, sample_label, callouts)
    elif archetype == "biology_cell":
        return render_biology_cell(params.get("cell_type", "Plant cell"), params.get("nucleus", "Nucleus"), params.get("vacuole", "Vacuole"), missing, sample_label, callouts)
    elif archetype == "right_triangle":
        return render_right_triangle(params.get("base_label", "4 cm"), params.get("height_label", "3 cm"), params.get("hypotenuse_label", "5 cm"), params.get("angle_theta", "θ"), missing, sample_label, params.get("_callouts"))
    elif archetype == "venn_2set":
        return render_venn_2set(params.get("set_a_label", "A"), params.get("set_b_label", "B"), params.get("only_a", "12"), params.get("intersection", "5"), params.get("only_b", "8"), params.get("neither", "3"), missing, sample_label, params.get("_callouts"))
    elif archetype == "pulley_system":
        return render_pulley_system(params.get("load_label", "L = 100 N"), params.get("effort_label", "E"), params.get("system_type", "Single Movable"), missing, sample_label, params.get("_callouts"))
    elif archetype == "inclined_plane":
        return render_inclined_plane(params.get("angle", "30°"), params.get("mass", "W = mg"), params.get("friction", "F_r"), missing, sample_label, params.get("_callouts"))
    elif archetype == "simple_pendulum":
        return render_simple_pendulum(params.get("length", "L = 1.0 m"), params.get("bob_label", "Bob (m)"), params.get("angle", "θ"), missing, sample_label, params.get("_callouts"))
    elif archetype == "electrolysis_cell":
        return render_electrolysis_cell(params.get("anode_label", "Anode (+)"), params.get("cathode_label", "Cathode (-)"), params.get("electrolyte", "CuSO4 (aq)"), missing, sample_label, params.get("_callouts"))
    elif archetype == "flower_structure":
        return render_flower_structure(params.get("flower_title", "Dicotyledonous Flower"), missing, sample_label, params.get("_callouts"))
    elif archetype == "nephron_unit":
        return render_nephron_unit(params.get("organ", "Nephron Structure"), missing, sample_label, params.get("_callouts"))
    elif archetype == "knapsack_sprayer":
        return render_knapsack_sprayer(params.get("tool_name", "Knapsack Sprayer"), missing, sample_label, callouts)
    elif archetype == "soil_profile":
        return render_soil_profile(params.get("profile_title", "Ideal Soil Profile"), missing, sample_label, callouts)
    elif archetype == "ruminant_stomach":
        return render_ruminant_stomach(params.get("animal", "Ruminant (Cow/Sheep)"), missing, sample_label, callouts)
    elif archetype == "triangular_prism":
        return render_triangular_prism(params.get("base_angle", "60°"), params.get("apex_angle", "60°"), params.get("ray_color", "#dc2626"), missing, sample_label, callouts)
    elif archetype == "separating_funnel":
        return render_separating_funnel(params.get("upper_liquid", "Oil"), params.get("lower_liquid", "Water"), missing, sample_label, callouts)
    elif archetype == "heart_structure":
        return render_heart_structure(params.get("organ_title", "Mammalian Heart"), missing, sample_label, callouts)
    elif archetype == "food_web":
        return render_food_web(params.get("ecosystem_name", "Terrestrial Food Web"), missing, sample_label, callouts)
    elif archetype == "wheelbarrow":
        return render_wheelbarrow(params.get("tool_name", "Farm Wheelbarrow"), missing, sample_label, callouts)
    elif archetype == "egg_structure":
        return render_egg_structure(params.get("egg_type", "Avian Egg Structure"), missing, sample_label, callouts)
    else:
        raise ValueError(f"Unknown archetype: {archetype}")
