"""Regression tests for the question-diagram trust boundary."""

from app.services.svg_safety import sanitize_svg


def test_sanitize_svg_returns_canonical_svg_without_wrapper():
    raw = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="5" cy="5" r="4" /></svg>'
    cleaned = sanitize_svg(raw)

    assert cleaned is not None
    assert cleaned.startswith("<svg")
    assert cleaned.endswith("</svg>")
    assert "faststrap-svg" not in cleaned


def test_sanitize_svg_rejects_active_or_remote_content():
    assert sanitize_svg('<svg onload="alert(1)"><circle /></svg>') is None
    assert sanitize_svg('<svg><script>alert(1)</script><circle /></svg>') is None
    assert sanitize_svg('<svg><style>* { display:none }</style><circle /></svg>') is None
    cleaned = sanitize_svg('<svg><circle style="fill:red" /></svg>')
    assert cleaned is not None and "style=" not in cleaned
    assert sanitize_svg('<svg><image href="https://evil.example/a.png" /></svg>') is None
    assert sanitize_svg('<div><svg><circle /></svg></div>') is None
