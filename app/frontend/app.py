"""FastHTML frontend application instance (FRONTEND_SPEC sec 2.1).

One FastHTML app mounted inside the FastAPI application at "/". Bootstrap is
added exactly once, at import time via Faststrap's CDN-first defaults. Session
support is enabled via ``secret_key`` (Starlette SessionMiddleware) — the
signed cookie carries auth tokens from M2 onwards.

Asset strategy: Faststrap's built-in CDN (cdn.jsdelivr.net) for Bootstrap,
htmx, and Faststrap CSS/JS. PWA service worker caches all CDN assets for
offline use after first load. App-owned assets (brand CSS, logo) served from
/assets via mount_assets.
"""

from pathlib import Path

from fasthtml.common import FastHTML, Link, Script
from faststrap import add_bootstrap, mount_assets
from faststrap.pwa import add_pwa

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

frontend_app = FastHTML(
    secret_key=settings.jwt_secret_key,
    sess_https_only=settings.app_env != "development",
    sess_path="/",
    exception_handlers={404: public_routes.not_found_handler, 500: public_routes.server_error_handler},
)

# Faststrap: exactly once, at startup (FRONTEND_SPEC sec 2.1).  Uses Faststrap's
# default CDN asset injection (Bootstrap CSS/JS, Bootstrap Icons, Faststrap CSS,
# htmx, fasthtml.js, surreal.js, css-scope-inline) from cdn.jsdelivr.net.
# use_cdn=True is the default; explicit here for clarity.
add_bootstrap(
    frontend_app,
    mode="light",
    use_cdn=True,
    include_modern_toast=True,
    font_family="Nunito Sans",
)

# PWA: service worker + manifest for offline capability.
# use_cdn=True is explicit so the SW's auto-precache list includes all CDN URLs.
# route_cache_policies ensures:
#   - /assets/ (local brand CSS, images) → network-first: always fetches fresh,
#     never serves an empty cache entry causing FOUC.
#   - /app, /ui (HTML routes) → network-first: always live server content.
#   - cdn.jsdelivr.net (Bootstrap, htmx, Faststrap) → cache-first: immutable
#     versioned URLs, safe to serve from cache permanently.
# pre_cache_urls: warm up local CSS + KaTeX during SW install so they are ready
#     before any navigation triggers a fetch.
# cache_version v2: clears any stale v1 caches from local-vendor era.
add_pwa(
    frontend_app,
    name="SkuPhase Exam Generator",
    short_name="SkuPhase",
    description="AI-powered exam generator for rural Nigerian schools",
    theme_color="#00412E",
    background_color="#E8EAE5",
    icon_path="/assets/img/logo.svg",
    display="standalone",
    start_url="/",
    service_worker=True,
    offline_page=True,
    cache_name="skuphase",
    cache_version="v3",
    use_cdn=True,
    pre_cache_urls=[
        "/assets/css/custom.css",
        "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css",
        "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js",
        "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js",
        "https://fonts.googleapis.com/css2?family=Nunito%20Sans:wght@400;500;700&display=swap",
    ],
    route_cache_policies={
        # Local app assets — always network-first to prevent FOUC
        "/assets/": "network-first",
        # App HTML routes — always live
        "/app": "network-first",
        "/ui/": "network-first",
        # CDN resources (Bootstrap, htmx, Faststrap, KaTeX) — immutable, cache-first
        "https://cdn.jsdelivr.net": "cache-first",
        "https://fonts.googleapis.com": "cache-first",
        "https://fonts.gstatic.com": "cache-first",
    },
)

# Brand CSS mounted after Faststrap so local tokens override cleanly (sec 3).
# Preload avoids flash of unstyled content.
frontend_app.hdrs.append(Link(rel="preload", href="/assets/css/custom.css", **{"as": "style"}))
frontend_app.hdrs.append(Link(rel="stylesheet", href="/assets/css/custom.css"))

# KaTeX for LaTeX scientific math, physics & chemistry formulas.
# Loaded from CDN; service worker caches after first load for offline rendering.
frontend_app.hdrs.append(Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"))
frontend_app.hdrs.append(Script(src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js", defer=True))
frontend_app.hdrs.append(Script(src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/mhchem.min.js", defer=True))
frontend_app.hdrs.append(Script(src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js", defer=True))
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
