"""Formula and Equation Catalog for SkuPhase Assessment Studio.

Provides verified, curriculum-aligned mathematical and scientific equations
structured for one-click insertion into exam questions and marking schemes.
"""

from __future__ import annotations

from typing import List, Optional
from app.schemas.library import FormulaItem, FormulaVariable

_FORMULAS: List[FormulaItem] = [
    # ── MATHEMATICS ──────────────────────────────────────────────────────────
    FormulaItem(
        id="math.quadratic_formula",
        name="Quadratic Formula",
        subject="Mathematics",
        topic="Algebra & Quadratic Equations",
        latex=r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        class_levels=["JSS 3", "SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="x", name="Unknown roots"),
            FormulaVariable(symbol="a", name="Coefficient of x²"),
            FormulaVariable(symbol="b", name="Coefficient of x"),
            FormulaVariable(symbol="c", name="Constant term"),
        ],
        description="Solves ax² + bx + c = 0",
    ),
    FormulaItem(
        id="math.pythagoras",
        name="Pythagorean Theorem",
        subject="Mathematics",
        topic="Geometry & Trigonometry",
        latex=r"a^2 + b^2 = c^2",
        class_levels=["JSS 2", "JSS 3", "SSS 1"],
        variables=[
            FormulaVariable(symbol="a", name="Adjacent side"),
            FormulaVariable(symbol="b", name="Opposite side"),
            FormulaVariable(symbol="c", name="Hypotenuse"),
        ],
        description="Relation between sides in a right-angled triangle",
    ),
    FormulaItem(
        id="math.sine_rule",
        name="Sine Rule",
        subject="Mathematics",
        topic="Trigonometry",
        latex=r"\frac{a}{\sin A} = \frac{b}{\sin B} = \frac{c}{\sin C}",
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="a, b, c", name="Side lengths"),
            FormulaVariable(symbol="A, B, C", name="Opposite angles"),
        ],
        description="Used for non-right-angled triangles given two angles and a side, or two sides and non-included angle",
    ),
    FormulaItem(
        id="math.cosine_rule",
        name="Cosine Rule",
        subject="Mathematics",
        topic="Trigonometry",
        latex=r"c^2 = a^2 + b^2 - 2ab\cos C",
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="c", name="Opposite side to angle C"),
            FormulaVariable(symbol="a, b", name="Adjacent sides"),
            FormulaVariable(symbol="C", name="Included angle"),
        ],
        description="Used when two sides and the included angle are known",
    ),
    FormulaItem(
        id="math.compound_interest",
        name="Compound Interest Formula",
        subject="Mathematics",
        topic="Commercial Arithmetic",
        latex=r"A = P\left(1 + \frac{r}{100}\right)^n",
        class_levels=["JSS 3", "SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="A", name="Total accrued amount", unit="₦"),
            FormulaVariable(symbol="P", name="Principal investment", unit="₦"),
            FormulaVariable(symbol="r", name="Annual interest rate", unit="%"),
            FormulaVariable(symbol="n", name="Number of compounding periods", unit="years"),
        ],
        description="Calculates compound amount over n periods",
    ),
    FormulaItem(
        id="math.circle_area",
        name="Area of a Circle",
        subject="Mathematics",
        topic="Mensuration",
        latex=r"A = \pi r^2",
        class_levels=["Primary 6", "JSS 1", "JSS 2", "JSS 3", "SSS 1"],
        variables=[
            FormulaVariable(symbol="A", name="Area", unit="cm² / m²"),
            FormulaVariable(symbol="r", name="Radius", unit="cm / m"),
        ],
        description="Area enclosed by a circular perimeter",
    ),
    FormulaItem(
        id="math.ap_nth_term",
        name="Arithmetic Progression (n-th Term)",
        subject="Mathematics",
        topic="Sequences and Series",
        latex=r"T_n = a + (n - 1)d",
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="T_n", name="n-th term"),
            FormulaVariable(symbol="a", name="First term"),
            FormulaVariable(symbol="n", name="Term position"),
            FormulaVariable(symbol="d", name="Common difference"),
        ],
        description="Determines the n-th value in an arithmetic sequence",
    ),

    # ── PHYSICS ──────────────────────────────────────────────────────────────
    FormulaItem(
        id="physics.suvat_v",
        name="First Equation of Motion",
        subject="Physics",
        topic="Kinematics & Motion",
        latex=r"v = u + at",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="v", name="Final velocity", unit="m/s"),
            FormulaVariable(symbol="u", name="Initial velocity", unit="m/s"),
            FormulaVariable(symbol="a", name="Acceleration", unit="m/s²"),
            FormulaVariable(symbol="t", name="Time taken", unit="s"),
        ],
        description="Relates velocity to constant acceleration over time",
    ),
    FormulaItem(
        id="physics.suvat_s",
        name="Second Equation of Motion",
        subject="Physics",
        topic="Kinematics & Motion",
        latex=r"s = ut + \frac{1}{2}at^2",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="s", name="Distance / displacement", unit="m"),
            FormulaVariable(symbol="u", name="Initial velocity", unit="m/s"),
            FormulaVariable(symbol="a", name="Acceleration", unit="m/s²"),
            FormulaVariable(symbol="t", name="Time", unit="s"),
        ],
        description="Calculates displacement under uniform acceleration",
    ),
    FormulaItem(
        id="physics.suvat_v2",
        name="Third Equation of Motion",
        subject="Physics",
        topic="Kinematics & Motion",
        latex=r"v^2 = u^2 + 2as",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="v", name="Final velocity", unit="m/s"),
            FormulaVariable(symbol="u", name="Initial velocity", unit="m/s"),
            FormulaVariable(symbol="a", name="Acceleration", unit="m/s²"),
            FormulaVariable(symbol="s", name="Displacement", unit="m"),
        ],
        description="Relates initial and final velocities to distance without time",
    ),
    FormulaItem(
        id="physics.newton_second_law",
        name="Newton's Second Law of Motion",
        subject="Physics",
        topic="Forces & Dynamics",
        latex=r"F = ma",
        class_levels=["JSS 2", "SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="F", name="Net resultant force", unit="N"),
            FormulaVariable(symbol="m", name="Mass of object", unit="kg"),
            FormulaVariable(symbol="a", name="Acceleration", unit="m/s²"),
        ],
        description="Force is proportional to the rate of change of momentum",
    ),
    FormulaItem(
        id="physics.ohms_law",
        name="Ohm's Law",
        subject="Physics",
        topic="Current Electricity",
        latex=r"V = IR",
        class_levels=["JSS 3", "SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="V", name="Potential difference / voltage", unit="V"),
            FormulaVariable(symbol="I", name="Electric current", unit="A"),
            FormulaVariable(symbol="R", name="Electrical resistance", unit="Ω"),
        ],
        description="Current through a conductor is proportional to potential difference",
    ),
    FormulaItem(
        id="physics.electric_power",
        name="Electric Power Equations",
        subject="Physics",
        topic="Current Electricity",
        latex=r"P = IV = I^2R = \frac{V^2}{R}",
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="P", name="Electrical power", unit="W"),
            FormulaVariable(symbol="I", name="Current", unit="A"),
            FormulaVariable(symbol="V", name="Voltage", unit="V"),
            FormulaVariable(symbol="R", name="Resistance", unit="Ω"),
        ],
        description="Rate of electrical energy dissipation in a circuit",
    ),
    FormulaItem(
        id="physics.heat_capacity",
        name="Specific Heat Capacity",
        subject="Physics",
        topic="Thermal Physics",
        latex=r"Q = mc\Delta\theta",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="Q", name="Quantity of heat energy", unit="J"),
            FormulaVariable(symbol="m", name="Mass of substance", unit="kg"),
            FormulaVariable(symbol="c", name="Specific heat capacity", unit="J/(kg·K)"),
            FormulaVariable(symbol=r"\Delta\theta", name="Temperature change", unit="°C or K"),
        ],
        description="Heat required to raise the temperature of a unit mass by 1K",
    ),
    FormulaItem(
        id="physics.wave_equation",
        name="Wave Speed Equation",
        subject="Physics",
        topic="Waves",
        latex=r"v = f\lambda",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="v", name="Wave velocity / speed", unit="m/s"),
            FormulaVariable(symbol="f", name="Frequency", unit="Hz"),
            FormulaVariable(symbol=r"\lambda", name="Wavelength", unit="m"),
        ],
        description="Fundamental relationship between wave velocity, frequency, and wavelength",
    ),
    FormulaItem(
        id="physics.lens_formula",
        name="Thin Lens & Mirror Formula",
        subject="Physics",
        topic="Optics & Light",
        latex=r"\frac{1}{f} = \frac{1}{u} + \frac{1}{v}",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="f", name="Focal length", unit="cm / m"),
            FormulaVariable(symbol="u", name="Object distance", unit="cm / m"),
            FormulaVariable(symbol="v", name="Image distance", unit="cm / m"),
        ],
        description="Relates focal length to object and image distances",
    ),
    FormulaItem(
        id="physics.hydrostatic_pressure",
        name="Fluid Pressure",
        subject="Physics",
        topic="Pressure in Fluids",
        latex=r"P = \rho gh",
        class_levels=["JSS 2", "SSS 1"],
        variables=[
            FormulaVariable(symbol="P", name="Liquid pressure", unit="N/m² or Pa"),
            FormulaVariable(symbol="\rho", name="Fluid density", unit="kg/m³"),
            FormulaVariable(symbol="g", name="Acceleration due to gravity", unit="m/s²"),
            FormulaVariable(symbol="h", name="Depth / column height", unit="m"),
        ],
        description="Hydrostatic pressure at depth h below a liquid surface",
    ),

    # ── CHEMISTRY ────────────────────────────────────────────────────────────
    FormulaItem(
        id="chem.moles_mass",
        name="Mole Calculation (from Mass)",
        subject="Chemistry",
        topic="Stoichiometry & The Mole Concept",
        latex=r"n = \frac{m}{M}",
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="n", name="Number of moles", unit="mol"),
            FormulaVariable(symbol="m", name="Reacting mass", unit="g"),
            FormulaVariable(symbol="M", name="Molar mass", unit="g/mol"),
        ],
        description="Calculates amount of substance from sample mass",
    ),
    FormulaItem(
        id="chem.molarity",
        name="Molar Concentration",
        subject="Chemistry",
        topic="Quantitative Analysis (Titration)",
        latex=r"C = \frac{n}{V} = \frac{m}{M \times V}",
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="C", name="Concentration", unit="mol/dm³"),
            FormulaVariable(symbol="n", name="Amount of solute", unit="mol"),
            FormulaVariable(symbol="V", name="Volume of solution", unit="dm³"),
        ],
        description="Definition of molarity for volumetric analysis",
    ),
    FormulaItem(
        id="chem.titration_ratio",
        name="Volumetric Titration Equation",
        subject="Chemistry",
        topic="Volumetric Analysis",
        latex=r"\frac{C_A V_A}{C_B V_B} = \frac{n_A}{n_B}",
        class_levels=["SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="C_A", name="Molar concentration of acid", unit="mol/dm³"),
            FormulaVariable(symbol="V_A", name="Volume of acid used", unit="cm³"),
            FormulaVariable(symbol="C_B", name="Molar concentration of base", unit="mol/dm³"),
            FormulaVariable(symbol="V_B", name="Volume of base pipetted", unit="cm³"),
            FormulaVariable(symbol="n_A / n_B", name="Mole ratio from balanced equation"),
        ],
        description="Standard WAEC/NECO titration calculation formula",
    ),
    FormulaItem(
        id="chem.ideal_gas_law",
        name="Ideal Gas Law",
        subject="Chemistry",
        topic="Gas Laws",
        latex=r"PV = nRT",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="P", name="Gas pressure", unit="atm / Pa"),
            FormulaVariable(symbol="V", name="Gas volume", unit="dm³ / m³"),
            FormulaVariable(symbol="n", name="Number of moles", unit="mol"),
            FormulaVariable(symbol="R", name="Universal gas constant", unit="8.314 J/(mol·K)"),
            FormulaVariable(symbol="T", name="Absolute temperature", unit="K"),
        ],
        description="Equation of state of a hypothetical ideal gas",
    ),
    FormulaItem(
        id="chem.neutralization_hcl",
        name="Hydrochloric Acid Neutralization",
        subject="Chemistry",
        topic="Acids, Bases & Salts",
        latex=r"\text{HCl} + \text{NaOH} \rightarrow \text{NaCl} + \text{H}_2\text{O}",
        class_levels=["JSS 3", "SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="HCl", name="Hydrochloric acid"),
            FormulaVariable(symbol="NaOH", name="Sodium hydroxide"),
            FormulaVariable(symbol="NaCl", name="Sodium chloride"),
            FormulaVariable(symbol="H_2O", name="Water"),
        ],
        description="Standard strong acid - strong base neutralization reaction",
    ),
    FormulaItem(
        id="chem.calcium_carbonate_decomp",
        name="Thermal Decomposition of Limestone",
        subject="Chemistry",
        topic="Chemical Reactions & Heating",
        latex=r"\text{CaCO}_3\text{(s)} \xrightarrow{\Delta} \text{CaO}\text{(s)} + \text{CO}_2\text{(g)}",
        class_levels=["SSS 1", "SSS 2"],
        variables=[
            FormulaVariable(symbol="CaCO_3", name="Calcium carbonate (limestone)"),
            FormulaVariable(symbol="CaO", name="Calcium oxide (quicklime)"),
            FormulaVariable(symbol="CO_2", name="Carbon dioxide"),
        ],
        description="Decomposition of calcium carbonate to quicklime and carbon dioxide",
    ),

    # ── FURTHER MATHEMATICS ──────────────────────────────────────────────────
    FormulaItem(
        id="further_math.matrix_2x2",
        name="2×2 Matrix Notation",
        subject="Further Mathematics",
        topic="Matrices & Determinants",
        latex=r"A = \begin{pmatrix} a & b \\ c & d \end{pmatrix}",
        class_levels=["SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="a, b, c, d", name="Matrix elements"),
        ],
        description="Standard square matrix representation",
    ),
    FormulaItem(
        id="further_math.matrix_inverse",
        name="Inverse of a 2×2 Matrix",
        subject="Further Mathematics",
        topic="Matrices & Determinants",
        latex=r"A^{-1} = \frac{1}{ad - bc}\begin{pmatrix} d & -b \\ -c & a \end{pmatrix}",
        class_levels=["SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="ad - bc", name="Determinant of A (|A| ≠ 0)"),
        ],
        description="Calculates the multiplicative inverse of a non-singular 2x2 matrix",
    ),
    FormulaItem(
        id="further_math.binomial_theorem",
        name="Binomial Coefficient",
        subject="Further Mathematics",
        topic="Series & Binomial Expansion",
        latex=r"\binom{n}{r} = \frac{n!}{r!(n - r)!}",
        class_levels=["SSS 1", "SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="n", name="Total elements"),
            FormulaVariable(symbol="r", name="Chosen elements"),
        ],
        description="Combinations formula for binomial expansions",
    ),
    FormulaItem(
        id="further_math.derivative_power",
        name="Derivative Power Rule",
        subject="Further Mathematics",
        topic="Differential Calculus",
        latex=r"\frac{d}{dx}\left(x^n\right) = n x^{n - 1}",
        class_levels=["SSS 2", "SSS 3"],
        variables=[
            FormulaVariable(symbol="n", name="Exponent power"),
        ],
        description="Fundamental rule for differentiating algebraic polynomials",
    ),
    FormulaItem(
        id="further_math.definite_integral",
        name="Definite Integral",
        subject="Further Mathematics",
        topic="Integral Calculus",
        latex=r"\int_{a}^{b} f(x)\,dx = F(b) - F(a)",
        class_levels=["SSS 3"],
        variables=[
            FormulaVariable(symbol="a", name="Lower integration limit"),
            FormulaVariable(symbol="b", name="Upper integration limit"),
            FormulaVariable(symbol="F(x)", name="Antiderivative of f(x)"),
        ],
        description="Fundamental theorem of calculus for finding area under curves",
    ),
]


def get_all_formulas() -> List[FormulaItem]:
    """Return all catalogued formulas."""
    return list(_FORMULAS)


def get_formulas_by_subject(subject: str) -> List[FormulaItem]:
    """Return formulas filtered by subject (case-insensitive)."""
    sub = subject.lower().strip()
    return [f for f in _FORMULAS if f.subject.lower() == sub]


def search_formulas(query: str, subject: Optional[str] = None) -> List[FormulaItem]:
    """Search formulas by title, topic, or LaTeX representation."""
    q = query.lower().strip()
    results = _FORMULAS
    if subject and subject.strip():
        sub = subject.lower().strip()
        results = [f for f in results if f.subject.lower() == sub]
    if not q:
        return results
    return [
        f for f in results
        if q in f.id.lower() or q in f.name.lower() or q in f.topic.lower() or q in f.latex.lower()
    ]


def get_formula_by_id(formula_id: str) -> Optional[FormulaItem]:
    """Retrieve a single formula by its unique ID."""
    for f in _FORMULAS:
        if f.id == formula_id:
            return f
    return None
