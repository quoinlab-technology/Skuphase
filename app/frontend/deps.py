"""Session-derived guards and user context (FRONTEND_SPEC.md §2.3)."""

from __future__ import annotations

from typing import Optional

from fasthtml.common import RedirectResponse
from starlette.requests import Request


def current_user(request: Request) -> Optional[dict]:
    """The cached UserResponse dict stored at login, or None."""
    return request.session.get("user")


def ensure_login(request: Request) -> Optional[RedirectResponse]:
    """Return a redirect when unauthenticated; None when allowed.

    Usage inside a handler::

        guard = ensure_login(request)
        if guard:
            return guard
    """
    if request.session.get("access_token"):
        return None
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
