"""Library Service for SkuPhase Assessment Studio.

Coordinates:
- Formula queries and searches
- Diagram catalog queries and filtering
- Structured diagram rendering (DiagramRenderSpec)
- Student vs Teacher callout generation and marking scheme key calculation
- Strict SVG sanitization via svg_safety
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.schemas.library import (
    CalloutStyle,
    DiagramMetadata,
    DiagramRenderSpec,
    FormulaItem,
    RenderedDiagramResponse,
)
from app.services.diagram_catalog import (
    get_all_diagrams,
    get_diagram_by_id,
    get_diagrams_by_subject,
    search_diagrams,
)
from app.services.formula_catalog import (
    get_all_formulas,
    get_formula_by_id,
    get_formulas_by_subject,
    search_formulas,
)
from app.services.svg_safety import sanitize_svg


ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
ALPHA_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]


def _format_callout(index: int, style: CalloutStyle) -> str:
    """Format an index (0-based) into a callout symbol."""
    if style == "roman":
        return ROMAN_NUMERALS[index] if index < len(ROMAN_NUMERALS) else f"R{index + 1}"
    elif style == "alpha":
        return ALPHA_LETTERS[index] if index < len(ALPHA_LETTERS) else f"A{index + 1}"
    elif style == "numeric":
        return str(index + 1)
    else:  # question_mark
        return "?"


class LibraryService:
    """Core service for discovering, querying, and rendering visual and formula assets."""

    # ── FORMULA QUERIES ──────────────────────────────────────────────────────

    @staticmethod
    def list_formulas(
        subject: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[FormulaItem]:
        """Return formulas optionally filtered by subject or keyword search."""
        if query and query.strip():
            return search_formulas(query, subject=subject)
        if subject and subject.strip():
            return get_formulas_by_subject(subject)
        return get_all_formulas()

    @staticmethod
    def get_formula(formula_id: str) -> Optional[FormulaItem]:
        """Fetch a formula by its unique ID."""
        return get_formula_by_id(formula_id)

    # ── DIAGRAM CATALOG QUERIES ──────────────────────────────────────────────

    @staticmethod
    def list_diagrams(
        subject: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[DiagramMetadata]:
        """Return registered diagrams optionally filtered by subject or search."""
        if query and query.strip():
            return search_diagrams(query, subject=subject)
        if subject and subject.strip():
            return get_diagrams_by_subject(subject)
        return get_all_diagrams()

    @staticmethod
    def get_diagram_metadata(diagram_id: str) -> Optional[DiagramMetadata]:
        """Fetch metadata for a diagram template."""
        # Try direct ID
        meta = get_diagram_by_id(diagram_id)
        if meta:
            return meta
        # Try by renderer name
        for d in get_all_diagrams():
            if d.renderer == diagram_id:
                return d
        return None

    # ── STRUCTURED DIAGRAM RENDERING ─────────────────────────────────────────

    @classmethod
    def render_diagram(
        cls,
        diagram_id: str,
        spec: DiagramRenderSpec,
    ) -> RenderedDiagramResponse:
        """Render a diagram template with the given specification.

        Computes callout labels for hidden parts, generates marking scheme criteria,
        dispatches to the renderer, and ensures the resulting SVG is strictly sanitized.
        """
        from app.services.diagram_templates import render_archetype

        meta = cls.get_diagram_metadata(diagram_id)
        if not meta:
            raise ValueError(f"Unknown diagram template: '{diagram_id}'")

        renderer_key = meta.renderer

        # Validate and sanitize parameters against catalog definition
        allowed_field_names = {f.name for f in meta.fields}
        sanitized_params: Dict[str, Any] = {}

        for k, v in spec.params.items():
            if k.startswith("_"):
                continue
            if k not in allowed_field_names:
                continue
            val_str = str(v)
            if len(val_str) > 60:
                val_str = val_str[:60]
            sanitized_params[k] = val_str

        # Fill defaults for missing fields
        for field in meta.fields:
            if field.name not in sanitized_params:
                sanitized_params[field.name] = field.default

        render_params: Dict[str, Any] = sanitized_params
        marking_points: List[str] = []

        if spec.mode == "exam" and spec.hidden_parts and meta:
            # Map hidden part keys to callout symbols and marking points
            hideable_map = {hp.key: hp for hp in meta.hideable_parts}
            unknown_parts = [part for part in spec.hidden_parts if part not in hideable_map]
            if unknown_parts:
                raise ValueError(
                    f"Unknown hideable part(s) for '{diagram_id}': {', '.join(unknown_parts)}"
                )
            callout_map: Dict[str, str] = {}

            for idx, part_key in enumerate(spec.hidden_parts):
                symbol = _format_callout(idx, spec.callout_style)
                callout_map[part_key] = symbol

                # Build marking scheme line
                part_def = hideable_map.get(part_key)
                answer_text = part_def.default_answer if part_def else part_key
                marking_points.append(f"1 mark — Part {symbol}: {answer_text}")

            render_params["_callouts"] = callout_map
            render_params["missing"] = ",".join(spec.hidden_parts)
            # Override fields matching hidden part keys with the callout symbol
            for part_key, symbol in callout_map.items():
                if part_key in render_params or any(f.name == part_key for f in meta.fields):
                    render_params[part_key] = symbol
        else:
            render_params["missing"] = ""

        if spec.sample_label:
            render_params["sample_label"] = spec.sample_label

        # Render raw SVG
        raw_svg = render_archetype(renderer_key, render_params)
        safe_svg = sanitize_svg(raw_svg)
        if not safe_svg:
            raise ValueError(f"Renderer for '{diagram_id}' produced invalid or unsafe SVG")

        return RenderedDiagramResponse(
            svg=safe_svg,
            marking_points=marking_points,
            diagram_id=diagram_id,
            mode=spec.mode,
        )
