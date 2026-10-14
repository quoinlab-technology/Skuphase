"""Guard against oversized signed browser-session cookies."""

from starlette.requests import Request

from app.frontend.deps import clear_auth, store_auth
from app.frontend.routes.exams import _remember_generation_context, _wizard_state


def test_login_replaces_stale_transient_session_state():
    session = {
        "wizard": {"custom_instructions": "old" * 2000},
        "generation_contexts": {"old": {"sections": ["old"] * 30}},
        "_flash": {"message": "stale"},
    }

    store_auth(session, {
        "access_token": "access",
        "refresh_token": "refresh",
        "user": {"email": "teacher@example.test"},
    })

    assert set(session) == {"access_token", "refresh_token", "user", "csrf"}
    assert session["user"]["email"] == "teacher@example.test"


def test_expiry_clears_all_cookie_backed_state():
    session = {
        "access_token": "expired",
        "refresh_token": "expired-refresh",
        "wizard": {"curriculum_weeks": ["large old catalogue"]},
        "generation_contexts": {"old": {"sections": ["large old sections"]}},
    }

    clear_auth(session)

    assert session == {}


def test_legacy_curriculum_cache_is_removed_from_wizard_session():
    session = {
        "wizard": {
            "subject": "Mathematics",
            "curriculum_weeks": [{"topic": "large cached catalogue"}],
            "curriculum_scope": "primary 4|mathematics|first term",
        }
    }
    request = Request({"type": "http", "method": "GET", "path": "/app/exams/new", "headers": [], "session": session})

    wizard = _wizard_state(request)

    assert wizard == {"subject": "Mathematics"}
    assert session["wizard"] == {"subject": "Mathematics"}


def test_generation_context_session_is_compact_and_bounded():
    session = {
        "generation_contexts": {
            str(index): {
                "total_questions": 25,
                "num_sections": 2,
                "selected_weeks": [str(week) for week in range(1, 14)],
                "sections": [{"name": "Section", "num_questions": 12}] * 5,
                "subject": "Physics",
                "grade_level": "SSS 3",
                "term": "First Term",
            }
            for index in range(5)
        }
    }

    _remember_generation_context(session, "newest", {
        "total_questions": 25,
        "num_sections": 2,
        "num_weeks": 13,
        "subject": "Physics",
        "grade_level": "SSS 3",
        "term": "First Term",
        "selected_weeks": [str(week) for week in range(1, 14)],
        "sections": [{"name": "Section", "num_questions": 12}] * 5,
    })

    contexts = session["generation_contexts"]
    assert len(contexts) == 3
    assert "newest" in contexts
    assert all("sections" not in item and "selected_weeks" not in item for item in contexts.values())
    assert contexts["newest"]["num_weeks"] == 13
