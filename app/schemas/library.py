"""Schemas for SkuPhase Visual & Formula Assessment Studio Library.

Provides structured types for:
- Diagram rendering specifications (modes, callout styles, hidden parts)
- Diagram catalog metadata (topics, class levels, hideable parts, parameters)
- Formula catalog items (canonical LaTeX, variable descriptions, units)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

CalloutStyle = Literal["roman", "alpha", "numeric", "question_mark"]
DiagramMode = Literal["study", "exam"]


class DiagramRenderSpec(BaseModel):
    """Specification for rendering an assessment diagram.

    Controls teacher vs student display states, callouts, and parametric values.
    """

    mode: DiagramMode = Field(
        default="exam",
        description="'study' shows full labels; 'exam' masks selected parts with callouts",
    )
    hidden_parts: List[str] = Field(
        default_factory=list,
        description="Keys of parts/labels to hide or replace with callouts",
    )
    callout_style: CalloutStyle = Field(
        default="roman",
        description="Style of marker: 'roman' (I, II, III), 'alpha' (A, B, C), 'numeric' (1, 2, 3), or 'question_mark' (?)",
    )
    show_values: bool = Field(
        default=True,
        description="Whether to show numerical measurement values or hide them",
    )
    sample_label: str = Field(
        default="",
        description="Optional badge text displayed in header (e.g. 'Fig. 1.2')",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parametric dimension, node, or component overrides",
    )


class HideablePart(BaseModel):
    """Definition of an anatomical or structural part that can be tested in an exam."""

    key: str = Field(..., description="Unique code for this part in the diagram")
    label: str = Field(..., description="Standard human-readable name of the part")
    default_answer: str = Field(
        default="",
        description="Expected model answer / marking text when this part is tested",
    )


class DiagramField(BaseModel):
    """A configurable parameter for a diagram template."""

    name: str = Field(..., description="Parameter key name")
    label: str = Field(..., description="Human-readable input label")
    default: str = Field(..., description="Default value")
    description: Optional[str] = Field(None, description="Guidance tooltip or description")


class DiagramMetadata(BaseModel):
    """Catalog metadata describing a diagram template."""

    id: str = Field(..., description="Unique slug (e.g. 'physics.simple_pulley')")
    title: str = Field(..., description="Display title for teachers")
    subject: str = Field(..., description="Subject: Physics, Chemistry, Biology, Agricultural Science, Mathematics")
    category: str = Field(..., description="Subcategory: Mechanics, Optics, Cells, Apparatus, Farm Tools, etc.")
    topics: List[str] = Field(default_factory=list, description="Curriculum topics this diagram relates to")
    class_levels: List[str] = Field(default_factory=list, description="Target grades: JSS 1-3, SSS 1-3, Primary 1-6")
    renderer: str = Field(..., description="Internal generator function key in diagram_templates")
    fields: List[DiagramField] = Field(default_factory=list, description="Parametric inputs")
    hideable_parts: List[HideablePart] = Field(default_factory=list, description="Parts that can be masked for exam mode")
    accessibility_desc: str = Field(..., description="Detailed text alternative for accessibility and print fallback")
    version: int = Field(default=1, description="Schema/renderer version")


class FormulaVariable(BaseModel):
    """Variable explanation and unit for a formula."""

    symbol: str = Field(..., description="Variable symbol (e.g. 'v', 'm', 'R')")
    name: str = Field(..., description="Name (e.g. 'Final velocity', 'Mass')")
    unit: Optional[str] = Field(None, description="Standard SI or measurement unit (e.g. 'm/s', 'kg', 'Ω')")


class FormulaItem(BaseModel):
    """A reusable curriculum equation or formula preset."""

    id: str = Field(..., description="Unique formula identifier (e.g. 'physics.suvat_v')")
    name: str = Field(..., description="Friendly title (e.g. 'First Equation of Linear Motion')")
    subject: str = Field(..., description="Subject: Mathematics, Physics, Chemistry, Further Mathematics")
    topic: str = Field(..., description="Curriculum topic (e.g. 'Kinematics', 'Electricity', 'Stoichiometry')")
    latex: str = Field(..., description="Canonical LaTeX string to insert into editor")
    display_latex: Optional[str] = Field(None, description="Optional presentation LaTeX if different from raw insert")
    class_levels: List[str] = Field(default_factory=list, description="Applicable grade levels")
    variables: List[FormulaVariable] = Field(default_factory=list, description="Breakdown of formula symbols")
    description: Optional[str] = Field(None, description="Usage note or condition of validity")


class RenderedDiagramResponse(BaseModel):
    """Result of rendering a diagram specification."""

    svg: str = Field(..., description="Sanitized SVG document markup")
    marking_points: List[str] = Field(
        default_factory=list,
        description="Suggested line-by-line marking scheme entries for masked callouts",
    )
    diagram_id: str = Field(..., description="ID of the diagram rendered")
    mode: DiagramMode = Field(..., description="Rendered mode ('study' or 'exam')")
