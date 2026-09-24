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


def _is_missing(val: str | int | float | None, slot_name: str, target: str) -> bool:
    """Return True if this node is the missing question target."""
    if slot_name == target:
        return True
    s = str(val or "").strip()
    return s in ("?", "[]", "[ ]", "")


# ─────────────────────────────────────────────────────────────────────────────
# Archetype A1: Horizontal Y-Fork (Circle -> 2 Rectangles)
# ─────────────────────────────────────────────────────────────────────────────

def render_horizontal_y_fork(
    parent: str | int,
    child_top: str | int,
    child_bottom: str | int,
    missing: str = "",
    sample_label: str = "",
) -> str:
    """Render horizontal Y-fork: Circle on left branching right to 2 boxes."""
    p_miss = _is_missing(parent, "parent", missing)
    ct_miss = _is_missing(child_top, "child_top", missing)
    cb_miss = _is_missing(child_bottom, "child_bottom", missing)

    p_txt = "?" if p_miss else _esc(parent)
    ct_txt = "?" if ct_miss else _esc(child_top)
    cb_txt = "?" if cb_miss else _esc(child_bottom)

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
) -> str:
    """Render two top fraction boxes joining into a bottom fraction box."""
    nl_miss = _is_missing(frac_left[0], "frac_left_num", missing)
    dl_miss = _is_missing(frac_left[1], "frac_left_den", missing)
    nr_miss = _is_missing(frac_right[0], "frac_right_num", missing)
    dr_miss = _is_missing(frac_right[1], "frac_right_den", missing)
    nb_miss = _is_missing(frac_bottom[0], "frac_bottom_num", missing)
    db_miss = _is_missing(frac_bottom[1], "frac_bottom_den", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="220" height="150" viewBox="0 0 220 150" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Connector lines -->
  <line x1="58" y1="65" x2="110" y2="86" stroke="#222" stroke-width="2" />
  <line x1="162" y1="65" x2="110" y2="86" stroke="#222" stroke-width="2" />

  <!-- Left Fraction Box -->
  <rect x="36" y="18" width="44" height="46" rx="4" stroke="#222" stroke-width="2" fill="white" />
  <line x1="38" y1="41" x2="78" y2="41" stroke="#222" stroke-width="1.8" />
  <text x="58" y="35" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if nl_miss else _esc(frac_left[0])}</text>
  <text x="58" y="58" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if dl_miss else _esc(frac_left[1])}</text>

  <!-- Right Fraction Box -->
  <rect x="140" y="18" width="44" height="46" rx="4" stroke="#222" stroke-width="2" fill="white" />
  <line x1="142" y1="41" x2="182" y2="41" stroke="#222" stroke-width="1.8" />
  <text x="162" y="35" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if nr_miss else _esc(frac_right[0])}</text>
  <text x="162" y="58" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if dr_miss else _esc(frac_right[1])}</text>

  <!-- Bottom Fraction Box -->
  <rect x="88" y="86" width="44" height="46" rx="4" stroke="#222" stroke-width="2" fill="white" />
  <line x1="90" y1="109" x2="130" y2="109" stroke="#222" stroke-width="1.8" />
  <text x="110" y="103" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if nb_miss else _esc(frac_bottom[0])}</text>
  <text x="110" y="126" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if db_miss else _esc(frac_bottom[1])}</text>
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
) -> str:
    """Render 5-node M-path: (TL, BL, Center, TR, BR)."""
    tl_m = _is_missing(tl, "tl", missing)
    bl_m = _is_missing(bl, "bl", missing)
    c_m = _is_missing(center, "center", missing)
    tr_m = _is_missing(tr, "tr", missing)
    br_m = _is_missing(br, "br", missing)

    badge = f'<text x="10" y="18" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    def _node(x: int, y: int, txt: str, is_m: bool, is_box: bool = False):
        t = "?" if is_m else _esc(txt)
        bg = "#fff9db" if is_m else "#ffffff"
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
  {_node(45, 30, str(tl), tl_m, tl_m)}
  {_node(45, 115, str(bl), bl_m, bl_m)}
  {_node(110, 78, str(center), c_m, True)}
  {_node(175, 30, str(tr), tr_m, tr_m)}
  {_node(175, 115, str(br), br_m, br_m)}
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
) -> str:
    """Render (base^exp) --- [mid_box] < (fork1, fork2)."""
    p_m = _is_missing(base, "base", missing)
    m_m = _is_missing(mid_box, "mid_box", missing)
    f1_m = _is_missing(fork1, "fork1", missing)
    f2_m = _is_missing(fork2, "fork2", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    p_content = "?" if p_m else f'{_esc(base)}<tspan dy="-6" font-size="10">{_esc(exp)}</tspan>'

    return f"""<svg width="250" height="110" viewBox="0 0 250 110" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Connector lines -->
  <line x1="68" y1="55" x2="100" y2="55" stroke="#222" stroke-width="2" />
  <line x1="148" y1="55" x2="195" y2="30" stroke="#222" stroke-width="2" />
  <line x1="148" y1="55" x2="195" y2="80" stroke="#222" stroke-width="2" />

  <!-- Power Circle -->
  <circle cx="44" cy="55" r="24" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if p_m else "#ffffff"}" />
  <text x="44" y="60" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif">{p_content}</text>

  <!-- Mid Box -->
  <rect x="100" y="38" width="48" height="34" rx="4" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if m_m else "#ffffff"}" />
  <text x="124" y="60" text-anchor="middle" font-size="14" font-weight="bold" font-family="Arial, sans-serif">{"?" if m_m else _esc(mid_box)}</text>

  <!-- Fork 1 (Top) -->
  <rect x="195" y="15" width="40" height="28" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if f1_m else "#ffffff"}" />
  <text x="215" y="34" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if f1_m else _esc(fork1)}</text>

  <!-- Fork 2 (Bottom) -->
  <rect x="195" y="68" width="40" height="28" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if f2_m else "#ffffff"}" />
  <text x="215" y="87" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if f2_m else _esc(fork2)}</text>
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
) -> str:
    """Render center hub with 4 peripheral arms."""
    c_m = _is_missing(center, "center", missing)
    t_m = _is_missing(top, "top", missing)
    b_m = _is_missing(bottom, "bottom", missing)
    l_m = _is_missing(left, "left", missing)
    r_m = _is_missing(right, "right", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="200" height="170" viewBox="0 0 200 170" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Cross arm lines -->
  <line x1="100" y1="36" x2="100" y2="134" stroke="#222" stroke-width="2.5" />
  <line x1="36" y1="85" x2="164" y2="85" stroke="#222" stroke-width="2.5" />

  <!-- Center Circle -->
  <circle cx="100" cy="85" r="22" stroke="#222" stroke-width="2.5" fill="{"#fff9db" if c_m else "#ffffff"}" />
  <text x="100" y="90" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if c_m else _esc(center)}</text>

  <!-- Top Box -->
  <rect x="78" y="10" width="44" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if t_m else "#ffffff"}" />
  <text x="100" y="28" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if t_m else _esc(top)}</text>
  <text x="100" y="52" text-anchor="middle" font-size="12" font-weight="bold" fill="#444">{html.escape(op_top)}</text>

  <!-- Bottom Box -->
  <rect x="78" y="134" width="44" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if b_m else "#ffffff"}" />
  <text x="100" y="152" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if b_m else _esc(bottom)}</text>
  <text x="100" y="125" text-anchor="middle" font-size="12" font-weight="bold" fill="#444">{html.escape(op_bot)}</text>

  <!-- Left Box -->
  <rect x="10" y="72" width="40" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if l_m else "#ffffff"}" />
  <text x="30" y="90" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if l_m else _esc(left)}</text>

  <!-- Right Box -->
  <rect x="150" y="72" width="40" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if r_m else "#ffffff"}" />
  <text x="170" y="90" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if r_m else _esc(right)}</text>
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
) -> str:
    """Render U-shape curve with Left, Right and Bottom trough circles."""
    l_m = _is_missing(left, "left", missing)
    r_m = _is_missing(right, "right", missing)
    b_m = _is_missing(bottom, "bottom", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="200" height="130" viewBox="0 0 200 130" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- U-path -->
  <path d="M 45 40 C 45 110, 155 110, 155 40" stroke="#222" stroke-width="3" fill="none" />

  <!-- Left circle -->
  <circle cx="45" cy="40" r="22" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if l_m else "#ffffff"}" />
  <text x="45" y="45" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if l_m else _esc(left)}</text>

  <!-- Right circle -->
  <circle cx="155" cy="40" r="22" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if r_m else "#ffffff"}" />
  <text x="155" y="45" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if r_m else _esc(right)}</text>

  <!-- Bottom trough circle -->
  <circle cx="100" cy="98" r="20" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if b_m else "#ffffff"}" />
  <text x="100" y="103" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if b_m else _esc(bottom)}</text>
</svg>"""


def render_arc_c(
    top: str | int,
    bottom: str | int,
    inside: str | int,
    missing: str = "",
    sample_label: str = "",
) -> str:
    """Render C-shape curve with Top, Bottom and Inner box."""
    t_m = _is_missing(top, "top", missing)
    b_m = _is_missing(bottom, "bottom", missing)
    i_m = _is_missing(inside, "inside", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="180" height="150" viewBox="0 0 180 150" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- C-path -->
  <path d="M 110 35 C 30 35, 30 115, 110 115" stroke="#222" stroke-width="3" fill="none" />

  <!-- Top circle -->
  <circle cx="110" cy="35" r="20" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if t_m else "#ffffff"}" />
  <text x="110" y="40" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if t_m else _esc(top)}</text>

  <!-- Bottom circle -->
  <circle cx="110" cy="115" r="20" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if b_m else "#ffffff"}" />
  <text x="110" y="120" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if b_m else _esc(bottom)}</text>

  <!-- Inner box -->
  <rect x="42" y="60" width="46" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if i_m else "#ffffff"}" />
  <text x="65" y="80" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if i_m else _esc(inside)}</text>
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
) -> str:
    """Render 2x2 grid with an attached circular result ear on right."""
    c11_m = _is_missing(r1c1, "r1c1", missing)
    c12_m = _is_missing(r1c2, "r1c2", missing)
    c21_m = _is_missing(r2c1, "r2c1", missing)
    c22_m = _is_missing(r2c2, "r2c2", missing)
    ear_m = _is_missing(ear, "ear", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="220" height="130" viewBox="0 0 220 130" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- 2x2 outer box -->
  <rect x="30" y="25" width="90" height="90" stroke="#222" stroke-width="2.5" fill="#ffffff" />
  <!-- Grid dividers -->
  <line x1="75" y1="25" x2="75" y2="115" stroke="#222" stroke-width="2" />
  <line x1="30" y1="70" x2="120" y2="70" stroke="#222" stroke-width="2" />

  <!-- Cells -->
  <text x="52" y="52" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if c11_m else _esc(r1c1)}</text>
  <text x="97" y="52" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if c12_m else _esc(r1c2)}</text>
  <text x="52" y="97" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if c21_m else _esc(r2c1)}</text>
  <text x="97" y="97" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if c22_m else _esc(r2c2)}</text>

  <!-- Ear connector -->
  <line x1="120" y1="70" x2="145" y2="70" stroke="#222" stroke-width="2" />

  <!-- Side Ear Bubble -->
  <circle cx="168" cy="70" r="22" stroke="#222" stroke-width="2.2" fill="{"#fff9db" if ear_m else "#ffffff"}" />
  <text x="168" y="75" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if ear_m else _esc(ear)}</text>
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
) -> str:
    """Render two top boxes on a T-bar beam hanging to bottom product box."""
    lt_m = _is_missing(left_top, "left_top", missing)
    rt_m = _is_missing(right_top, "right_top", missing)
    b_m = _is_missing(bottom, "bottom", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="200" height="140" viewBox="0 0 200 140" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- T-Bar lines -->
  <line x1="58" y1="50" x2="142" y2="50" stroke="#222" stroke-width="2.5" />
  <line x1="100" y1="50" x2="100" y2="92" stroke="#222" stroke-width="2.5" />

  <!-- Left Top Box -->
  <rect x="36" y="20" width="44" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if lt_m else "#ffffff"}" />
  <text x="58" y="40" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if lt_m else _esc(left_top)}</text>

  <!-- Right Top Box -->
  <rect x="120" y="20" width="44" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if rt_m else "#ffffff"}" />
  <text x="142" y="40" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if rt_m else _esc(right_top)}</text>

  <!-- Bottom Box -->
  <rect x="78" y="92" width="44" height="30" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if b_m else "#ffffff"}" />
  <text x="100" y="112" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if b_m else _esc(bottom)}</text>
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
) -> str:
    """Render triangle with numbers at 3 vertices and center value."""
    t_m = _is_missing(top, "top", missing)
    l_m = _is_missing(left, "left", missing)
    r_m = _is_missing(right, "right", missing)
    c_m = _is_missing(center, "center", missing)

    badge = f'<text x="10" y="16" font-size="11" font-weight="bold" fill="#666">{html.escape(sample_label)}</text>' if sample_label else ""

    return f"""<svg width="200" height="150" viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg">
  {badge}
  <!-- Triangle path -->
  <polygon points="100,24 35,124 165,124" stroke="#222" stroke-width="2.5" fill="none" />

  <!-- Top Vertex Circle -->
  <circle cx="100" cy="24" r="18" stroke="#222" stroke-width="2" fill="{"#fff9db" if t_m else "#ffffff"}" />
  <text x="100" y="29" text-anchor="middle" font-size="12" font-weight="bold" font-family="Arial, sans-serif">{"?" if t_m else _esc(top)}</text>

  <!-- Left Vertex Circle -->
  <circle cx="35" cy="124" r="18" stroke="#222" stroke-width="2" fill="{"#fff9db" if l_m else "#ffffff"}" />
  <text x="35" y="129" text-anchor="middle" font-size="12" font-weight="bold" font-family="Arial, sans-serif">{"?" if l_m else _esc(left)}</text>

  <!-- Right Vertex Circle -->
  <circle cx="165" cy="124" r="18" stroke="#222" stroke-width="2" fill="{"#fff9db" if r_m else "#ffffff"}" />
  <text x="165" y="129" text-anchor="middle" font-size="12" font-weight="bold" font-family="Arial, sans-serif">{"?" if r_m else _esc(right)}</text>

  <!-- Center Box/Value -->
  <rect x="80" y="75" width="40" height="26" rx="3" stroke="#222" stroke-width="2" fill="{"#fff9db" if c_m else "#ffffff"}" />
  <text x="100" y="93" text-anchor="middle" font-size="13" font-weight="bold" font-family="Arial, sans-serif">{"?" if c_m else _esc(center)}</text>
</svg>"""
