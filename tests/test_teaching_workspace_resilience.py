import asyncio

import pytest
from pydantic import ValidationError
from pypdf import PdfReader
from starlette.testclient import TestClient

from app.main import app
from app.schemas.lesson_plan import WeeklyExerciseQuestion
from app.services.worksheet_export_service import export_worksheet_pdf


class StubResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300

    def json(self):
        return self._payload


class LoginStub:
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
        return StubResponse({}, 404)


class TeachingApiStub:
    def __init__(self, *, fail_summary=False):
        self.fail_summary = fail_summary
        self.active = 0
        self.max_active = 0
        self.calls = []

    async def __call__(self, req, method, path, json=None, params=None):
        self.calls.append((method, path))
        if path in {
            "/lesson-plans",
            "/lesson-plans/coverage/summary",
            "/lesson-plans/exercises",
            "/lesson-plans/coverage",
        }:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            try:
                delay = 0.08 if self.fail_summary and path == "/lesson-plans/coverage/summary" else 0.01
                await asyncio.sleep(delay)
            finally:
                self.active -= 1
        payloads = {
            "/curriculum/classes": {"classes": ["Primary 4"]},
            "/curriculum/subjects": {"subjects": [{"subject_name": "Mathematics"}]},
            "/curriculum/school/weeks": {"weeks": []},
            "/curriculum/weeks": {"weeks": []},
            "/lesson-plans": [{
                "id": "qa-plan",
                "title": "QA teaching plan",
                "week_number": 1,
                "term": "First Term",
                "status": "draft",
                "learning_objectives": [],
            }],
            "/lesson-plans/coverage/summary": {
                "total": 10,
                "completed": 2,
                "verified": 1,
            },
            "/lesson-plans/exercises": [],
            "/lesson-plans/coverage": [],
        }
        return StubResponse(payloads.get(path, {}))


def _login(client, monkeypatch):
    monkeypatch.setattr("app.frontend.routes.auth.call_api", LoginStub())
    response = client.post(
        "/login",
        data={"email": "qa@example.test", "password": "not-a-real-password"},
    )
    assert response.status_code == 303


