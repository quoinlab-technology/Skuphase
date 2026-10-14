"""Regression coverage for the remaining Pass-1/Pass-2 reliability findings."""

from pathlib import Path

import httpx
import pytest

from app.services import branding


def test_school_logo_timeout_uses_bundled_brand_mark(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, _url):
            raise TimeoutError("upstream URL must not be logged")

    monkeypatch.setattr(branding.httpx, "Client", BrokenClient)
    image = branding.logo_flowable(
        "https://storage.example.invalid/school-logo.png",
        width=60,
        height=60,
    )

    assert image is not None
    expected = Path(branding.__file__).resolve().parents[1] / "assets" / "img" / "skuphase_logo.png"
    assert Path(image.filename) == expected


@pytest.mark.parametrize("status_code", [404, 504])
def test_school_logo_http_failure_uses_bundled_brand_mark(monkeypatch, status_code):
    class FailedResponse:
        headers = {"content-type": "text/plain"}
        content = b"upstream response must not be logged or rendered"

        def raise_for_status(self):
            request = httpx.Request("GET", "https://storage.example.invalid/logo.png")
            response = httpx.Response(status_code, request=request)
            raise httpx.HTTPStatusError("upstream failure", request=request, response=response)

    class FailedClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, _url):
            return FailedResponse()

    monkeypatch.setattr(branding.httpx, "Client", FailedClient)
    image = branding.logo_flowable(
        "https://storage.example.invalid/school-logo.png",
        width=60,
        height=60,
    )

    expected = Path(branding.__file__).resolve().parents[1] / "assets" / "img" / "skuphase_logo.png"
    assert image is not None
    assert Path(image.filename) == expected


def test_exam_table_scrolls_inside_panel_at_intermediate_viewports():
    css_path = Path(__file__).resolve().parents[1] / "app" / "assets" / "css" / "custom.css"
    css = css_path.read_text(encoding="utf-8")
    table_rule = css.split(".app-table-container {", 1)[1].split("}", 1)[0]

    assert "overflow-x: auto" in table_rule
    assert "min-width: 0" in table_rule
    assert "max-width: 100%" in table_rule
    assert ".app-content,\n.app-main" in css


def test_print_logo_fallback_is_marked_and_print_waits_for_assets():
    from app.frontend.routes.exams import _print_after_assets_script, _render_clean_print_paper

    markup = str(_render_clean_print_paper(
        {"id": "e1", "subject": "Mathematics", "grade_level": "Primary 5", "questions": []},
        {"school_name": "Test School", "school_logo_url": "https://storage.example.invalid/logo.png"},
    ))
    script = str(_print_after_assets_script())

    assert 'data-school-logo="true"' in markup
    assert 'data-fallback-src="/assets/img/skuphase_logo.png"' in markup
    assert "Promise.race" in script
    assert "window.print()" in script
