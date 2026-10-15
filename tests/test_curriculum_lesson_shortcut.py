from fasthtml.common import to_xml
from starlette.testclient import TestClient

from app.main import app
from app.frontend.routes.curriculum import _authoring_panel, _build_timeline


class StubResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300

    def json(self):
        return self._payload


class ApiStub:
    async def __call__(self, req, method, path, json=None, params=None):
        if path == "/auth/login":
            return StubResponse({
                "access_token": "qa-access-token",
                "refresh_token": "qa-refresh-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "user_id": "qa-user",
                    "full_name": "QA Teacher",
                    "email": "qa@example.test",
                    "role": "teacher",
                    "account_type": "school_staff",
                    "is_active": True,
                    "is_verified": True,
                },
            })
        if path == "/curriculum/classes":
            return StubResponse({"classes": ["Primary 5"]})
        if path == "/curriculum/subjects":
            return StubResponse({"subjects": [{"subject_name": "Mathematics"}]})
        if path == "/curriculum/school/weeks":
            return StubResponse({"weeks": [{"id": "scheme-123", "week_number": 3, "topic": "Fractions"}]})
        if path == "/curriculum/boards":
            return StubResponse({"boards": ["NERDC"]})
        return StubResponse({})


def _login(client, monkeypatch):
    monkeypatch.setattr("app.frontend.routes.auth.call_api", ApiStub())
    response = client.post(
        "/login",
        data={"email": "qa@example.test", "password": "not-a-real-password"},
    )
    assert response.status_code == 303


def test_curriculum_week_offers_lesson_shortcut_with_scope_and_week():
    markup = to_xml(_build_timeline(
        [{"id": "scheme-123", "week_number": 3, "topic": "Fractions", "has_override": True, "seeded_topic": "Fractions"}],
        "Primary 5",
        "Mathematics",
        "Second Term",
    ))

    assert "Prepare lesson" in markup
    assert "/app/teaching?class_level=Primary+5&amp;subject=Mathematics&amp;term=Second+Term&amp;scheme_id=scheme-123#" in markup
    assert "School edit" in markup
    assert "official NERDC text is unchanged" in markup


def test_teacher_curriculum_editor_only_exposes_school_local_fields():
    markup = to_xml(_authoring_panel({
        "id": "scheme-123",
        "week_number": 3,
        "term": "Second Term",
        "topic": "Fractions",
        "seeded_topic": "Fractions",
        "subtopics": ["Equivalent fractions"],
        "seeded_subtopics": ["Equivalent fractions"],
        "can_edit_canonical": False,
        "can_edit_local": True,
    }))

    assert 'name="topic"' not in markup
    assert "Topic (read-only)" in markup
    assert 'name="teacher_notes"' in markup
    assert "official NERDC reference remains unchanged" in markup


def test_teaching_shortcut_preselects_requested_scheme_week(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    wanted_id = "00000000-0000-0000-0000-000000000032"
    weeks = [
        {"id": "00000000-0000-0000-0000-000000000031", "curriculum_id": "curr-1", "week_number": 1, "topic": "Number work", "subtopics": []},
        {"id": wanted_id, "curriculum_id": "curr-1", "week_number": 2, "topic": "Fractions", "subtopics": []},
    ]

    async def scoped_api(req, method, path, json=None, params=None):
        if path == "/curriculum/classes":
            return StubResponse({"classes": ["Primary 5"]})
        if path == "/curriculum/subjects":
            return StubResponse({"subjects": [{"subject_name": "Mathematics"}]})
        if path == "/curriculum/school/weeks":
            return StubResponse({"weeks": weeks})
        if path == "/lesson-plans/coverage/summary":
            return StubResponse({"total": 0, "planned": 0, "in_progress": 0, "completed": 0, "verified": 0})
        if path == "/lesson-plans/coverage":
            return StubResponse([])
        if path == "/lesson-plans":
            return StubResponse([])
        return StubResponse({})

    monkeypatch.setattr("app.frontend.routes.teaching.call_api", scoped_api)
    response = client.get(
        f"/app/teaching?class_level=Primary%205&subject=Mathematics&term=Second+Term&scheme_id={wanted_id}"
    )

    assert response.status_code == 200
    assert "Lesson planning opened for Week 2: Fractions." in response.text
    assert f'<option value="{wanted_id}" selected>' in response.text
    assert "name=\"curriculum_id\" value=\"curr-1\"" in response.text
    assert 'id="create-lesson-plan"' in response.text


def test_teaching_shortcut_rejects_week_outside_current_scope(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    stub = ApiStub()
    async def unavailable_week_api(req, method, path, json=None, params=None):
        if path == "/lesson-plans/coverage/summary":
            return StubResponse({"total": 0, "planned": 0, "in_progress": 0, "completed": 0, "verified": 0})
        if path in {"/lesson-plans/coverage", "/lesson-plans"}:
            return StubResponse([])
        return await stub(req, method, path, json=json, params=params)

    monkeypatch.setattr("app.frontend.routes.teaching.call_api", unavailable_week_api)
    response = client.get(
        "/app/teaching?class_level=Primary%204&subject=Mathematics&term=First+Term&scheme_id=not-in-scope"
    )

    assert response.status_code == 200
    assert "That curriculum week is not available for the selected class" in response.text
    assert "Lesson planning opened for Week" not in response.text
