"""M2 frontend auth tests (FRONTEND_SPEC §6.1–6.3).

The frontend calls the API in-process via ``app.frontend.routes.auth.call_api``;
tests stub that function so no database is required.
"""

import pytest
from starlette.testclient import TestClient

from app.main import app


class FakeResp:
    """Minimal httpx.Response stand-in used by ``unwrap``."""

    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload if payload is not None else {}

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


def _tokens(user=None):
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": user or {
            "user_id": "u1",
            "full_name": "Amina",
            "email": "amina@example.com",
            "role": "school_admin",
            "account_type": "school_staff",
            "is_active": True,
            "is_verified": True,
        },
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_api(monkeypatch):
    """Patch call_api with a queue of fake responses (last repeats)."""

    def _make(responses):
        calls = {"n": 0, "last": None}

        async def fake_call_api(req, method, path, json=None, params=None):
            calls["n"] += 1
            calls["last"] = (method, path, json)
            if isinstance(responses, list):
                resp = responses[min(calls["n"] - 1, len(responses) - 1)]
            else:
                resp = responses
            return resp if isinstance(resp, FakeResp) else resp()

        monkeypatch.setattr("app.frontend.routes.auth.call_api", fake_call_api)
        return calls

    return _make


# ------------------------------------------------------------ pages render


@pytest.mark.parametrize(
    "path",
    ["/login", "/register", "/register?mode=individual", "/forgot-password", "/reset-password"],
)
def test_auth_pages_render(client, path):
    r = client.get(path)
    assert r.status_code == 200


def test_login_page_has_fields(client):
    r = client.get("/login")
    assert 'type="email"' in r.text
    assert "forgot-password" in r.text


def test_register_school_has_admin_fields(client):
    r = client.get("/register")
    assert "admin_full_name" in r.text
    assert "admin_email" in r.text


def test_register_individual_has_workspace(client):
    r = client.get("/register?mode=individual")
    assert "workspace_name" in r.text


def test_registration_split_screen_brand_panel(client):
    """The brand panel must match media_1788662908327.png with exact trust bullets and faststrap icons."""
    r = client.get("/register")
    assert "Start generating" in r.text
    assert "Free plan — no credit card required" in r.text
    assert "NERDC curriculum aligned" in r.text
    assert "Full admin control over AI generation" in r.text
    assert "Ready to print in PDF or Word" in r.text


def test_registration_persona_selector_has_no_emojis(client):
    """Persona selector must match media_1788663171702.png using real FastStrap icons without emojis."""
    r = client.get("/register")
    # No emojis
    assert "🏫" not in r.text
    assert "👤" not in r.text
    # FastStrap bootstrap icons
    assert "bi-building" in r.text
    assert "bi-person-fill" in r.text
    # Labels matching screenshot
    assert "School / Institution" in r.text
    assert "Multi-teacher school" in r.text
    assert "Individual Teacher" in r.text
    assert "Solo / Private tutor" in r.text


def test_school_registration_two_step_elements(client):
    """School form must contain all Step 1 and Step 2 fields from media_1788662908327.png and media_1788663073935.png."""
    r = client.get("/register?mode=school")
    # Progress bars
    assert 'id="reg-bar-1"' in r.text
    assert 'id="reg-bar-2"' in r.text
    # Step 1 elements
    assert "Register your school" in r.text
    assert "Step 1 of 2 — School details" in r.text
    assert 'name="school_name"' in r.text
    assert 'name="state"' in r.text
    assert 'name="lga"' in r.text
    assert 'name="school_type"' in r.text
    assert 'name="contact_email"' in r.text
    assert 'name="contact_phone"' in r.text
    assert 'name="referral_source"' in r.text
    assert "Continue to admin setup" in r.text
    # Step 2 elements
    assert "Set up your admin account" in r.text
    assert "Step 2 of 2 — Admin user" in r.text
    assert 'name="admin_first_name"' in r.text
    assert 'name="admin_last_name"' in r.text
    assert 'name="admin_email"' in r.text
    assert 'name="admin_job_title"' in r.text
    assert 'name="admin_password"' in r.text
    assert "Create School Account" in r.text



# ------------------------------------------------------------ guards


