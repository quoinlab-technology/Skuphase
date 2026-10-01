"""Tests for the Visual & Formula Library API and services."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import library_router
from app.services.formula_catalog import get_all_formulas, get_formulas_by_subject, search_formulas
from app.services.diagram_catalog import get_all_diagrams, get_diagrams_by_subject, search_diagrams
from app.services.library_service import LibraryService
from app.schemas.library import DiagramRenderSpec


def _get_test_client() -> TestClient:
    test_app = FastAPI()
    test_app.include_router(library_router.router, prefix="/api/v1/library")
    return TestClient(test_app)


def test_formula_catalog_integrity():
    formulas = get_all_formulas()
    assert len(formulas) >= 25
    subjects = {f.subject for f in formulas}
    assert "Mathematics" in subjects
    assert "Physics" in subjects
    assert "Chemistry" in subjects
    assert "Further Mathematics" in subjects

    # Test subject filtering
    physics = get_formulas_by_subject("Physics")
    assert len(physics) >= 8
    assert all(f.subject == "Physics" for f in physics)

    # Test search
    suvat = search_formulas("suvat")
    assert len(suvat) >= 1


def test_diagram_catalog_integrity():
    diagrams = get_all_diagrams()
    assert len(diagrams) >= 25
    subjects = {d.subject for d in diagrams}
    assert "Physics" in subjects
    assert "Chemistry" in subjects
    assert "Biology" in subjects
    assert "Agricultural Science" in subjects
    assert "Mathematics" in subjects

    # Test subject filtering
    bio = get_diagrams_by_subject("Biology")
    assert len(bio) >= 3


def test_diagram_render_study_mode():
    res = LibraryService.render_diagram("math.right_triangle", DiagramRenderSpec(mode="study"))
    assert res.svg.startswith("<svg")
    assert len(res.marking_points) == 0


def test_diagram_render_exam_mode_with_callouts():
    spec = DiagramRenderSpec(
        mode="exam",
        hidden_parts=["hypotenuse", "height"],
        callout_style="roman",
        show_values=True,
    )
    res = LibraryService.render_diagram("math.right_triangle", spec)
    assert res.svg.startswith("<svg")
    assert len(res.marking_points) == 2
    assert "Part I" in res.marking_points[0]
    assert "Part II" in res.marking_points[1]


def test_library_api_endpoints():
    client = _get_test_client()
    # 1. Formulas
    r_f = client.get("/api/v1/library/formulas")
    assert r_f.status_code == 200
    assert len(r_f.json()) >= 25

    # 2. Diagrams
    r_d = client.get("/api/v1/library/diagrams")
    assert r_d.status_code == 200
    assert len(r_d.json()) >= 25

    # 3. Render
    payload = {
        "mode": "exam",
        "hidden_parts": ["load"],
        "callout_style": "alpha",
        "show_values": True,
        "params": {"load_label": "250 N"},
    }
    r_r = client.post("/api/v1/library/diagrams/physics.simple_pulley/render", json=payload)
    assert r_r.status_code == 200
    data = r_r.json()
    assert data["svg"].startswith("<svg")
    assert len(data["marking_points"]) == 1
    assert "Part A" in data["marking_points"][0]
