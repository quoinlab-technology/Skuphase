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
from starlette.responses import RedirectResponse, Response

from app.config.settings import get_settings
from app.frontend.routes import auth as auth_routes
from app.frontend.routes import bank as bank_routes
from app.frontend.routes import curriculum as curriculum_routes
from app.frontend.routes import dashboard as dashboard_routes
from app.frontend.routes import admin as admin_routes
from app.frontend.routes import exams as exams_routes
from app.frontend.routes import ops as ops_routes
from app.frontend.routes import public as public_routes
from app.frontend.routes import settings as settings_routes
from app.frontend.routes import staff as staff_routes
from app.frontend.routes import teaching as teaching_routes
from app.frontend.routes import guided as guided_routes
from app.frontend.middleware import register_middlewares

settings = get_settings()


def _session_expired_handler(req, exc):
    """Leave an expired in-app session at the sign-in page.

    HTMX requests need an explicit client-side redirect; normal browser
    requests use a standard 303 so no protected action remains on screen.
    """
    if req.headers.get("hx-request", "").lower() == "true":
        return Response(status_code=200, headers={"HX-Redirect": "/login?expired=1"})
    return RedirectResponse("/login?expired=1", status_code=303)

frontend_app = FastHTML(
    secret_key=settings.jwt_secret_key,
    sess_https_only=settings.app_env != "development",
    sess_path="/",
    exception_handlers={
        404: public_routes.not_found_handler,
        500: public_routes.server_error_handler,
        303: _session_expired_handler,
    },
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
        "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js",
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

# Mermaid for model-generated flow/process diagrams (water cycle, food
# chains, industrial processes). Loaded from CDN; service worker caches
# after first load for offline rendering. Faststrap's init script renders
# [data-fs-mermaid] containers whenever window.mermaid is present.
frontend_app.hdrs.append(Script(src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js", defer=True))
# KaTeX for LaTeX scientific math, physics & chemistry formulas.
# Loaded from CDN; service worker caches after first load for offline rendering.
frontend_app.hdrs.append(Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"))
frontend_app.hdrs.append(Script(src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js", defer=True))
frontend_app.hdrs.append(Script(src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/mhchem.min.js", defer=True))
frontend_app.hdrs.append(Script(src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js", defer=True))
frontend_app.hdrs.append(Script("""
document.addEventListener('DOMContentLoaded', function() {
    function renderMath(el) {
        var target = el || document.body;
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(target, {
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
    renderMath(document.body);
    // Faststrap's own init() also renders [data-fs-mermaid] containers
    // whenever window.mermaid exists. This explicit fallback guarantees the
    // diagrams render even when mermaid.min.js (deferred, larger bundle)
    // finishes loading after the Faststrap init pass.
    function renderMermaid(el) {
        var target = el || document.body;
        if (typeof mermaid === 'undefined') {
            return;
        }
        var nodes = target.querySelectorAll
            ? Array.prototype.filter.call(
                target.querySelectorAll('[data-fs-mermaid="true"]'),
                function (node) { return node.dataset.fsMermaidInit !== 'true'; }
              )
            : [];
        if (!nodes.length) {
            return;
        }
        try {
            mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
        } catch (e) { /* already initialised */ }
        try {
            if (typeof mermaid.run === 'function') {
                mermaid.run({ nodes: nodes });
                nodes.forEach(function (node) { node.dataset.fsMermaidInit = 'true'; });
            }
        } catch (e) { /* malformed diagram: leave source text visible */ }
    }
    renderMermaid(document.body);
    // Re-render after HTMX content swap — scoped directly to the swapped subtree
    // to avoid full-page DOM traversals on low-end mobile hardware.
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        renderMath(evt.detail && evt.detail.target ? evt.detail.target : document.body);
        renderMermaid(evt.detail && evt.detail.target ? evt.detail.target : document.body);
    });
    document.body.addEventListener('htmx:oobAfterSwap', function(evt) {
        renderMath(evt.detail && evt.detail.target ? evt.detail.target : document.body);
        renderMermaid(evt.detail && evt.detail.target ? evt.detail.target : document.body);
    });

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

# Consistent feedback for every mutation form.  Most SkuPhase workflows use a
# normal POST form (rather than an HTMX endpoint), so Faststrap's HTMX-only
# LoadingButton cannot cover login, invitations, registration, settings, and
# exam actions by itself.  This keeps the interaction lightweight and works on
# low-bandwidth mobile connections: disable only the submitted control, show a
# small inline spinner, and prevent accidental double submissions.
frontend_app.hdrs.append(Script("""
document.addEventListener('DOMContentLoaded', function () {
    function mutationForm(form) {
        var method = (form.getAttribute('method') || 'get').toLowerCase();
        return method !== 'get' || form.hasAttribute('hx-post') || form.hasAttribute('hx-put') || form.hasAttribute('hx-delete');
    }

    function pendingLabel(button) {
        var explicit = button.getAttribute('data-loading-label');
        if (explicit) return explicit;
        var label = (button.textContent || '').trim().toLowerCase();
        if (label.indexOf('invite') >= 0 || label.indexOf('send') >= 0) return 'Sending…';
        if (label.indexOf('login') >= 0 || label.indexOf('sign in') >= 0) return 'Signing in…';
        if (label.indexOf('create') >= 0 || label.indexOf('register') >= 0) return 'Creating…';
        if (label.indexOf('save') >= 0 || label.indexOf('update') >= 0) return 'Saving…';
        if (label.indexOf('delete') >= 0 || label.indexOf('remove') >= 0) return 'Removing…';
        return 'Working…';
    }

    function start(button, form) {
        if (!button || button.disabled || button.dataset.loadingActive === 'true') return;
        button.dataset.loadingActive = 'true';
        button.dataset.loadingOriginalHtml = button.innerHTML;
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' + pendingLabel(button);
        form.dataset.loadingButton = 'true';
    }

    function restore(form) {
        if (!form) return;
        var button = form.querySelector('[data-loading-active="true"]');
        if (!button) return;
        if (button.dataset.loadingOriginalHtml) button.innerHTML = button.dataset.loadingOriginalHtml;
        button.disabled = false;
        button.removeAttribute('aria-busy');
        delete button.dataset.loadingActive;
        delete button.dataset.loadingOriginalHtml;
        delete form.dataset.loadingButton;
    }

    document.addEventListener('submit', function (event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement) || form.dataset.noLoading === 'true' || !mutationForm(form)) return;
        var button = event.submitter || form.querySelector('button[type="submit"], input[type="submit"]');
        start(button, form);
    }, true);

    document.body.addEventListener('htmx:afterRequest', function (event) {
        var form = event.detail && event.detail.elt instanceof HTMLFormElement ? event.detail.elt : null;
        restore(form);
    });
    document.body.addEventListener('htmx:sendError', function (event) {
        var form = event.detail && event.detail.elt instanceof HTMLFormElement ? event.detail.elt : null;
        restore(form);
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
admin_routes.register_routes(frontend_app)
guided_routes.guided_routes(frontend_app)
exams_routes.register_routes(frontend_app)
curriculum_routes.curriculum_routes(frontend_app)
from app.frontend.routes import proposals
proposals.register_routes(frontend_app)
curriculum_routes.register_curriculum_authoring_routes(frontend_app)
bank_routes.register_routes(frontend_app)
staff_routes.register_routes(frontend_app)
settings_routes.register_routes(frontend_app)
ops_routes.register_routes(frontend_app)
teaching_routes.teaching_routes(frontend_app)
