"""FastHTML frontend application instance (FRONTEND_SPEC sec 2.1).

One FastHTML app mounted inside the FastAPI application at "/". Bootstrap is
added exactly once, at import time. Session support is enabled via
``secret_key`` (Starlette SessionMiddleware) — the signed cookie carries auth
tokens from M2 onwards.
"""

from pathlib import Path

from fasthtml.common import FastHTML, Link, Meta, Script, Style
from faststrap import add_bootstrap, mount_assets

from app.config.settings import get_settings
from app.frontend.routes import auth as auth_routes
from app.frontend.routes import bank as bank_routes
from app.frontend.routes import curriculum as curriculum_routes
from app.frontend.routes import dashboard as dashboard_routes
from app.frontend.routes import exams as exams_routes
from app.frontend.routes import ops as ops_routes
from app.frontend.routes import proposals as proposals_routes
from app.frontend.routes import public as public_routes
from app.frontend.routes import settings as settings_routes
from app.frontend.routes import staff as staff_routes
from app.frontend.middleware import register_middlewares

settings = get_settings()

# Core runtime scripts (htmx, fasthtml.js, surreal.js, css-scope-inline) are
# vendored under /assets/js instead of fasthtml's default CDN <script> tags.
# The security middleware sets `script-src 'self'`, which would silently block
# every CDN script — and with it ALL hx-get/hx-post/hx-delete behaviour
# (tabs, preflight, approve, delete-question...).  Serving them from our own
# /assets mount keeps the strict CSP intact and makes the app fully
# offline-resilient — the same policy already used for Bootstrap and KaTeX.
_CORE_JS = "/assets/js"

frontend_app = FastHTML(
    # default_hdrs=False replaces fasthtml's CDN header set with our own
    # self-hosted equivalents below (charset/viewport/htmx/fasthtml-js/
    # surreal/css-scope-inline — same elements, same order as fasthtml's
    # def_hdrs so behaviour is unchanged).
    default_hdrs=False,
    hdrs=[
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1, viewport-fit=cover"),
        Script(src=f"{_CORE_JS}/htmx.min.js"),
        Script(src=f"{_CORE_JS}/fasthtml.js"),
        Script(src=f"{_CORE_JS}/surreal.js"),
        Script(src=f"{_CORE_JS}/css-scope-inline.js"),
    ],
    secret_key=settings.jwt_secret_key,
    sess_https_only=settings.app_env != "development",
    sess_path="/",
    exception_handlers={404: public_routes.not_found_handler, 500: public_routes.server_error_handler},
)

# Faststrap: exactly once, at startup (FRONTEND_SPEC sec 2.1).  font_family is
# intentionally omitted: faststrap would inject a Google-Fonts <link>, which
# the strict CSP blocks.  We self-host Nunito Sans instead (see below).
add_bootstrap(
    frontend_app,
    mode="light",
    include_modern_toast=True,
)

# Self-hosted Nunito Sans webfont (offline-resilient; CSP: style-src 'self')
# plus the same body-font wiring faststrap applies when font_family is set.
frontend_app.hdrs.append(Link(rel="stylesheet", href="/assets/vendor/fonts/nunito-sans.css"))
frontend_app.hdrs.append(
    Style(
        ":root { --bs-body-font-family: 'Nunito Sans', sans-serif; } "
        "body { font-family: var(--bs-body-font-family); }"
    )
)

# Brand CSS mounted after Faststrap so local tokens override cleanly (sec 3).
# Preload avoids flash of unstyled content.
frontend_app.hdrs.append(Link(rel="preload", href="/assets/css/custom.css", as_="style"))
frontend_app.hdrs.append(Link(rel="stylesheet", href="/assets/css/custom.css"))

# KaTeX for LaTeX scientific math, physics & chemistry formulas (offline-resilient)
frontend_app.hdrs.append(Link(rel="stylesheet", href="/assets/vendor/katex/katex.min.css"))
frontend_app.hdrs.append(Script(src="/assets/vendor/katex/katex.min.js", defer=True))
frontend_app.hdrs.append(Script(src="/assets/vendor/katex/mhchem.min.js", defer=True))
frontend_app.hdrs.append(Script(src="/assets/vendor/katex/auto-render.min.js", defer=True))
frontend_app.hdrs.append(Script("""
document.addEventListener('DOMContentLoaded', function() {
    function renderMath() {
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\\\(', right: '\\\\)', display: false},
                    {left: '\\\\[', right: '\\\\]', display: true}
                ],
                throwOnError: false
            });
        }
    }
    renderMath();
    // Re-render after any HTMX content swap — including out-of-band swaps
    // (OOB) used by the question edit/delete flows, which dispatch
    // `htmx:oobAfterSwap` rather than `htmx:afterSwap`.
    function onHtmxSwap() {
        renderMath();
    }
    document.body.addEventListener('htmx:afterSwap', onHtmxSwap);
    document.body.addEventListener('htmx:oobAfterSwap', onHtmxSwap);
    document.body.addEventListener('htmx:afterSettle', onHtmxSwap);

    // Remove orphaned Bootstrap modal backdrops.  When a modal lives inside
    // a container that HTMX replaces via OOB swap (e.g. #tab-content on the
    // exam detail page), Bootstrap's .modal-backdrop (appended to <body>,
    // outside the swapped container) is orphaned along with the
    // `modal-open` class on <body> that locks page scroll.  The server fires
    // the `cleanup-modals` event via HX-Trigger after the OOB swap completes,
    // guaranteeing cleanup runs even when the modal element itself was
    // destroyed by the swap.
    document.body.addEventListener('cleanup-modals', function () {
        document.querySelectorAll('.modal-backdrop').forEach(function (b) { b.remove(); });
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    });
});
"""))

# App-owned static assets (css/img) served from /assets (never /static).
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
mount_assets(frontend_app, str(_ASSETS_DIR))

# Security + CSRF middlewares (F46, F49, F50)
register_middlewares(frontend_app)

# Routes
public_routes.register_routes(frontend_app)
auth_routes.register_session_routes(frontend_app)
auth_routes.register_routes(frontend_app)
auth_routes.register_more_routes(frontend_app)
auth_routes.register_settlement_routes(frontend_app)
dashboard_routes.register_routes(frontend_app)
exams_routes.register_routes(frontend_app)
curriculum_routes.curriculum_routes(frontend_app)
bank_routes.register_routes(frontend_app)
proposals_routes.register_routes(frontend_app)
staff_routes.register_routes(frontend_app)
settings_routes.register_routes(frontend_app)
ops_routes.register_routes(frontend_app)
