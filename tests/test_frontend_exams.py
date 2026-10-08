"""M3 frontend exams tests (FRONTEND_SPEC sec 6.4-6.6).

The frontend calls the API in-process via ``app.frontend.routes.exams.call_api``;
tests stub that function so no database is required. Login is performed for real
(via the auth router with a stubbed ``call_api``) to obtain a session cookie.
"""

import json

import pytest
from starlette.testclient import TestClient

from app.main import app


class FakeResp:
    def __init__(self, status: int, payload: dict | None = None, content: bytes = b""):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.content = content

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


def _tokens():
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-123",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "user_id": "u1", "full_name": "Amina", "email": "amina@example.com",
            "role": "school_admin", "account_type": "school_staff",
            "is_active": True, "is_verified": True,
        },
    }


def _tokens_teacher():
    t = _tokens()
    t["user"] = {**t["user"], "user_id": "t1", "role": "teacher"}
    return t


def _gen_ok(**extra):
    payload = {"exam_id": "e1", "warnings": []}
    payload.update(extra)
    return FakeResp(200, payload)



EXAM = {
    "id": "e1", "title": "Primary 5 Mathematics First Term",
    "subject": "Mathematics", "grade_level": "Primary 5",
    "term": "First Term", "workflow_state": "teacher_review",
    "status": "completed", "total_questions": 5, "total_marks": 10,
    "questions": [
        {"question_number": i, "question_text": f"Q{i}?",
         "question_type": "multiple_choice", "marks": 2, "options": ["a", "b"],
         "correct_answer": "A"}
        for i in range(1, 6)
    ],
}

EXAM_LIST = {"exams": [EXAM], "total": 1}


@pytest.fixture
def client():
    return TestClient(app)


def _stub(responses):
    calls = {"n": 0}

    async def fake(req, method, path, json=None, params=None):
        calls["n"] += 1
        resp = responses if isinstance(responses, FakeResp) else (
            responses[min(calls["n"] - 1, len(responses) - 1)])
        return resp() if callable(resp) else resp

    return fake


@pytest.fixture
def logged_in(client, monkeypatch):
    """Log in for real (stubbed auth API) then patch exams.call_api."""
    monkeypatch.setattr(
        "app.frontend.routes.auth.call_api", _stub(FakeResp(200, _tokens()))
    )
    client.post("/login", data={"email": "a@b.com", "password": "password123"})
    calls = {"n": 0, "last": None}

    def _make(responses):
        calls["n"] = 0

        async def fake(req, method, path, json=None, params=None):
            calls["n"] += 1
            calls["last"] = (method, path, json)
            resp = responses if isinstance(responses, FakeResp) else (
                responses[min(calls["n"] - 1, len(responses) - 1)])
            return resp() if callable(resp) else resp

        monkeypatch.setattr("app.frontend.routes.exams.call_api", fake)
        return calls

    return _make


# ------------------------------------------------------------ guards