def test_app_redirects_anon_to_login(client):
    r = client.get("/app", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location", "")


# ------------------------------------------------------------ login flow


SESSION_COOKIE = "session_"


def _session_json(client) -> dict:
    """Decode the signed (not encrypted) session_ cookie payload."""
    import base64
    import json
    import zlib

    raw = client.cookies.get(SESSION_COOKIE)
    if not raw:
        return {}
    payload = raw.split(".")[0]
    payload += "=" * (-len(payload) % 4)
    data = base64.urlsafe_b64decode(payload)
    try:
        return json.loads(data)
    except Exception:
        return json.loads(zlib.decompress(data))


def test_login_success_sets_session_and_redirects(client, mock_api):
    mock_api(FakeResp(200, _tokens()))
    r = client.post("/login", data={"email": "a@b.com", "password": "password123"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location") == "/app"
    assert _session_json(client).get("access_token") == "access-token-123"


def test_login_failure_shows_friendly_error(client, mock_api):
    mock_api(FakeResp(401, {"detail": "Incorrect email or password."}))
    r = client.post("/login", data={"email": "a@b.com", "password": "wrong"}, follow_redirects=False)
    assert r.status_code == 200
    assert "Incorrect email or password." in r.text


def test_login_rate_limited(client, mock_api):
    mock_api(FakeResp(429, {"detail": "Too many failed attempts. Try again later."}))
    r = client.post("/login", data={"email": "a@b.com", "password": "x"}, follow_redirects=False)
    assert r.status_code == 200
    assert "Too many failed attempts" in r.text


# ------------------------------------------------------------ registration


def test_individual_registration_auto_logs_in(client, mock_api):
    mock_api(
        [
            FakeResp(201, {"user_id": "u1", "school_id": "s1", "workspace_name": "w", "user": {}}),
            FakeResp(200, _tokens()),
        ]
    )
    r = client.post(
        "/register/individual",
        data={"full_name": "Amina", "email": "a@b.com", "password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers.get("location") == "/app"
    assert _session_json(client).get("access_token") == "access-token-123"


def test_school_registration_auto_logs_in(client, mock_api):
    mock_api(
        [
            FakeResp(201, {"school_id": "s1", "school_name": "Primary", "admin_user": {}, "message": "ok"}),
            FakeResp(200, _tokens()),
        ]
    )
    r = client.post(
        "/register/school",
        data={
            "school_name": "Green Primary",
            "contact_email": "school@b.com",
            "admin_full_name": "Bola",
            "admin_email": "bola@b.com",
            "admin_password": "password123",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers.get("location") == "/app"


def test_school_registration_with_first_and_last_name_and_state(client, mock_api):
    calls = mock_api(
        [
            FakeResp(201, {"school_id": "s1", "school_name": "Greenfield Academy", "admin_user": {}, "message": "ok"}),
            FakeResp(200, _tokens()),
        ]
    )
    r = client.post(
        "/register/school",
        data={
            "school_name": "Greenfield Academy",
            "state": "Lagos",
            "lga": "Victoria Island",
            "school_type": "Private Primary",
            "contact_email": "admin@greenfield.edu.ng",
            "contact_phone": "+234 801 000 0000",
            "referral_source": "Word of mouth",
            "admin_first_name": "Adaeze",
            "admin_last_name": "Okafor",
            "admin_email": "adaeze@greenfield.edu.ng",
            "admin_job_title": "Vice-Principal",
            "admin_password": "Password123!",
            "agree_terms": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers.get("location") == "/app"
    # Registration succeeded, followed by auto-login with admin credentials
    assert calls["n"] == 2
    assert calls["last"][1] == "/auth/login"
    assert calls["last"][2]["email"] == "adaeze@greenfield.edu.ng"
    assert calls["last"][2]["password"] == "Password123!"



def test_registration_validation_error_shows_message(client, mock_api):
    mock_api(
        FakeResp(
            422,
            {
                "detail": [
                    {
                        "loc": ["body", "full_name"],
                        "msg": "String should have at least 2 characters",
                    }
                ]
            },
        )
    )
    r = client.post(
        "/register/individual",
        data={"full_name": "A", "email": "a@b.com", "password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "Full name" in r.text


# ------------------------------------------------------------ logout


def test_logout_clears_session(client, mock_api):
    mock_api([FakeResp(200, _tokens()), FakeResp(200, {"message": "Logged out"})])
    client.post("/login", data={"email": "a@b.com", "password": "password123"}, follow_redirects=False)
    assert _session_json(client).get("access_token") == "access-token-123"

    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location")
    assert _session_json(client).get("access_token") is None


# ------------------------------------------------------------ forgot/reset


def test_forgot_password_never_enumerates(client, mock_api):
    mock_api(FakeResp(200, {"message": "ok"}))
    r = client.post("/forgot-password", data={"email": "nobody@example.com"}, follow_redirects=False)
    assert r.status_code == 303
    r2 = client.get("/forgot-password")
    assert "If that email is registered" in r2.text


def test_reset_password_mismatch_blocks(client):
    r = client.post(
        "/reset-password",
        data={"token": "t", "new_password": "password123", "confirm_password": "different"},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "do not match" in r.text


def test_reset_password_success_redirects(client, mock_api):
    mock_api(FakeResp(200, {"message": "ok"}))
    r = client.post(
        "/reset-password",
        data={"token": "t", "new_password": "password123", "confirm_password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/login" in r.headers.get("location")
