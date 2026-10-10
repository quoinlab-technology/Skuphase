"""Regression tests for browser-session expiry handling."""

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request

from app.frontend import api


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.is_success = 200 <= status_code < 300

    def json(self):
        return self._payload


class _Client:
    async def request(self, *args, **kwargs):
        return _Response(401, {"detail": "Token expired"})

    async def post(self, *args, **kwargs):
        return _Response(401, {"detail": "Refresh token expired"})


def _request(session):
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/app/exams",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
        "query_string": b"",
        "session": session,
    })


@pytest.mark.asyncio
async def test_expired_jwt_clears_session_and_redirects(monkeypatch):
    session = {
        "access_token": "header.payload.signature",
        "refresh_token": "expired-refresh-token",
        "user": {"role": "teacher"},
    }
    monkeypatch.setattr(api, "_get_client", lambda: _Client())

    with pytest.raises(HTTPException) as caught:
        await api.call_api(_request(session), "GET", "/exams/")

    assert caught.value.status_code == 303
    assert caught.value.headers["Location"] == "/login?expired=1"
    assert not session


@pytest.mark.asyncio
async def test_opaque_tokens_are_not_treated_as_expired(monkeypatch):
    session = {
        "access_token": "opaque-access-token",
        "refresh_token": "opaque-refresh-token",
        "user": {"role": "teacher"},
    }
    monkeypatch.setattr(api, "_get_client", lambda: _Client())

    response = await api.call_api(_request(session), "GET", "/exams/")

    assert response.status_code == 401
    assert session["access_token"] == "opaque-access-token"