def test_exams_list_redirects_anon(client):
    r = client.get("/app/exams", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location", "")


def test_exam_detail_redirects_anon(client):
    r = client.get("/app/exams/e1", follow_redirects=False)
    assert r.status_code == 303


# ------------------------------------------------------------ list page


def test_exams_list_renders(client, logged_in):
    logged_in(FakeResp(200, EXAM_LIST))
    r = client.get("/app/exams")
    assert r.status_code == 200
    assert "Mathematics" in r.text
    assert "/app/exams/e1" in r.text


def test_exams_list_empty_state(client, logged_in):
    logged_in(FakeResp(200, {"exams": [], "total": 0}))
    r = client.get("/app/exams")
    assert r.status_code == 200
    assert "exam" in r.text.lower()


def test_exams_list_api_error(client, logged_in):
    logged_in(FakeResp(500, {"detail": "boom"}))
    r = client.get("/app/exams")
    assert r.status_code == 200  # error rendered in-page, never a 500


# ------------------------------------------------------------ wizard + manual


def test_wizard_page_renders(client, logged_in):
    # Regression: "/app/exams/new" must NOT be shadowed by the param route
    # "/app/exams/{exam_id}" (which would 303-redirect to /app/exams).
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    r = client.get("/app/exams/new", follow_redirects=False)
    assert r.status_code == 200
    assert "app-stepper" in r.text          # the modern step nav renders
    assert "Create exam with AI" in r.text


def test_wizard_all_steps_render(client, logged_in):
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    for step in ("1", "2", "3", "4"):
        r = client.get(f"/app/exams/new?step={step}", follow_redirects=False)
        assert r.status_code == 200
        assert "app-stepper" in r.text

    # Step 1: Exam Scope verification
    r1 = client.get("/app/exams/new?step=1")
    assert "Exam Scope" in r1.text
    assert "Total Marks" in r1.text
    assert "Difficulty Preset" in r1.text
    assert "Balanced" in r1.text
    assert "Exam Prep" in r1.text
    assert "CA Test" in r1.text
    # Ensure NO field variable names bleed through into visible HTML
    assert ">csrf_token" not in r1.text
    assert ">exam_title" not in r1.text
    assert ">total_marks" not in r1.text
    assert ">difficulty_preset" not in r1.text
    assert ">bloom_levels" not in r1.text
    assert ">term" not in r1.text
    assert ">weeks" not in r1.text


    # Step 2: Curriculum coverage verification
    r2 = client.get("/app/exams/new?step=2")
    assert "Curriculum Coverage" in r2.text
    assert "NERDC Curriculum Scope" in r2.text
    assert "Focus Topics" in r2.text
    assert 'value="Whole Numbers, Place Value, Fractions, Basic Operations"' not in r2.text

    # Step 3: Exam Structure verification
    r3 = client.get("/app/exams/new?step=3")
    assert "Exam Structure" in r3.text
    assert "SECTION 1" in r3.text
    assert "Section A: Objectives" in r3.text
    assert "Add Section" in r3.text
    assert "Additional instructions for AI (optional)" in r3.text
    assert 'name="custom_instructions"' in r3.text
    assert 'name="total_marks" type="hidden"' in r3.text

    # Step 4: Confirm & Review verification
    r4 = client.get("/app/exams/new?step=4")
    assert "Review" in r4.text
    assert "Generate Exam" in r4.text
    assert "AI Instructions" in r4.text


def test_modern_wizard_preserves_scope_title_and_target_marks(client, logged_in):
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    r = client.post("/app/exams/new?step=2", data={
        "exam_title": "Primary 6 Mathematics Examination",
        "grade_level": "Primary 6",
        "subject": "Mathematics",
        "term": "First Term",
        "total_marks": "60",
        "difficulty_preset": "balanced",
        "bloom_levels": ["Remember"],
    })
    assert r.status_code == 200
    r = client.post("/app/exams/new?step=3", data={
        "selected_weeks": ["1"],
        "focus_topics": "",
        "total_marks": "60",
    })
    assert r.status_code == 200
    r = client.post("/app/exams/new?step=4", data={
        "total_marks": "60",
        "section_1_title": "Section A",
        "section_1_qtype": "multiple_choice",
        "section_1_num": "20",
        "section_1_marks_per_q": "2",
        "section_1_marks": "40",
        "section_2_title": "Section B",
        "section_2_qtype": "short_answer",
        "section_2_num": "5",
        "section_2_marks_per_q": "4",
        "section_2_marks": "20",
        "custom_instructions": "",
    })
    assert r.status_code == 200
    assert "Primary 6 Mathematics Examination" in r.text
    assert "Mathematics · Primary 6" in r.text
    assert "60 marks" in r.text


def test_wizard_step1_navigation(client, logged_in):
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    r = client.post("/ui/exams/wizard/step1", data={
        "grade_level": "Primary 4",
        "subject": "Mathematics",
        "term": "First Term",
        "exam_title": "Primary 4 Mathematics — First Term Examination",
        "total_marks": "100",
        "difficulty_preset": "balanced",
        "bloom_levels": ["Remember", "Understand", "Apply", "Analyse"],
    })
    assert r.status_code == 200
    assert "Curriculum Coverage" in r.text
    assert "NERDC Curriculum Scope" in r.text





def test_manual_entry_page_renders(client, logged_in):
    logged_in(FakeResp(404, {"detail": "no curriculum yet"}))
    r = client.get("/app/exams/new/manual")
    assert r.status_code == 200
    assert "Manual Exam" in r.text
    assert "manual-question-editor" in r.text
    assert "manual-copilot-panel" in r.text
    assert "Apply suggestion" in r.text
    assert "nothing is applied automatically" in r.text
    assert "JSS 1" in r.text
    assert "SSS 3" in r.text
    assert "Physics" in r.text
    assert "manualNoticeModal" in r.text
    assert "Study Mode (Show Full Labels)" in r.text


def test_exams_list_has_direct_ai_and_manual_actions(client, logged_in):
    logged_in(FakeResp(200, EXAM_LIST))
    r = client.get("/app/exams")
    assert r.status_code == 200
    assert "Generate with AI" in r.text
    assert "Manual Exam" in r.text
    assert 'href="/app/exams/new/manual"' in r.text
    assert 'data-bs-target="#createExamModal"' not in r.text


def test_manual_composer_submits_structured_questions(client, logged_in):
    calls = logged_in(FakeResp(200, {"exam_id": "manual-1"}))
    questions = [{
        "question_number": 1,
        "type": "multiple_choice",
        "question_text": "What is 2 + 2?",
        "marks": 2,
        "options": ["3", "4", "5", "6"],
        "sub_parts": [
            {"part": "a", "question": "Show your working.", "marks": 1, "marking_scheme": ["Correct method"]},
        ],
    }]
    r = client.post("/ui/exams/manual-submit", data={
        "subject": "Mathematics",
        "grade_level": "Primary 4",
        "duration_minutes": "60",
        "language": "English",
        "questions_json": json.dumps(questions),
    })
    assert r.status_code == 200
    assert "Open exam" in r.text
    assert calls["last"][0:2] == ("POST", "/exams/manual-submit")
    assert calls["last"][2]["questions"] == questions


# ------------------------------------------------------------ detail + actions


def test_exam_detail_renders_questions(client, logged_in):
    logged_in(FakeResp(200, EXAM))
    r = client.get("/app/exams/e1")
    assert r.status_code == 200
    assert "Q1?" in r.text
    assert "Q5?" in r.text


def test_exam_detail_404_handled(client, logged_in):
    logged_in(FakeResp(404, {"detail": "not found"}))
    r = client.get("/app/exams/nope")
    assert r.status_code == 200  # error state page, no crash


def test_poll_partial(client, logged_in):
    logged_in(FakeResp(200, EXAM))
    r = client.get("/ui/exams/e1/poll")
    assert r.status_code == 200


def test_refine_action(client, logged_in):
    logged_in(FakeResp(200, {**EXAM, "workflow_state": "refinement_requested"}))
    r = client.post("/ui/exams/e1/refine",
                    data={"instructions": "make it harder"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)


def test_submit_final_action(client, logged_in):
    logged_in(FakeResp(200, {**EXAM, "workflow_state": "final_submitted_by_teacher"}))
    r = client.post("/ui/exams/e1/submit-final", follow_redirects=False)
    assert r.status_code in (200, 303)


def test_approve_action_preflight_block(client, logged_in):
    logged_in(FakeResp(409, {"detail": "Preflight failed",
                             "failed_checks": ["Total marks mismatch (5 != 10)"]}))
    r = client.post("/ui/exams/e1/approve")
    assert r.status_code == 200  # block surfaced in-page, not a 500


def test_export_action(client, logged_in):
    logged_in(FakeResp(200, {"export_id": "x1", "file_name": "abc.pdf"}))
    r = client.post("/ui/exams/e1/export", follow_redirects=False)
    assert r.status_code in (200, 303)


def test_delete_action(client, logged_in):
    logged_in(FakeResp(204, {}))
    r = client.delete("/ui/exams/e1", follow_redirects=False)
    assert r.status_code in (200, 303)

def test_exam_detail_renders_phase6_elements(client, logged_in):
    logged_in(FakeResp(200, EXAM))
    r = client.get("/app/exams/e1")
    assert r.status_code == 200
    assert "app-section-strip-card" in r.text
    assert "Run Preflight" in r.text
    assert "Approve" in r.text
    assert "Questions" in r.text
    assert "Preflight" in r.text
    assert "Quality Report" in r.text
    assert "Audit Comments" in r.text


def test_exam_detail_approved_header_actions(client, logged_in):
    approved_exam = {**EXAM, "workflow_state": "approved", "status": "approved"}
    logged_in(FakeResp(200, approved_exam))
    r = client.get("/app/exams/e1")
    assert r.status_code == 200
    assert "Export PDF" in r.text


def test_edit_question_recalculates_marks(client, logged_in):
    logged_in(FakeResp(200, {"id": "q1", "marks": 5, "total_marks": 15}))
    r = client.post(
        "/ui/exams/e1/questions/q1/edit",
        data={"question_text": "Updated question?", "marks": "5", "options": "A\nB", "correct_answer": "A"},
    )
    assert r.status_code == 200
    assert "recalculated" in r.text.lower()


def test_resolve_audit_comment(client, logged_in):
    logged_in([
        FakeResp(200, {"message": "Audit comment resolved"}),
        FakeResp(200, [{"id": "c1", "status": "resolved", "comment_text": "Need harder question"}]),
    ])
    r = client.post("/ui/exams/e1/comments/c1/resolve")
    assert r.status_code == 200
    assert "resolved" in r.text.lower()


def test_delete_question_action(client, logged_in):
    logged_in([
        FakeResp(200, {'message': 'Question 1 deleted successfully'}),
        FakeResp(200, EXAM),
    ])
    r = client.delete('/ui/exams/e1/questions/q1')
    assert r.status_code == 200
    assert 'deleted' in r.text.lower()


def test_question_modal_populates_textarea(client, logged_in):
    exam_with_q = {
        **EXAM,
        'questions': [
            {
                'id': 'q1',
                'question_number': 1,
                'question_text': 'What is the capital of Lagos State?',
                'question_type': 'multiple_choice',
                'options': ['Ikeja', 'Badagry', 'Epe', 'Ikorodu'],
                'correct_answer': 'A',
                'marks': 2,
                'explanation': 'Ikeja is the capital.',
            }
        ]
    }
    logged_in(FakeResp(200, exam_with_q))
    r = client.get('/app/exams/e1')
    assert r.status_code == 200
    # Ensure textarea contains the text as child, not just an empty tag
    assert '>What is the capital of Lagos State?</textarea>' in r.text
    assert '>Ikeja\nBadagry\nEpe\nIkorodu</textarea>' in r.text
    assert '>Ikeja is the capital.</textarea>' in r.text


def test_section_headers_rendered(client, logged_in):
    logged_in(FakeResp(200, EXAM))
    r = client.get('/app/exams/e1')
    assert r.status_code == 200
    # Section header should be present
    assert 'app-exam-section-header' in r.text
    assert 'Section A (Objectives)' in r.text
    # Top toolbar with show answers should be present
    assert 'Show answers &amp; explanations' in r.text or 'Show answers & explanations' in r.text


def test_section_header_has_add_from_bank_button(client, logged_in):
    logged_in(FakeResp(200, EXAM))
    r = client.get('/app/exams/e1')
    assert r.status_code == 200
    assert 'Add from Bank' in r.text
    assert 'importBankModal-e1-1' in r.text


def test_section_bank_picker_loads_items(client, logged_in, monkeypatch):
    logged_in(FakeResp(200, EXAM))

    async def fake_bank_call(req, method, path, **kwargs):
        if '/exams/e1' in path and method == 'GET':
            return FakeResp(200, EXAM)
        if '/exams/question-bank/items' in path and method == 'GET':
            return FakeResp(200, [
                {
                    'id': 'b-item-1',
                    'question_text': 'Sample Bank Question for Math',
                    'difficulty': 'easy',
                    'marks': 2,
                    'question_type': 'multiple_choice',
                    'topic': 'Algebra',
                }
            ])
        return FakeResp(404, {})

    monkeypatch.setattr('app.frontend.routes.exams.call_api', fake_bank_call)
    r = client.get('/ui/exams/e1/sections/1/bank-picker')
    assert r.status_code == 200
    assert 'Sample Bank Question for Math' in r.text
    assert 'chk-bank-1-b-item-1' in r.text


def test_import_bank_questions_into_section(client, logged_in, monkeypatch):
    logged_in(FakeResp(200, EXAM))

    async def fake_api_call(req, method, path, **kwargs):
        if '/exams/e1/questions/import-from-bank' in path and method == 'POST':
            return FakeResp(200, {'message': 'imported', 'imported_count': 1})
        if '/exams/e1' in path and method == 'GET':
            return FakeResp(200, EXAM)
        return FakeResp(404, {})

    monkeypatch.setattr('app.frontend.routes.exams.call_api', fake_api_call)
    r = client.post(
        '/ui/exams/e1/questions/import-bank',
        data={
            'bank_item_ids': ['b-item-1'],
            'section_number': '1',
            'section_name': 'Section A (Objectives)',
        }
    )
    assert r.status_code == 200
    assert 'Successfully imported 1 question(s)' in r.text
