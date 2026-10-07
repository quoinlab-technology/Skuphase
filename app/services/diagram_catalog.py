"""Diagram Catalog Registry for SkuPhase Assessment Studio.

Defines metadata, parameter schemas, hideable anatomical/structural parts,
topics, and accessibility descriptions for all diagram templates.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from app.schemas.library import DiagramField, DiagramMetadata, HideablePart

_CATALOG: Dict[str, DiagramMetadata] = {}


def register_diagram(diag: DiagramMetadata) -> None:
    """Register a diagram template in the catalog."""
    _CATALOG[diag.id] = diag


# ─────────────────────────────────────────────────────────────────────────────
# 1. MATHEMATICS & QUANTITATIVE REASONING (Existing 10 Archetypes)
# ─────────────────────────────────────────────────────────────────────────────

register_diagram(
    DiagramMetadata(
        id="math.horizontal_y_fork",
        title="Horizontal Y-Fork (Circle → 2 Boxes)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Number Patterns", "Visual Reasoning", "Operations"],
        class_levels=["Primary 4", "Primary 5", "Primary 6", "JSS 1"],
        renderer="horizontal_y_fork",
        fields=[
            DiagramField(name="parent", label="Parent Circle", default="12"),
            DiagramField(name="child_top", label="Top Child Box", default="4"),
            DiagramField(name="child_bottom", label="Bottom Child Box", default="8"),
        ],
        hideable_parts=[
            HideablePart(key="parent", label="Parent Circle", default_answer="12"),
            HideablePart(key="child_top", label="Top Child Box", default_answer="4"),
            HideablePart(key="child_bottom", label="Bottom Child Box", default_answer="8"),
        ],
        accessibility_desc="Quantitative reasoning horizontal Y-fork connecting a parent circle to two child square boxes.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.fraction_branch",
        title="Fraction Branch Tree (2 Fractions → 1 Result)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Fractions", "Visual Reasoning", "Arithmetic"],
        class_levels=["Primary 5", "Primary 6", "JSS 1"],
        renderer="fraction_branch",
        fields=[
            DiagramField(name="frac_left_num", label="Left Numerator", default="1"),
            DiagramField(name="frac_left_den", label="Left Denominator", default="2"),
            DiagramField(name="frac_right_num", label="Right Numerator", default="1"),
            DiagramField(name="frac_right_den", label="Right Denominator", default="4"),
            DiagramField(name="frac_bottom_num", label="Result Numerator", default="3"),
            DiagramField(name="frac_bottom_den", label="Result Denominator", default="4"),
        ],
        hideable_parts=[
            HideablePart(key="frac_bottom_num", label="Result Numerator", default_answer="3"),
            HideablePart(key="frac_bottom_den", label="Result Denominator", default_answer="4"),
            HideablePart(key="frac_left_num", label="Left Numerator", default_answer="1"),
        ],
        accessibility_desc="Two top fraction boxes branching down through connecting lines to a single result fraction box.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.m_network",
        title="M-Shape / W-Shape Network (5 Nodes)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Number Patterns", "Visual Reasoning"],
        class_levels=["Primary 4", "Primary 5", "Primary 6", "JSS 1"],
        renderer="m_network",
        fields=[
            DiagramField(name="tl", label="Top Left", default="3"),
            DiagramField(name="bl", label="Bottom Left", default="9"),
            DiagramField(name="center", label="Center Hub", default="15"),
            DiagramField(name="tr", label="Top Right", default="6"),
            DiagramField(name="br", label="Bottom Right", default="18"),
        ],
        hideable_parts=[
            HideablePart(key="center", label="Center Hub", default_answer="15"),
            HideablePart(key="tl", label="Top Left Node", default_answer="3"),
            HideablePart(key="tr", label="Top Right Node", default_answer="6"),
        ],
        accessibility_desc="Five interconnected numbered circular nodes arranged in an M or W lattice.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.power_fork",
        title="Power Circle + Fork (Base^Exp → Mid → 2 Forks)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Indices", "Powers", "Visual Reasoning"],
        class_levels=["Primary 6", "JSS 1", "JSS 2"],
        renderer="power_fork",
        fields=[
            DiagramField(name="base", label="Base Circle", default="2"),
            DiagramField(name="exp", label="Exponent Badge", default="3"),
            DiagramField(name="mid_box", label="Middle Box", default="8"),
            DiagramField(name="fork1", label="Top Fork", default="4"),
            DiagramField(name="fork2", label="Bottom Fork", default="2"),
        ],
        hideable_parts=[
            HideablePart(key="mid_box", label="Middle Box", default_answer="8"),
            HideablePart(key="fork1", label="Top Fork", default_answer="4"),
            HideablePart(key="fork2", label="Bottom Fork", default_answer="2"),
        ],
        accessibility_desc="Power circle with base and small superscript badge connecting to middle box and splitting into two fork boxes.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.compass_cross",
        title="4-Way Compass Cross (Hub + 4 Arms)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Arithmetic Operations", "Visual Reasoning"],
        class_levels=["Primary 5", "Primary 6", "JSS 1"],
        renderer="compass_cross",
        fields=[
            DiagramField(name="center", label="Center Hub", default="20"),
            DiagramField(name="top", label="North Arm", default="5"),
            DiagramField(name="bottom", label="South Arm", default="10"),
            DiagramField(name="left", label="West Arm", default="2"),
            DiagramField(name="right", label="East Arm", default="4"),
            DiagramField(name="op_top", label="Top Operator", default="+"),
            DiagramField(name="op_bot", label="Bottom Operator", default="×"),
        ],
        hideable_parts=[
            HideablePart(key="center", label="Center Hub", default_answer="20"),
            HideablePart(key="top", label="North Arm", default_answer="5"),
            HideablePart(key="bottom", label="South Arm", default_answer="10"),
        ],
        accessibility_desc="Central hub surrounded by four directional circular arms with mathematical operator signs.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.horseshoe",
        title="Horseshoe U-Shape (Top-L, Top-R, Trough)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Multiplication", "Visual Reasoning"],
        class_levels=["Primary 4", "Primary 5", "Primary 6"],
        renderer="horseshoe",
        fields=[
            DiagramField(name="left", label="Left Circle", default="7"),
            DiagramField(name="right", label="Right Circle", default="9"),
            DiagramField(name="bottom", label="Bottom Trough", default="63"),
        ],
        hideable_parts=[
            HideablePart(key="bottom", label="Bottom Result", default_answer="63"),
            HideablePart(key="left", label="Left Circle", default_answer="7"),
            HideablePart(key="right", label="Right Circle", default_answer="9"),
        ],
        accessibility_desc="U-shaped curved band connecting two top circular nodes down to a bottom result box.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.arc_c",
        title="Arc C-Shape (Top, Bottom, Inner Box)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Division", "Ratios", "Visual Reasoning"],
        class_levels=["Primary 4", "Primary 5", "Primary 6"],
        renderer="arc_c",
        fields=[
            DiagramField(name="top", label="Top Node", default="15"),
            DiagramField(name="bottom", label="Bottom Node", default="5"),
            DiagramField(name="inside", label="Inner Box", default="3"),
        ],
        hideable_parts=[
            HideablePart(key="inside", label="Inner Result Box", default_answer="3"),
            HideablePart(key="top", label="Top Node", default_answer="15"),
            HideablePart(key="bottom", label="Bottom Node", default_answer="5"),
        ],
        accessibility_desc="C-shaped curved arc spanning between top and bottom circular nodes with an inner value box.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.grid_with_ear",
        title="2x2 Grid with Result Ear",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Matrices", "Determinants", "Patterns"],
        class_levels=["Primary 5", "Primary 6", "JSS 1"],
        renderer="grid_with_ear",
        fields=[
            DiagramField(name="r1c1", label="Row 1, Col 1", default="2"),
            DiagramField(name="r1c2", label="Row 1, Col 2", default="4"),
            DiagramField(name="r2c1", label="Row 2, Col 1", default="3"),
            DiagramField(name="r2c2", label="Row 2, Col 2", default="6"),
            DiagramField(name="ear", label="Result Ear", default="24"),
        ],
        hideable_parts=[
            HideablePart(key="ear", label="Result Ear Bubble", default_answer="24"),
            HideablePart(key="r1c1", label="Row 1 Col 1", default_answer="2"),
        ],
        accessibility_desc="Four cells in a 2-by-2 square grid connected by a pointer to a protruding circular result bubble.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.tbar_multiplier",
        title="T-Bar Multiplier (2 Top Boxes → Beam to Product)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Multiplication", "Factors", "Visual Reasoning"],
        class_levels=["Primary 4", "Primary 5", "Primary 6"],
        renderer="tbar_multiplier",
        fields=[
            DiagramField(name="left_top", label="Left Top Box", default="6"),
            DiagramField(name="right_top", label="Right Top Box", default="7"),
            DiagramField(name="bottom", label="Bottom Product", default="42"),
        ],
        hideable_parts=[
            HideablePart(key="bottom", label="Bottom Product", default_answer="42"),
            HideablePart(key="left_top", label="Left Top Factor", default_answer="6"),
            HideablePart(key="right_top", label="Right Top Factor", default_answer="7"),
        ],
        accessibility_desc="Two top factor boxes resting on a horizontal beam dropping to a bottom product box.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.triangle_puzzle",
        title="Triangle Puzzle (3 Vertices + Center Value)",
        subject="Mathematics",
        category="Quantitative Reasoning",
        topics=["Geometry", "Arithmetic", "Visual Reasoning"],
        class_levels=["Primary 4", "Primary 5", "Primary 6", "JSS 1"],
        renderer="triangle_puzzle",
        fields=[
            DiagramField(name="top", label="Top Vertex", default="4"),
            DiagramField(name="left", label="Left Vertex", default="6"),
            DiagramField(name="right", label="Right Vertex", default="8"),
            DiagramField(name="center", label="Center Value", default="24"),
        ],
        hideable_parts=[
            HideablePart(key="center", label="Center Value", default_answer="24"),
            HideablePart(key="top", label="Top Vertex", default_answer="4"),
            HideablePart(key="left", label="Left Vertex", default_answer="6"),
            HideablePart(key="right", label="Right Vertex", default_answer="8"),
        ],
        accessibility_desc="Equilateral triangle with circles at each of the 3 corners and a rectangular box in the center.",
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. MATHEMATICS (Geometry & Trigonometry)
# ─────────────────────────────────────────────────────────────────────────────

register_diagram(
    DiagramMetadata(
        id="math.right_triangle",
        title="Right-Angled Triangle (Pythagoras & Trigonometry)",
        subject="Mathematics",
        category="Geometry & Trigonometry",
        topics=["Pythagoras Theorem", "Trigonometric Ratios (SOHCAHTOA)", "Mensuration"],
        class_levels=["JSS 2", "JSS 3", "SSS 1", "SSS 2"],
        renderer="right_triangle",
        fields=[
            DiagramField(name="base_label", label="Base Side", default="4 cm"),
            DiagramField(name="height_label", label="Height Side", default="3 cm"),
            DiagramField(name="hypotenuse_label", label="Hypotenuse", default="5 cm"),
            DiagramField(name="angle_theta", label="Base Angle θ", default="θ"),
        ],
        hideable_parts=[
            HideablePart(key="hypotenuse", label="Hypotenuse Side", default_answer="5 cm"),
            HideablePart(key="angle_theta", label="Angle θ", default_answer="36.9°"),
            HideablePart(key="height", label="Opposite Height", default_answer="3 cm"),
        ],
        accessibility_desc="Right-angled triangle with square 90-degree corner indicator, labeled base, height, hypotenuse, and acute angle theta.",
    )
)

register_diagram(
    DiagramMetadata(
        id="math.venn_2set",
        title="2-Set Venn Diagram (Universal Set + Sets A & B)",
        subject="Mathematics",
        category="Set Theory",
        topics=["Sets", "Venn Diagrams", "Probability"],
        class_levels=["JSS 2", "JSS 3", "SSS 1"],
        renderer="venn_2set",
        fields=[
            DiagramField(name="set_a_label", label="Set A Label", default="A"),
            DiagramField(name="set_b_label", label="Set B Label", default="B"),
            DiagramField(name="only_a", label="Only A Count/Elements", default="12"),
            DiagramField(name="intersection", label="A ∩ B (Both)", default="5"),
            DiagramField(name="only_b", label="Only B Count/Elements", default="8"),
            DiagramField(name="neither", label="Outside (Neither)", default="3"),
        ],
        hideable_parts=[
            HideablePart(key="intersection", label="Intersection (A ∩ B)", default_answer="5"),
            HideablePart(key="only_a", label="Set A only", default_answer="12"),
            HideablePart(key="only_b", label="Set B only", default_answer="8"),
            HideablePart(key="neither", label="Complement (Neither)", default_answer="3"),
        ],
        accessibility_desc="Universal rectangle containing two overlapping circular sets A and B with marked intersection and outside region.",
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. PHYSICS
# ─────────────────────────────────────────────────────────────────────────────

register_diagram(
    DiagramMetadata(
        id="physics.electric_circuit",
        title="Electric Circuit (Series / Parallel with Meter)",
        subject="Physics",
        category="Current Electricity",
        topics=["Current Electricity", "Ohm's Law", "Resistors in Series"],
        class_levels=["JSS 2", "JSS 3", "SSS 1", "SSS 2"],
        renderer="electric_circuit",
        fields=[
            DiagramField(name="battery", label="Battery Voltage", default="12 V"),
            DiagramField(name="resistor", label="Resistor Label", default="R = 4 Ω"),
            DiagramField(name="current", label="Current Flow Indicator", default="I"),
        ],
        hideable_parts=[
            HideablePart(key="resistor", label="Resistor Value", default_answer="4 Ω"),
            HideablePart(key="battery", label="Battery Voltage", default_answer="12 V"),
            HideablePart(key="current", label="Ammeter Reading", default_answer="3 A"),
        ],
        accessibility_desc="Schematic electric circuit with DC battery cell, switch, series resistor, and current flow indicator.",
    )
)

register_diagram(
    DiagramMetadata(
        id="physics.optical_ray",
        title="Convex Lens Ray Diagram",
        subject="Physics",
        category="Optics & Light",
        topics=["Reflection and Refraction", "Lenses", "Light Rays"],
        class_levels=["SSS 1", "SSS 2"],
        renderer="optical_ray",
        fields=[
            DiagramField(name="object_label", label="Object Arrow", default="Object"),
            DiagramField(name="image_label", label="Image Arrow", default="Image"),
            DiagramField(name="focal_length", label="Focal Length Marker", default="F"),
        ],
        hideable_parts=[
            HideablePart(key="image", label="Formed Image", default_answer="Real, inverted, magnified image"),
            HideablePart(key="focal_length", label="Principal Focus F", default_answer="Focus point F"),
        ],
        accessibility_desc="Principal horizontal optical axis, converging convex lens, upright object arrow, two refracted rays passing through focal point, and inverted real image arrow.",
    )
)

register_diagram(
    DiagramMetadata(
        id="physics.simple_pulley",
        title="Simple Pulley System (Effort & Load)",
        subject="Physics",
        category="Mechanics & Machines",
        topics=["Simple Machines", "Pulleys", "Mechanical Advantage"],
        class_levels=["JSS 1", "JSS 2", "SSS 1"],
        renderer="pulley_system",
        fields=[
            DiagramField(name="load_label", label="Load Weight", default="L = 100 N"),
            DiagramField(name="effort_label", label="Effort Force", default="E"),
            DiagramField(name="system_type", label="Pulley Type", default="Single Movable"),
        ],
        hideable_parts=[
            HideablePart(key="effort", label="Effort Value E", default_answer="50 N"),
            HideablePart(key="load", label="Load Value L", default_answer="100 N"),
        ],
        accessibility_desc="Overhead ceiling bracket supporting pulley wheel with wrapped rope, hanging load block, and effort rope with pull arrow.",
    )
)

register_diagram(
    DiagramMetadata(
        id="physics.inclined_plane",
        title="Inclined Plane (Forces & Resolution)",
        subject="Physics",
        category="Mechanics & Dynamics",
        topics=["Simple Machines", "Friction", "Resolution of Forces"],
        class_levels=["SSS 1", "SSS 2"],
        renderer="inclined_plane",
        fields=[
            DiagramField(name="angle", label="Incline Angle θ", default="30°"),
            DiagramField(name="mass", label="Object Mass / Weight", default="W = mg"),
            DiagramField(name="friction", label="Friction Force", default="F_r"),
        ],
        hideable_parts=[
            HideablePart(key="normal_reaction", label="Normal Reaction R", default_answer="R = mg cos θ"),
            HideablePart(key="parallel_weight", label="Parallel Weight Component", default_answer="mg sin θ"),
            HideablePart(key="friction", label="Frictional Force", default_answer="μR"),
        ],
        accessibility_desc="Right-angled inclined ramp with angle theta, rectangular block on slope, downward gravity arrow, and normal reaction perpendicular to ramp.",
    )
)

register_diagram(
    DiagramMetadata(
        id="physics.simple_pendulum",
        title="Simple Pendulum (Length & Oscillation)",
        subject="Physics",
        category="Waves & Oscillations",
        topics=["Simple Harmonic Motion", "Oscillations", "Periodic Time"],
        class_levels=["SSS 1", "SSS 2"],
        renderer="simple_pendulum",
        fields=[
            DiagramField(name="length", label="String Length L", default="L = 1.0 m"),
            DiagramField(name="bob_label", label="Pendulum Bob", default="Bob (m)"),
            DiagramField(name="angle", label="Displacement Angle θ", default="θ"),
        ],
        hideable_parts=[
            HideablePart(key="mean_position", label="Equilibrium / Mean Position", default_answer="Lowest center position"),
            HideablePart(key="length", label="Effective Length L", default_answer="1.0 m"),
        ],
        accessibility_desc="Fixed rigid clamp supporting an inextensible light string of length L attached to a suspended spherical metal bob displaced at angle theta.",
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# 4. CHEMISTRY
# ─────────────────────────────────────────────────────────────────────────────

register_diagram(
    DiagramMetadata(
        id="chem.burette",
        title="Burette & Titration Setup",
        subject="Chemistry",
        category="Laboratory Apparatus",
        topics=["Volumetric Analysis", "Acids, Bases & Salts", "Apparatus"],
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        renderer="burette",
        fields=[
            DiagramField(name="volume", label="Initial / Final Volume", default="25.0 mL"),
            DiagramField(name="titre", label="Titre Flask Label", default="Conical Flask"),
            DiagramField(name="indicator", label="Acid / Base Solution", default="Standard Acid"),
        ],
        hideable_parts=[
            HideablePart(key="burette", label="Burette Tube & Meniscus", default_answer="Burette"),
            HideablePart(key="flask", label="Conical / Erlenmeyer Flask", default_answer="Conical Flask"),
            HideablePart(key="stopcock", label="Stopcock Tap", default_answer="Stopcock"),
        ],
        accessibility_desc="Graduated vertical glass burette clamped to retort stand with stopcock positioned above a conical titration flask.",
    )
)

register_diagram(
    DiagramMetadata(
        id="chem.liebig_condenser",
        title="Liebig Condenser (Distillation)",
        subject="Chemistry",
        category="Laboratory Apparatus",
        topics=["Separation Techniques", "Distillation", "Apparatus"],
        class_levels=["JSS 2", "SSS 1", "SSS 2"],
        renderer="liebig_condenser",
        fields=[
            DiagramField(name="water_in", label="Water Inlet", default="Water In"),
            DiagramField(name="water_out", label="Water Outlet", default="Water Out"),
            DiagramField(name="vapour", label="Distillate Vapour", default="Vapour"),
        ],
        hideable_parts=[
            HideablePart(key="water_in", label="Cold Water Inlet (Bottom)", default_answer="Cold water inlet"),
            HideablePart(key="water_out", label="Warm Water Outlet (Top)", default_answer="Water outlet"),
            HideablePart(key="condenser_tube", label="Inner Condenser Tube", default_answer="Condensing tube"),
        ],
        accessibility_desc="Slanted double-jacketed glass Liebig condenser showing inner vapor tube and outer cooling water jacket with lower inlet and upper outlet.",
    )
)

register_diagram(
    DiagramMetadata(
        id="chem.electrolysis_cell",
        title="Electrolytic Cell (Anode & Cathode)",
        subject="Chemistry",
        category="Electrochemistry",
        topics=["Electrolysis", "Electrochemistry", "Redox"],
        class_levels=["SSS 2", "SSS 3"],
        renderer="electrolysis_cell",
        fields=[
            DiagramField(name="anode_label", label="Anode (+)", default="Anode (+)"),
            DiagramField(name="cathode_label", label="Cathode (-)", default="Cathode (-)"),
            DiagramField(name="electrolyte", label="Electrolyte Solution", default="CuSO4 (aq)"),
        ],
        hideable_parts=[
            HideablePart(key="anode", label="Positive Electrode (Anode)", default_answer="Anode (positive electrode where oxidation occurs)"),
            HideablePart(key="cathode", label="Negative Electrode (Cathode)", default_answer="Cathode (negative electrode where reduction occurs)"),
            HideablePart(key="electrolyte", label="Electrolyte Bath", default_answer="Electrolyte solution"),
        ],
        accessibility_desc="Beaker containing chemical electrolyte solution with two submerged electrodes connected via wires to a DC battery power supply.",
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# 5. BIOLOGY
# ─────────────────────────────────────────────────────────────────────────────

register_diagram(
    DiagramMetadata(
        id="bio.cell",
        title="Plant & Animal Cell Structure",
        subject="Biology",
        category="Cell Biology",
        topics=["Cell Structure and Organization", "Microscopy"],
        class_levels=["JSS 1", "JSS 2", "SSS 1"],
        renderer="biology_cell",
        fields=[
            DiagramField(name="cell_type", label="Cell Type", default="Plant Cell"),
            DiagramField(name="nucleus", label="Nucleus Label", default="Nucleus"),
            DiagramField(name="vacuole", label="Vacuole Label", default="Vacuole"),
        ],
        hideable_parts=[
            HideablePart(key="nucleus", label="Cell Nucleus", default_answer="Nucleus (contains genetic material DNA)"),
            HideablePart(key="vacuole", label="Large Sap Vacuole", default_answer="Vacuole (maintains cell turgidity)"),
            HideablePart(key="cell_wall", label="Cellulose Cell Wall", default_answer="Cell Wall (provides structural rigidity)"),
            HideablePart(key="chloroplast", label="Chloroplasts", default_answer="Chloroplast (site of photosynthesis)"),
        ],
        accessibility_desc="Cross-section diagram of a eukaryotic plant cell showing cell wall, plasma membrane, large central vacuole, green chloroplasts, and nucleus.",
    )
)

register_diagram(
    DiagramMetadata(
        id="bio.flower_structure",
        title="Longitudinal Section of a Flower",
        subject="Biology",
        category="Plant Anatomy",
        topics=["Plant Reproduction", "Flower Structure", "Pollination"],
        class_levels=["JSS 2", "SSS 1", "SSS 2"],
        renderer="flower_structure",
        fields=[
            DiagramField(name="flower_title", label="Flower Type", default="Dicotyledonous Flower"),
        ],
        hideable_parts=[
            HideablePart(key="anther", label="Anther (Male Stamen)", default_answer="Anther (produces pollen grains)"),
            HideablePart(key="stigma", label="Stigma (Female Carpel)", default_answer="Stigma (receptive surface for pollen)"),
            HideablePart(key="ovary", label="Ovary with Ovules", default_answer="Ovary (develops into fruit after fertilization)"),
            HideablePart(key="petal", label="Petal / Corolla", default_answer="Petal (attracts pollinating insects)"),
            HideablePart(key="sepal", label="Sepal / Calyx", default_answer="Sepal (protects flower bud)"),
        ],
        accessibility_desc="Longitudinal section of an insect-pollinated flower displaying sepals, petals, stamen (filament and anther), and carpel (stigma, style, and ovary).",
    )
)

register_diagram(
    DiagramMetadata(
        id="bio.nephron",
        title="Mammalian Nephron (Kidney Excretory Unit)",
        subject="Biology",
        category="Human Physiology",
        topics=["Excretion", "Kidney Function", "Homeostasis"],
        class_levels=["SSS 2", "SSS 3"],
        renderer="nephron_unit",
        fields=[
            DiagramField(name="organ", label="Organ Title", default="Nephron Structure"),
        ],
        hideable_parts=[
            HideablePart(key="bowmans_capsule", label="Bowman's Capsule", default_answer="Bowman's capsule (site of ultrafiltration)"),
            HideablePart(key="glomerulus", label="Glomerulus Capillary Bed", default_answer="Glomerulus"),
            HideablePart(key="loop_of_henle", label="Loop of Henle", default_answer="Loop of Henle (water reabsorption and osmoregulation)"),
            HideablePart(key="collecting_duct", label="Collecting Duct", default_answer="Collecting duct (transports urine to renal pelvis)"),
        ],
        accessibility_desc="Diagram of a single kidney nephron detailing the cup-like Bowman's capsule with enclosed glomerulus, convoluted tubules, hairpin Loop of Henle, and collecting duct.",
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# 6. AGRICULTURAL SCIENCE
# ─────────────────────────────────────────────────────────────────────────────

register_diagram(
    DiagramMetadata(
        id="agric.knapsack_sprayer",
        title="Knapsack Sprayer (Crop Protection Tool)",
        subject="Agricultural Science",
        category="Farm Tools & Equipment",
        topics=["Farm Tools and Machinery", "Crop Protection", "Pesticide Application"],
        class_levels=["JSS 1", "JSS 2", "SSS 1"],
        renderer="knapsack_sprayer",
        fields=[
            DiagramField(name="tool_name", label="Equipment Name", default="Knapsack Sprayer"),
        ],
        hideable_parts=[
            HideablePart(key="nozzle", label="Spray Nozzle", default_answer="Nozzle (atomizes spray liquid into fine droplets)"),
            HideablePart(key="tank", label="Chemical Solution Tank", default_answer="Chemical tank / container"),
            HideablePart(key="lance", label="Trigger Lance / Rod", default_answer="Spray lance"),
            HideablePart(key="pump_lever", label="Pump Operating Lever", default_answer="Pump handle / lever"),
        ],
        accessibility_desc="Side-view diagram of a manual backpack knapsack sprayer showing liquid tank, shoulder straps, pump handle, flexible hose, trigger lance, and atomizing nozzle.",
    )
)

register_diagram(
    DiagramMetadata(
        id="agric.soil_profile",
        title="Soil Profile (Horizons O, A, B, C, R)",
        subject="Agricultural Science",
        category="Soil Science",
        topics=["Soil Formation", "Soil Horizons", "Crop Production"],
        class_levels=["JSS 2", "SSS 1", "SSS 2"],
        renderer="soil_profile",
        fields=[
            DiagramField(name="profile_title", label="Profile Label", default="Ideal Soil Profile"),
        ],
        hideable_parts=[
            HideablePart(key="horizon_o", label="Horizon O (Organic Layer)", default_answer="Horizon O (humus and decomposing organic matter)"),
            HideablePart(key="horizon_a", label="Horizon A (Topsoil)", default_answer="Horizon A (topsoil, mineral rich with root activity)"),
            HideablePart(key="horizon_b", label="Horizon B (Subsoil)", default_answer="Horizon B (subsoil, zone of accumulation)"),
            HideablePart(key="horizon_c", label="Horizon C (Parent Rock)", default_answer="Horizon C (weathered parent rock material)"),
            HideablePart(key="horizon_r", label="Horizon R (Bedrock)", default_answer="Horizon R (unweathered solid bedrock)"),
        ],
        accessibility_desc="Vertical cross-section of a soil column showing progressive depth layers from surface organic litter (O) down to solid bedrock (R).",
    )
)

register_diagram(
    DiagramMetadata(
        id="agric.ruminant_stomach",
        title="Ruminant Digestive System (4 Compartments)",
        subject="Agricultural Science",
        category="Animal Science",
        topics=["Anatomy and Physiology of Farm Animals", "Digestive System"],
        class_levels=["JSS 3", "SSS 1", "SSS 2"],
        renderer="ruminant_stomach",
        fields=[
            DiagramField(name="animal", label="Animal Type", default="Ruminant (Cow/Sheep)"),
        ],
        hideable_parts=[
            HideablePart(key="rumen", label="Rumen (Paunch)", default_answer="Rumen (largest compartment, microbial fermentation)"),
            HideablePart(key="reticulum", label="Reticulum (Honeycomb)", default_answer="Reticulum (hardware compartment, regurgitation of cud)"),
            HideablePart(key="omasum", label="Omasum (Manyplies)", default_answer="Omasum (water and nutrient absorption)"),
            HideablePart(key="abomasum", label="Abomasum (True Stomach)", default_answer="Abomasum (true enzymatic glandular digestion)"),
        ],
        accessibility_desc="Anatomical diagram of a compound ruminant stomach detailing the esophagus leading into the rumen, reticulum, omasum, and abomasum.",
    )
)


# ─────────────────────────────────────────────────────────────────────────────
# CATALOG QUERY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# 6. EXPANDED SECONDARY SCIENCE & AGRICULTURE (PHASE 2 COMPREHENSIVE SET)
# ─────────────────────────────────────────────────────────────────────────────

register_diagram(
    DiagramMetadata(
        id="physics.triangular_prism",
        title="Triangular Prism (Refraction & Dispersion)",
        subject="Physics",
        category="Optics & Light",
        topics=["Refraction", "Dispersion of Light", "Snell's Law"],
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        renderer="triangular_prism",
        fields=[
            DiagramField(name="base_angle", label="Base Angles", default="60°"),
            DiagramField(name="apex_angle", label="Apex Angle (A)", default="60°"),
            DiagramField(name="ray_color", label="Ray Color", default="#dc2626"),
        ],
        hideable_parts=[
            HideablePart(key="incident_ray", label="Incident Ray", default_answer="Incident light ray"),
            HideablePart(key="normal", label="Normal Line", default_answer="Normal perpendicular to glass face"),
            HideablePart(key="refracted_ray", label="Refracted Ray", default_answer="Refracted ray inside prism"),
            HideablePart(key="emergent_ray", label="Emergent Ray", default_answer="Emergent ray exiting prism"),
            HideablePart(key="deviation_angle", label="Angle of Deviation (D)", default_answer="Angle of deviation"),
        ],
        accessibility_desc="Equilateral glass prism with light ray refracting at first face and emerging at second face with marked deviation angle.",
    )
)

register_diagram(
    DiagramMetadata(
        id="chem.separating_funnel",
        title="Separating Funnel (Immiscible Liquids)",
        subject="Chemistry",
        category="Laboratory Apparatus",
        topics=["Separation Techniques", "Immiscible Liquids", "Apparatus"],
        class_levels=["JSS 2", "SSS 1", "SSS 2"],
        renderer="separating_funnel",
        fields=[
            DiagramField(name="upper_liquid", label="Upper Liquid", default="Kerosene / Oil"),
            DiagramField(name="lower_liquid", label="Lower Liquid", default="Water"),
        ],
        hideable_parts=[
            HideablePart(key="stopper", label="Glass Stopper", default_answer="Glass stopper"),
            HideablePart(key="upper_layer", label="Upper Liquid Layer", default_answer="Upper layer (less dense liquid, e.g. oil)"),
            HideablePart(key="interface", label="Meniscus / Interface", default_answer="Boundary / interface between liquids"),
            HideablePart(key="lower_layer", label="Lower Liquid Layer", default_answer="Lower layer (denser liquid, e.g. water)"),
            HideablePart(key="stopcock", label="Stopcock Tap", default_answer="Stopcock tap"),
        ],
        accessibility_desc="Pear-shaped separating funnel supported by ring clamp showing two distinct immiscible liquid layers above a stopcock tap and receiving beaker.",
    )
)

register_diagram(
    DiagramMetadata(
        id="bio.heart_structure",
        title="Mammalian Heart (4 Chambers)",
        subject="Biology",
        category="Circulatory System",
        topics=["Transport System", "Heart Anatomy", "Circulation"],
        class_levels=["JSS 2", "SSS 1", "SSS 2"],
        renderer="heart_structure",
        fields=[
            DiagramField(name="organ_title", label="Title", default="Mammalian Heart"),
        ],
        hideable_parts=[
            HideablePart(key="right_atrium", label="Right Atrium", default_answer="Right atrium (receives deoxygenated blood)"),
            HideablePart(key="left_atrium", label="Left Atrium", default_answer="Left atrium (receives oxygenated blood from lungs)"),
            HideablePart(key="right_ventricle", label="Right Ventricle", default_answer="Right ventricle (pumps blood to lungs)"),
            HideablePart(key="left_ventricle", label="Left Ventricle", default_answer="Left ventricle (pumps blood to aorta and body)"),
            HideablePart(key="septum", label="Central Septum", default_answer="Muscular septum preventing mixing of blood"),
        ],
        accessibility_desc="Section through mammalian heart showing right and left atria, right and left ventricles, and dividing muscular septum.",
    )
)

register_diagram(
    DiagramMetadata(
        id="bio.food_web",
        title="Ecosystem Food Chain & Trophic Levels",
        subject="Biology",
        category="Ecology & Ecosystems",
        topics=["Energy Flow", "Trophic Levels", "Food Chains & Webs"],
        class_levels=["JSS 1", "JSS 2", "SSS 1"],
        renderer="food_web",
        fields=[
            DiagramField(name="ecosystem_name", label="Ecosystem Name", default="Terrestrial Food Web"),
        ],
        hideable_parts=[
            HideablePart(key="producer", label="Primary Producer", default_answer="Primary producer (green plants / autotrophs)"),
            HideablePart(key="primary_consumer", label="Primary Consumer (Herbivore)", default_answer="Primary consumer / herbivore"),
            HideablePart(key="secondary_consumer", label="Secondary Consumer (Carnivore)", default_answer="Secondary consumer / carnivore"),
            HideablePart(key="apex_predator", label="Apex Predator (Tertiary Consumer)", default_answer="Apex predator / tertiary consumer"),
        ],
        accessibility_desc="Vertical four-tier trophic energy pyramid with arrows showing directional energy transfer from green plant producers up to apex carnivores.",
    )
)

register_diagram(
    DiagramMetadata(
        id="agric.wheelbarrow",
        title="Farm Wheelbarrow (Second-Class Lever)",
        subject="Agricultural Science",
        category="Farm Tools & Machinery",
        topics=["Farm Tools", "Simple Farm Machines", "Levers in Agriculture"],
        class_levels=["JSS 1", "JSS 2", "SSS 1"],
        renderer="wheelbarrow",
        fields=[
            DiagramField(name="tool_name", label="Tool Name", default="Farm Wheelbarrow"),
        ],
        hideable_parts=[
            HideablePart(key="wheel", label="Wheel & Axle (Fulcrum)", default_answer="Front wheel (fulcrum / pivot)"),
            HideablePart(key="tray", label="Hopper / Tray (Load)", default_answer="Metal tray / bucket (load)"),
            HideablePart(key="handles", label="Handles (Effort)", default_answer="Handles (effort applied by farmer)"),
            HideablePart(key="legs", label="Supporting Legs", default_answer="Ground resting legs / stands"),
        ],
        accessibility_desc="Side schematic view of a farm wheelbarrow highlighting wheel at front, load tray in center, and handles at rear.",
    )
)

register_diagram(
    DiagramMetadata(
        id="agric.egg_structure",
        title="Internal Structure of an Egg",
        subject="Agricultural Science",
        category="Animal Production & Poultry",
        topics=["Poultry Production", "Egg Anatomy", "Reproduction"],
        class_levels=["JSS 3", "SSS 1", "SSS 2"],
        renderer="egg_structure",
        fields=[
            DiagramField(name="egg_type", label="Specimen Label", default="Avian Egg Structure"),
        ],
        hideable_parts=[
            HideablePart(key="shell", label="Calcareous Shell", default_answer="Porous shell for protection and gas exchange"),
            HideablePart(key="air_cell", label="Air Space / Cell", default_answer="Air cell at blunt end"),
            HideablePart(key="albumen", label="Albumen (Egg White)", default_answer="Albumen / egg white (protein & water)"),
            HideablePart(key="yolk", label="Yolk & Germinal Disc", default_answer="Yolk (nutrient supply)"),
            HideablePart(key="chalaza", label="Chalaza Cords", default_answer="Chalaza (twisted protein cords centering the yolk)"),
        ],
        accessibility_desc="Longitudinal cross section of a fresh poultry egg displaying shell, air space, albumen layers, central yolk, and twisted chalaza cords.",
    )
)


def get_all_diagrams() -> List[DiagramMetadata]:
    """Return all registered diagram definitions."""
    return list(_CATALOG.values())


def validate_diagram_catalog() -> list[str]:
    """Return deterministic editorial issues in the seeded diagram inventory."""
    issues: list[str] = []
    seen: set[str] = set()
    for item in _CATALOG.values():
        if item.id in seen:
            issues.append(f"duplicate diagram id: {item.id}")
        seen.add(item.id)
        if not item.title.strip() or not item.renderer.strip():
            issues.append(f"missing title or renderer: {item.id}")
        if not item.subject.strip() or not item.topics:
            issues.append(f"missing subject or topics: {item.id}")
        if not item.accessibility_desc.strip():
            issues.append(f"missing accessibility description: {item.id}")
    return issues


def get_diagram_by_id(diagram_id: str) -> Optional[DiagramMetadata]:
    """Find a registered diagram by its unique ID."""
    return _CATALOG.get(diagram_id)


def get_diagrams_by_subject(subject: str) -> List[DiagramMetadata]:
    """Filter diagrams by subject name."""
    sub = subject.lower().strip()
    return [d for d in _CATALOG.values() if d.subject.lower() == sub]


def search_diagrams(query: str, subject: Optional[str] = None) -> List[DiagramMetadata]:
    """Search diagrams by keyword and optional subject filter."""
    q = query.lower().strip()
    results = list(_CATALOG.values())
    if subject and subject.strip():
        sub = subject.lower().strip()
        results = [d for d in results if d.subject.lower() == sub]
    if not q:
        return results
    return [
        d for d in results
        if q in d.title.lower()
        or q in d.category.lower()
        or any(q in t.lower() for t in d.topics)
    ]
