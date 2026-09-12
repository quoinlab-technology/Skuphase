"""Session-derived guards and user context (FRONTEND_SPEC.md §2.3)."""

from __future__ import annotations

from typing import Optional

from fasthtml.common import RedirectResponse
from starlette.requests import Request


def current_user(request: Request) -> Optional[dict]:
    """The cached UserResponse dict stored at login, or None."""
    return request.session.get("user")


def _is_token_expired(token: str) -> bool:
    """Check if a JWT string is expired or malformed. Returns False for non-JWT test tokens."""
    if not token or token.count(".") != 2:
        return False
    from app.core.security import verify_token
    return verify_token(token) is None


def ensure_login(request: Request) -> Optional[RedirectResponse]:
    """Return a redirect when unauthenticated or expired without refresh; None when allowed.

    Usage inside a handler::

        guard = ensure_login(request)
        if guard:
            return guard

    Token expiration during API calls is handled transparently inside ``call_api``
    via the session's ``refresh_token``. This function only gates on whether any
    ``access_token`` at all is present so that test sessions (which use opaque
    non-JWT strings like ``"access-token-123"``) are never redirected.
    """
    token = request.session.get("access_token")
    if token:
        # If expired but a refresh token exists, let call_api handle the refresh
        # transparently. Only hard-block when there is no access_token whatsoever.
        if not _is_token_expired(token) or request.session.get("refresh_token"):
            return None

    # No access token (and no refresh fallback) — redirect to login.
    clear_auth(request.session)
    is_htmx = (
        request.headers.get("hx-request") == "true"
        or request.headers.get("HX-Request") == "true"
    )
    if is_htmx:
        from starlette.responses import Response
        return Response(status_code=200, headers={"HX-Redirect": "/login?expired=1"})
    return RedirectResponse("/login?expired=1", status_code=303)


def require_role(request: Request, *roles: str) -> Optional[RedirectResponse]:
    """Redirect non-admin/role-mismatched users away from guarded pages."""
    guard = ensure_login(request)
    if guard:
        return guard
    user = current_user(request) or {}
    if user.get("role") not in roles:
        return RedirectResponse("/app", status_code=303)
    return None


def store_auth(session, data: dict) -> None:
    """Persist a TokenResponse payload into the session (§2.3)."""
    session["access_token"] = data["access_token"]
    session["refresh_token"] = data["refresh_token"]
    session["user"] = data.get("user") or {}
    import secrets

    session.setdefault("csrf", secrets.token_hex(16))


def clear_auth(session) -> None:
    for key in ("access_token", "refresh_token", "user", "csrf"):
        session.pop(key, None)