def test_teaching_workspace_parallelizes_independent_fetches(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    api_stub = TeachingApiStub()
    monkeypatch.setattr("app.frontend.routes.teaching.call_api", api_stub)

    response = client.get("/app/teaching?class_level=Primary%204&subject=Mathematics")

    assert response.status_code == 200
    assert "QA teaching plan" in response.text
    assert api_stub.max_active == 3
    assert ("GET", "/lesson-plans/coverage") in api_stub.calls


def test_teaching_workspace_renders_partial_data_on_source_timeout(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    api_stub = TeachingApiStub(fail_summary=True)
    monkeypatch.setattr("app.frontend.routes.teaching.call_api", api_stub)
    monkeypatch.setattr("app.frontend.routes.teaching.TEACHING_API_TIMEOUT_SECONDS", 0.04)

    response = client.get("/app/teaching?class_level=Primary%204&subject=Mathematics")

    assert response.status_code == 200
    assert "QA teaching plan" in response.text
    assert "Some teaching information could not be loaded" in response.text


def test_teaching_workspace_explains_subject_reset_and_school_wide_coverage(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    api_stub = TeachingApiStub()

    async def scoped_api(req, method, path, json=None, params=None):
        if path == "/curriculum/subjects":
            return StubResponse({"subjects": [{"subject_name": "Basic Science"}]})
        return await api_stub(req, method, path, json=json, params=params)

    monkeypatch.setattr("app.frontend.routes.teaching.call_api", scoped_api)
    response = client.get("/app/teaching?class_level=Primary%204&subject=Physics")

    assert response.status_code == 200
    assert "Physics is not available for Primary 4" in response.text
    assert "school-wide syllabus record" in response.text
    assert "School records marked completed" in response.text


def test_worksheet_form_exposes_question_type_marks_and_answer_key(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    monkeypatch.setattr("app.frontend.routes.teaching.call_api", TeachingApiStub())

    response = client.get("/app/teaching/worksheets?class_level=Primary%204&subject=Mathematics")

    assert response.status_code == 200
    assert "Weekly worksheets" in response.text
    assert "<title>" not in response.text.split("<body", 1)[1]
    assert 'name="question_type_1"' in response.text
    assert 'name="question_marks_1"' in response.text
    assert 'name="answer_key_1"' in response.text
    assert "answer keys are not printed for learners" in response.text
    assert "add-worksheet-question" in response.text
    assert 'name="question_type_2"' not in response.text
    assert "remove-worksheet-question" in response.text
    assert 'id="worksheet-question-list"' in response.text
    assert "Create worksheet" in response.text
    assert "btn-primary btn-outline-success" not in response.text
    assert "btn-primary btn-outline-secondary" not in response.text


def test_teaching_workspace_links_to_focused_worksheet_page_and_uses_full_width_plan_cards(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    monkeypatch.setattr("app.frontend.routes.teaching.call_api", TeachingApiStub())

    response = client.get("/app/teaching?class_level=Primary%204&subject=Mathematics")

    assert response.status_code == 200
    assert "Build a weekly worksheet" not in response.text
    assert "/app/teaching/worksheets?class_level=Primary+4&amp;subject=Mathematics&amp;term=First+Term" in response.text
    assert "Your teaching plans" in response.text
    assert 'name="question_type_1"' not in response.text
    assert "Coverage progress" in response.text


def test_worksheet_creation_persists_type_marks_options_and_answer_key(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    _login(client, monkeypatch)
    captured = {}

    async def create_api(req, method, path, json=None, params=None):
        if path == "/lesson-plans/exercises":
            captured.update(json)
            return StubResponse({"id": "qa-exercise"}, 201)
        return StubResponse({}, 404)

    monkeypatch.setattr("app.frontend.routes.teaching.call_api", create_api)
    response = client.post("/app/teaching/exercises/create", data={
        "lesson_plan_id": "00000000-0000-0000-0000-000000000001",
        "title": "QA worksheet",
        "question_text_1": "Which is a source of light?",
        "question_type_1": "mcq",
        "question_marks_1": "3",
        "answer_options_1": "Sun\nMoon",
        "answer_key_1": "Sun",
    })

    assert response.status_code == 303
    assert captured["questions"] == [{
        "question_number": 1,
        "type": "mcq",
        "question_text": "Which is a source of light?",
        "marks": 3,
        "answer_lines": 0,
        "answer_options": ["Sun", "Moon"],
        "answer_key": "Sun",
    }]


def test_multiple_choice_question_requires_two_options():
    with pytest.raises(ValidationError):
        WeeklyExerciseQuestion(type="mcq", question_text="Choose", answer_options=["Only one"])


def test_worksheet_pdf_prints_mcq_options_but_not_answer_key(tmp_path):
    filename = export_worksheet_pdf(
        export_dir=tmp_path,
        title="QA worksheet",
        subject="Science",
        grade_level="Primary 4",
        term="First Term",
        instructions=None,
        questions=[{
            "type": "mcq",
            "question_text": "Which is a source of light?",
            "marks": 2,
            "answer_lines": 0,
            "answer_options": ["Sun", "Moon"],
            "answer_key": "Private key: Sun",
        }],
    )

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(tmp_path / "worksheets" / filename).pages)
    assert "Sun" in pdf_text and "Moon" in pdf_text
    assert "Which is a source of light?" in pdf_text
    assert "Private key" not in pdf_text


def test_worksheet_pdf_renders_tex_as_vector_formula_not_literal_delimiters(tmp_path, monkeypatch):
    import app.services.worksheet_export_service as worksheet_export

    rendered = []
    original = worksheet_export.formula_to_svg

    def capture_formula(formula, **kwargs):
        rendered.append(formula)
        return original(formula, **kwargs)

    monkeypatch.setattr(worksheet_export, "formula_to_svg", capture_formula)
    filename = export_worksheet_pdf(
        export_dir=tmp_path,
        title="Quadratic equations practice",
        subject="Mathematics",
        grade_level="Primary 6",
        term="First Term",
        instructions=None,
        questions=[{"question_text": r"Solve $$x^2 + 5x + 6 = 0$$, then use \(y = 2\).", "marks": 2}],
    )

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(tmp_path / "worksheets" / filename).pages)
    assert rendered == ["x^2 + 5x + 6 = 0", "y = 2"]
    assert "$$" not in pdf_text
    assert r"\(" not in pdf_text
