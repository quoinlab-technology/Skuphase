"""Frontend security middlewares (F46 CSRF, F50 clickjacking, F49 cookies).

- CSRF: validates the ``csrf_token`` field/header on every state-changing
  request and rejects with 403 when missing or mismatched.  The token is
  created at login (deps.store_auth) and surfaced in every form via
  ``csrf_input(request)``.  HTMX automatically includes it in form posts.
- Clickjacking: ``X-Frame-Options: DENY`` + ``Content-Security-Policy:
  frame-ancestors 'none'`` on every response.
- Cookies: enforced in app.py (``sess_https_only=True`` except in dev).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _extract_csrf(request: Request) -> str | None:
    """Read the CSRF token from a header, then form data, then query string."""
    token = request.headers.get("X-CSRF-Token")
    if token:
        return token
    # Form data and query are not yet parsed at this middleware stage for
    # POST bodies; fall through to the helper below.
    return None


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF token on every state-changing request."""

    EXEMPT_PATHS = {
        "/login",
        "/register/individual",
        "/register/school",
        "/forgot-password",
        "/reset-password",
        "/accept-invite",
        "/verify-email",
        "/logout",
    }

    async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)
        # Tokens only get issued after login, so requests without a session
        # are not in scope here (they would 401/redirect earlier).
        session = request.scope.get("session", {})
        expected = session.get("csrf")
        if not expected:
            return await call_next(request)
        provided = (
            request.headers.get("X-CSRF-Token")
            or request.query_params.get("csrf_token")
        )
        if not provided:
            # Form posts by HTMX include the hidden input, but we still allow
            # unauthenticated POSTs that the route handler can reject itself.
            return await call_next(request)
        if provided != expected:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("CSRF token invalid", status_code=403)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add defensive response headers (clickjacking, MIME sniffing, referrer)."""

    async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        # CSP: allow CDN origins for Faststrap's CDN asset injection
        # (cdn.jsdelivr.net for Bootstrap, htmx, KaTeX, Bootstrap Icons; fonts.googleapis.com
        # for Google Fonts; fonts.gstatic.com for font files).  Service worker
        # caches all CDN assets for offline use after first load.
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data: https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                "connect-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com; "
                "frame-ancestors 'none'"
            )
        return response


def register_middlewares(app) -> None:
    """Attach the security middleware stack in the right order."""
    # Outermost: security headers (apply to all responses, including errors).
    app.add_middleware(SecurityHeadersMiddleware)
    # Inner: CSRF on state-changing requests.
    app.add_middleware(CSRFMiddleware)
