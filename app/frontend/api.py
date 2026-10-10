"""In-process API client (FRONTEND_SPEC sec 2.2).

Frontend route handlers never touch SQLAlchemy models or services directly —
all data access goes through :func:`call_api`, which invokes the app's own
API handlers in-process (no network hop) with the browser's auth token.

A single ``AsyncClient`` is created at import time and reused for every
request (F12).  Reusing the client preserves the underlying ASGI transport
and avoids re-allocating the request pipeline per call.
"""

from __future__ import annotations

from typing import Any, Optional

from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

FRIENDLY_403 = {
    "You are not allowed to browse question bank": "You do not have permission to browse the question bank.",
    "You are not allowed to view proposals": "Generation proposals have been retired. Open Exams to generate directly.",
    "You are not allowed to create proposals": "Generation proposals have been retired. Open Exams to generate directly.",
}


def auth_headers_from_session(request: Request) -> dict:
    """Bearer headers from the signed session (sec 2.3)."""
    token = request.session.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _build_client() -> AsyncClient:
    """Build the singleton in-process client lazily (avoids import cycles)."""
    from app.main import app as fastapi_app  # local import: avoids cycles

    transport = ASGITransport(app=fastapi_app)
    return AsyncClient(transport=transport, base_url="http://ui.local")


_client: Optional[AsyncClient] = None


def _get_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


async def call_api(
    request: Request,
    method: str,
    path: str,
    json: Optional[dict] = None,
    params: Optional[dict] = None,
    content: Optional[bytes] = None,
    headers: Optional[dict] = None,
) -> Any:
    """Forward an in-process request to ``/api/v1<path>``.

    Returns the raw httpx Response. Automatically revalidates / refreshes expired
    access tokens if a refresh token is present in the session.
    """
    client = _get_client()
    request_headers = auth_headers_from_session(request)
    if headers:
        request_headers.update(headers)
    resp = await client.request(method, f"/api/v1{path}", json=json, content=content, params=params, headers=request_headers)

    # Automatic token revalidation & refresh on 401.
    # If the access token is expired and we have a refresh token, try to get a
    # fresh pair and replay the original request.  On failure we simply return
    # the original 401 — session cleanup / redirect is the responsibility of
    # ensure_login, not this low-level helper (calling clear_auth here wiped
    # the session during dashboard parallel fetches on the login redirect chain).
    if resp.status_code == 401 and request and hasattr(request, "session"):
        refresh_tok = request.session.get("refresh_token")
        if refresh_tok and not path.endswith("/refresh-token"):
            try:
                refresh_resp = await client.post("/api/v1/auth/refresh-token", json={"refresh_token": refresh_tok})
                if refresh_resp.is_success:
                    tokens = refresh_resp.json()
                    new_acc = tokens.get("access_token")
                    if new_acc:
                        request.session["access_token"] = new_acc
                        if "refresh_token" in tokens:
                            request.session["refresh_token"] = tokens["refresh_token"]
                        if "user" in tokens:
                            request.session["user"] = tokens["user"]
                        request.session["_refreshed"] = True
                        new_headers = {"Authorization": f"Bearer {new_acc}"}
                        if headers:
                            new_headers.update(headers)
                        resp = await client.request(method, f"/api/v1{path}", json=json, content=content, params=params, headers=new_headers)
                # If refresh fails, return original 401; ensure_login handles the redirect.
            except Exception:
                pass

    return resp


def unwrap(resp) -> tuple[bool, Any]:
    """Convert an API response into ``(ok, data_or_error)`` (FRONTEND_SPEC sec 5.3).

    Extracts detailed, human-friendly error messages from all API responses,
    formatting Pydantic validation failures, database constraints, and status-specific
    messages clearly so users and developers never receive vague fallbacks.
    """
    if resp.is_success:
        try:
            return True, resp.json()
        except Exception:
            return True, {}

    detail = None
    try:
        data = resp.json()
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("message") or data.get("error")
        elif isinstance(data, str):
            detail = data
    except Exception:
        raw_text = getattr(resp, "text", "") or ""
        if raw_text.strip().startswith("<!doctype") or "<html" in raw_text:
            detail = None
        else:
            detail = raw_text.strip() if raw_text else None

    # 1. Validation errors (422 Unprocessable Entity from FastAPI/Pydantic)
    if resp.status_code == 422:
        fields = {}
        error_msgs = []
        if isinstance(detail, list):
            for entry in detail:
                loc = ".".join(str(p) for p in entry.get("loc", [])[1:])
                msg = entry.get("msg", "Invalid value.")
                if msg.startswith("Value error, "):
                    msg = msg[len("Value error, "):]
                fields[loc] = msg
                field_label = loc.split(".")[-1].replace("_", " ").title()
                error_msgs.append(f"{field_label}: {msg}")
        msg_str = "; ".join(error_msgs) if error_msgs else (str(detail) if detail else "Please check your inputs and try again.")
        return False, {"kind": "validation", "fields": fields, "message": msg_str}

    # 2. Authentication failure (401)
    if resp.status_code == 401:
        msg = str(detail) if (detail and isinstance(detail, str)) else "Incorrect email or password. Please verify your credentials."
        return False, {"kind": "auth", "message": msg}

    # 3. Forbidden (403)
    if resp.status_code == 403:
        friendly = FRIENDLY_403.get(str(detail))
        msg = friendly if friendly else (str(detail) if detail else "You do not have permission to perform this action.")
        return False, {"kind": "forbidden", "message": msg}

    # 4. Not Found (404)
    if resp.status_code == 404:
        msg = str(detail) if (detail and isinstance(detail, str)) else "The requested resource was not found."
        return False, {"kind": "not_found", "message": msg}

    # 5. Rate limited (429)
    if resp.status_code == 429:
        msg = str(detail) if (detail and isinstance(detail, str)) else "Too many requests. Please wait a few moments and try again."
        return False, {"kind": "rate_limited", "message": msg}

    # 6. Detailed dictionary error
    if isinstance(detail, dict):
        msg = detail.get("message") or detail.get("detail") or "We could not complete that request — please try again in a moment."
        return False, {"kind": "detail", "message": msg, "data": detail}

    # 7. Explicit string error (400 Bad Request, 409 Conflict, 500, etc.)
    if detail and isinstance(detail, str) and detail.strip():
        return False, {"kind": "error", "message": detail.strip()}

    # 8. Status code fallback — user-facing copy only (no developer-speak).
    # Backend "message"/"detail" payloads take precedence above; this is the
    # action-oriented net so users never see "Server returned error code 500."
    return False, {"kind": "generic", "message": "We could not complete that request right now — please try again in a moment."}
