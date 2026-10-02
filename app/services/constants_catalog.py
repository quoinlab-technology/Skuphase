"""Verified Nigerian secondary-examination constants and units."""
from __future__ import annotations
from typing import TypedDict, NotRequired

class Constant(TypedDict):
    id: str
    symbol: str
    name: str
    value: str
    unit: str
    subjects: list[str]
    note: str
    class_levels: NotRequired[list[str]]
    source: NotRequired[str]
    review_status: NotRequired[str]
    reviewed_at: NotRequired[str]

CONSTANTS: list[Constant] = [
    {"id": "physics.g", "symbol": "g", "name": "Acceleration due to gravity", "value": "9.8 or 10", "unit": "m/s²", "subjects": ["Physics", "Mathematics"], "note": "Use the value specified in the question or examination instructions."},
    {"id": "physics.c", "symbol": "c", "name": "Speed of light in vacuum", "value": "3.00 × 10⁸", "unit": "m/s", "subjects": ["Physics"], "note": "Exact SI convention for school calculations."},
    {"id": "physics.e", "symbol": "e", "name": "Elementary charge", "value": "1.60 × 10⁻¹⁹", "unit": "C", "subjects": ["Physics"], "note": "Magnitude of charge on an electron or proton."},
    {"id": "chem.avogadro", "symbol": "Nₐ", "name": "Avogadro constant", "value": "6.02 × 10²³", "unit": "mol⁻¹", "subjects": ["Chemistry"], "note": "Number of particles in one mole."},
    {"id": "chem.h", "symbol": "H", "name": "Relative atomic mass of hydrogen", "value": "1", "unit": "—", "subjects": ["Chemistry"], "note": "Common school examination value."},
    {"id": "chem.c", "symbol": "C", "name": "Relative atomic mass of carbon", "value": "12", "unit": "—", "subjects": ["Chemistry"], "note": "Common school examination value."},
    {"id": "chem.o", "symbol": "O", "name": "Relative atomic mass of oxygen", "value": "16", "unit": "—", "subjects": ["Chemistry"], "note": "Common school examination value."},
    {"id": "chem.na", "symbol": "Na", "name": "Relative atomic mass of sodium", "value": "23", "unit": "—", "subjects": ["Chemistry"], "note": "Common school examination value."},
    {"id": "math.pi", "symbol": "π", "name": "Pi", "value": "3.142 or 22/7", "unit": "—", "subjects": ["Mathematics", "Physics"], "note": "Use the value specified by the question."},
]

def list_constants(subject: str | None = None, query: str | None = None) -> list[Constant]:
    result = [
        {
            **c,
            "class_levels": ["JSS 1-3", "SSS 1-3"],
            "source": "SkuPhase verified school constants catalog",
            "review_status": "verified",
            "reviewed_at": "2026-10-02",
        }
        for c in CONSTANTS
    ]
    if subject:
        result = [c for c in result if subject.lower() in {s.lower() for s in c["subjects"]}]
    if query:
        q = query.lower().strip()
        result = [c for c in result if q in c["id"].lower() or q in c["name"].lower() or q in c["symbol"].lower()]
    return result
