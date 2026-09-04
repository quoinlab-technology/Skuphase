"""M1 frontend tests: public pages, branded errors, API precedence.

Covers the FRONTEND_SPEC.md §9.1 M1 exit criteria:
app boots, shells render, landing page works, tests green.
"""

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_landing_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Curriculum-aligned exams" in r.text
    assert "SkuPhase" in r.text
    # Auth CTAs are present (§6.10)
    assert "/register" in r.text
    assert "/login" in r.text


def test_landing_links_brand_css(client):
    r = client.get("/")
    assert "/assets/css/custom.css" in r.text


def test_brand_css_asset_served(client):
    r = client.get("/assets/css/custom.css")
    assert r.status_code == 200
    assert "--brand-primary" in r.text
    assert "#00412E" in r.text


def test_about_page_renders(client):
    r = client.get("/about")
    assert r.status_code == 200
    assert "About SkuPhase" in r.text
    # Honest coverage copy (§6.10)
    assert "Pre-Nursery to Primary 6" in r.text


def test_privacy_page_renders(client):
    r = client.get("/privacy")
    assert r.status_code == 200
    assert "Privacy" in r.text
    assert "Terms" in r.text


def test_unknown_page_gets_branded_404(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404
    assert "Page not found" in r.text
    # Recovery path present (§5.4)
    assert 'href="/"' in r.text


def test_health_endpoint_unaffected(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_api_takes_precedence_over_ui_mount(client):
    """API routes must win over the catch-all frontend mount (§2.1)."""
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401  # API responds — not swallowed by the UI


def test_docs_still_available(client):
    r = client.get("/docs")
    assert r.status_code == 200
