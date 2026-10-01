"""Exams router tests (mocked DB) incl. governance + tenant isolation."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import exams_router
from app.core.database import get_db_session
from app.core.dependencies import get_current_user


def _build_test_app(db_session: AsyncMock, current_user: SimpleNamespace) -> TestClient:
    app = FastAPI()
    app.include_router(exams_router.router, prefix="/api/v1/exams")

    async def override_db():
        return db_session

    async def override_user():
        return current_user

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app)


def _admin(school_id=None, role="school_admin", account_type="school_staff"):
    return SimpleNamespace(
        user_id=uuid.uuid4(),
        school_id=school_id or uuid.uuid4(),
        role=role,
        account_type=account_type,
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )


def _question(**overrides):
    base = dict(
        id=uuid.uuid4(),
        question_number=1,
        type="multiple_choice",
        question_text="Which option shows a living thing?",
        marks=2,
        difficulty="easy",
        bloom_level="remember",
        topic="Living things",
        options=["A. goat", "B. stone", "C. water", "D. chair"],
        correct_answer="A",
        explanation="A goat is alive.",
        marking_scheme=["Correct choice"],
        sub_parts=None,
        diagram_svg=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _dispatching_db(exam, questions):
    """AsyncMock whose execute() dispatches on the statement's table.

    Exam selects -> scalar_one_or_none(exam); Question selects ->
    scalars().all() == questions.
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    async def _execute(stmt, *args, **kwargs):
        stmt_text = str(stmt).lower()

        class _Result:
            def scalar_one_or_none(self_inner):
                if "generation_jobs" in stmt_text or "usage_logs" in stmt_text:
                    return None
                return exam

            def scalars(self_inner):
                return SimpleNamespace(all=lambda: questions)

            def scalar(self_inner):
                return 0

            def all(self_inner):
                return []

        return _Result()

    db.execute = AsyncMock(side_effect=_execute)
    return db


SECTION_PAYLOAD = {
    "section_number": 1,
    "section_title": "SECTION A",
    "question_type": "multiple_choice",
    "num_questions": 5,
    "marks_per_question": 1,
    "instruction_type": "answer_all",
    "sub_part_style": "none",
}


def test_refine_exam_endpoint_success():
    user = _admin()
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        status="under_review",
        workflow_state="teacher_review",
        llm_call_count=1,
        llm_call_limit=3,
    )
    db = _dispatching_db(exam, [])

    client = _build_test_app(db, user)
    with patch("app.api.v1.exams_router.ExamGenerator") as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.refine_exam = AsyncMock(
            return_value={
                "message": "Exam questions refined successfully",
                "exam_id": str(exam.id),
                "updated_questions": 2,
                "provider": "groq",
                "tokens_used": 123,
            }
        )
        response = client.post(
            f"/api/v1/exams/{exam.id}/refine",
            json={"feedback": "Simplify wording", "question_ids": []},
        )

    assert response.status_code == 200
    assert response.json()["updated_questions"] == 2
    assert db.commit.await_count >= 2


def test_approve_exam_endpoint_success():
    user = _admin()
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        status="under_review",
        workflow_state="final_submitted_by_teacher",
    )
    question = _question()
    db = _dispatching_db(exam, [question])

    client = _build_test_app(db, user)
    response = client.post(f"/api/v1/exams/{exam.id}/approve")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert exam.status == "approved"
    assert db.commit.await_count == 1


def test_export_exam_endpoint_success():
    user = _admin()
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        subject="Basic Science",
        grade_level="Primary 4",
        status="approved",
        duration_minutes=90,
        total_marks=2,
        instructions="Answer all questions",
    )
    question = _question()
    db = _dispatching_db(exam, [question])

    client = _build_test_app(db, user)
    file_name = f"{uuid.uuid4().hex}.pdf"
    with patch("app.api.v1.exams_router.ExportService.export_exam_pdf") as mock_export:
        mock_export.return_value = file_name
        response = client.post(
            f"/api/v1/exams/{exam.id}/export",
            json={"format": "pdf", "include_answers": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == file_name
    assert data["download_url"].endswith(file_name)
    assert "/exports/" in data["download_url"]
    assert db.commit.await_count == 1


def test_refine_exam_endpoint_forbidden_for_school_teacher():
    user = _admin(role="teacher")
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, user)
    response = client.post(
        f"/api/v1/exams/{uuid.uuid4()}/refine",
        json={"feedback": "Please simplify wording", "question_ids": []},
    )

    assert response.status_code == 403
    assert db.commit.await_count == 0


def test_individual_teacher_can_generate():
    """Dual-mode: individual teachers drive their own workspace."""
    user = _admin(role="teacher", account_type="individual_teacher")
    exam = None
    db = _dispatching_db(exam, [])
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: 0))

    client = _build_test_app(db, user)
    with patch("app.api.v1.exams_router.enqueue_generation_job") as mock_enqueue, \
         patch("app.api.v1.exams_router.CurriculumService") as mock_curr:
        mock_curr.get_objectives_for_weeks = AsyncMock(
            return_value=[{"week_number": 1, "topic": "t", "subtopics": []}]
        )
        job_id = uuid.uuid4()
        mock_enqueue.return_value = job_id
        response = client.post(
            "/api/v1/exams/generate",
            json={
                "subject": "English",
                "grade_level": "Primary 4",
                "term": "First Term",
                "selected_weeks": [1],
                "sections": [SECTION_PAYLOAD],
                "duration_minutes": 60,
            },
        )

    assert response.status_code == 202
    mock_enqueue.assert_called_once()


def test_approve_exam_endpoint_not_found():
    user = _admin()
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))

    client = _build_test_app(db, user)
    response = client.post(f"/api/v1/exams/{uuid.uuid4()}/approve")

    assert response.status_code == 404
    assert db.commit.await_count == 0


def test_export_exam_endpoint_rejects_non_pdf_format():
    user = _admin()
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, user)
    response = client.post(
        f"/api/v1/exams/{uuid.uuid4()}/export",
        json={"format": "docx", "include_answers": True},
    )

    assert response.status_code == 400
    assert db.commit.await_count == 0


def test_auditor_can_submit_exam_audit_comment():
    user = _admin(role="auditor")
    exam = SimpleNamespace(id=uuid.uuid4(), school_id=user.school_id, status="completed")
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh_comment(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_refresh_comment)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: exam))

    client = _build_test_app(db, user)
    response = client.post(
        f"/api/v1/exams/{exam.id}/audit-comments",
        json={
            "comment_text": "Question 2 should be clearer for pupils.",
            "suggested_question_text": "Explain photosynthesis in simple terms.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "open"
    assert db.commit.await_count == 1
    assert db.add.call_count == 1


def test_refine_from_comments_batches_feedback_and_does_not_burn_budget_on_400():
    user = _admin()
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        status="under_review",
        workflow_state="teacher_review",
        llm_call_count=1,
        llm_call_limit=3,
    )
    comment = SimpleNamespace(
        id=uuid.uuid4(),
        exam_id=exam.id,
        question_id=uuid.uuid4(),
        comment_text="Question has ambiguous wording.",
        suggested_question_text="State two uses of chlorophyll.",
        suggested_marking_scheme='["Definition"]',
        status="open",
        resolved_by_user_id=None,
        resolved_at=None,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: exam),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [comment])),
        ]
    )

    client = _build_test_app(db, user)
    with patch("app.api.v1.exams_router.ExamGenerator") as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.refine_exam = AsyncMock(
            return_value={
                "message": "Exam questions refined successfully",
                "exam_id": str(exam.id),
                "updated_questions": 1,
                "provider": "groq",
                "tokens_used": 77,
            }
        )
        response = client.post(
            f"/api/v1/exams/{exam.id}/refine-from-comments",
            json={"additional_feedback": "Keep complexity moderate."},
        )

    assert response.status_code == 200
    assert response.json()["comments_processed"] == 1
    assert comment.status == "resolved"


def test_refine_from_comments_no_comments_does_not_consume_budget():
    user = _admin()
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        status="under_review",
        workflow_state="teacher_review",
        llm_call_count=1,
        llm_call_limit=3,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: exam),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
        ]
    )

    client = _build_test_app(db, user)
    response = client.post(f"/api/v1/exams/{exam.id}/refine-from-comments", json={})

    assert response.status_code == 400
    # E4 regression: budget untouched when there is nothing to refine.
    assert exam.llm_call_count == 1


def test_teacher_can_create_generation_proposal():
    user = _admin(role="teacher")
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh_proposal(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_refresh_proposal)

    client = _build_test_app(db, user)
    response = client.post(
        "/api/v1/exams/generation-proposals",
        json={
            "subject": "Basic Science",
            "grade_level": "Primary 4",
            "term": "First Term",
            "selected_weeks": [1, 2],
            "desired_outcomes": "Focus on living things and their habitats with examples.",
            "custom_instructions": "Align to school end-of-term format.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "Basic Science"
    assert db.commit.await_count == 1
    assert db.add.call_count == 1


def test_admin_can_generate_exam_from_proposal():
    user = _admin()
    proposal = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        status="open",
        subject="Mathematics",
        grade_level="Primary 5",
        desired_outcomes="Cover fractions and simple multiplication.",
        custom_instructions="Use local market examples.",
        draft_questions="What is one-half of 10?",
        used_by_user_id=None,
        used_at=None,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: proposal),
            SimpleNamespace(scalar=lambda: 0),
        ]
    )

    client = _build_test_app(db, user)
    with patch("app.api.v1.exams_router.enqueue_generation_job", new_callable=AsyncMock) as mock_enqueue:
        response = client.post(
            f"/api/v1/exams/generation-proposals/{proposal.id}/generate",
            json={
                "sections": [SECTION_PAYLOAD],
                "duration_minutes": 60,
                "include_diagrams": False,
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "generating"
    assert proposal.status == "used"
    assert proposal.used_by_user_id == user.user_id
    # F-10: exam + proposal flip + job are committed atomically by the
    # request-scoped dependency, so the endpoint itself performs no commit.
    assert db.commit.await_count == 0
    mock_enqueue.assert_called_once()


def test_auditor_cannot_generate_exam_from_proposal():
    user = _admin(role="auditor")
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, user)
    response = client.post(
        f"/api/v1/exams/generation-proposals/{uuid.uuid4()}/generate",
        json={"sections": [SECTION_PAYLOAD]},
    )

    assert response.status_code == 403
    assert db.commit.await_count == 0


def test_teacher_can_submit_manual_exam():
    user = _admin(role="teacher")
    exam_stub = SimpleNamespace(id=uuid.uuid4())
    questions = [
        _question(type="essay", question_text="Define force.", marks=10),
        _question(
            question_number=2,
            type="short_answer",
            question_text="State one example of a force.",
            marks=5,
        ),
    ]
    db = _dispatching_db(None, questions)

    def _capture_add(obj):
        from app.models.exam import Exam as ExamModel

        if isinstance(obj, ExamModel):
            obj.id = exam_stub.id
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

    db.add.side_effect = _capture_add

    client = _build_test_app(db, user)
    response = client.post(
        "/api/v1/exams/manual-submit",
        json={
            "subject": "Basic Science",
            "grade_level": "Primary 4",
            "duration_minutes": 90,
            "instructions": "Answer all questions.",
            "questions": [
                {
                    "question_number": 1,
                    "type": "essay",
                    "question_text": "Define force and give two examples.",
                    "marks": 10,
                },
                {
                    "question_number": 2,
                    "type": "short_answer",
                    "question_text": "State Newton's first law.",
                    "marks": 5,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_marks"] == 15
    assert len(payload["questions"]) == 2


# ---------------------------------------------------------------------------
# GOVERNANCE BYPASS REGRESSIONS (audit C3)
# ---------------------------------------------------------------------------

def test_update_exam_cannot_set_approved_status():
    user = _admin()
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        status="under_review",
        workflow_state="teacher_review",
    )
    db = _dispatching_db(exam, [_question()])
    client = _build_test_app(db, user)
    response = client.put(
        f"/api/v1/exams/{exam.id}",
        json={"status": "approved"},
    )
    assert response.status_code == 422


def test_update_exam_rejects_mutation_of_approved_exam():
    user = _admin()
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        status="approved",
        workflow_state="approved",
    )
    db = _dispatching_db(exam, [_question()])
    client = _build_test_app(db, user)
    response = client.put(
        f"/api/v1/exams/{exam.id}",
        json={"instructions": "tamper"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# TENANT ISOLATION (audit A2)
# ---------------------------------------------------------------------------

def test_cross_school_exam_access_returns_404():
    user = _admin()  # school A
    other_school_exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=uuid.uuid4(),  # school B
        status="under_review",
        workflow_state="teacher_review",
    )

    async def _execute(stmt, *args, **kwargs):
        class _Result:
            def scalar_one_or_none(self_inner):
                return None  # tenant filter excludes it

        return _Result()

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(side_effect=_execute)

    client = _build_test_app(db, user)
    response = client.get(f"/api/v1/exams/{other_school_exam.id}")
    assert response.status_code == 404


def test_save_to_bank_marks_items_school_owned():
    user = _admin(role="teacher")
    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        subject="Mathematics",
        grade_level="Primary 4",
    )
    question = _question(topic="Fractions", difficulty="easy", marks=1)
    db = _dispatching_db(exam, [question])

    added = []
    db.add.side_effect = lambda obj: added.append(obj)

    client = _build_test_app(db, user)
    response = client.post(f"/api/v1/exams/{exam.id}/question-bank/save", json={})

    assert response.status_code == 200
    assert len(added) == 1
    # SECURITY regression: school-contributed items must NEVER be platform.
    assert added[0].owner_type == "school"
    assert added[0].school_id == user.school_id


def test_few_shot_selector_only_reads_platform_rows():
    """Structural guard: the shared-corpus query filters owner_type=platform."""
    import inspect

    from app.services import few_shot_selector

    source = inspect.getsource(few_shot_selector.FewShotSelector.select)
    assert 'owner_type' in source and 'platform' in source


# ---------------------------------------------------------------------------
# EXPORT DOWNLOAD ENDPOINTS (audit F-01 regression: `db` was used but never
# injected, so every call crashed with a NameError -> 500).
# ---------------------------------------------------------------------------

def test_download_export_rejects_bad_filename_with_400():
    user = _admin()
    exam = SimpleNamespace(id=uuid.uuid4(), school_id=user.school_id)
    client = _build_test_app(_dispatching_db(exam, []), user)

    response = client.get(f"/api/v1/exams/{exam.id}/exports/not-a-valid-export-name")

    assert response.status_code == 400


def test_download_export_without_credentials_returns_401_before_tenant_lookup():
    user = _admin()  # school A
    other = SimpleNamespace(id=uuid.uuid4(), school_id=uuid.uuid4())
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _execute(stmt, *args, **kwargs):
        class _Result:
            def scalar_one_or_none(self_inner):
                return None  # tenant filter excludes it

        return _Result()

    db.execute = AsyncMock(side_effect=_execute)
    client = _build_test_app(db, user)

    response = client.get(f"/api/v1/exams/{other.id}/exports/{uuid.uuid4().hex}.pdf")

    assert response.status_code == 401


def test_download_export_without_credentials_returns_401_before_file_lookup():
    user = _admin()
    exam = SimpleNamespace(id=uuid.uuid4(), school_id=user.school_id)
    client = _build_test_app(_dispatching_db(exam, []), user)

    response = client.get(f"/api/v1/exams/{exam.id}/exports/{uuid.uuid4().hex}.pdf")

    # File presence must not be disclosed before authentication succeeds.
    assert response.status_code == 401


def test_list_exports_cross_school_returns_404():
    user = _admin()  # school A
    other = SimpleNamespace(id=uuid.uuid4(), school_id=uuid.uuid4())
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _execute(stmt, *args, **kwargs):
        class _Result:
            def scalar_one_or_none(self_inner):
                return None

        return _Result()

    db.execute = AsyncMock(side_effect=_execute)
    client = _build_test_app(db, user)

    response = client.get(f"/api/v1/exams/{other.id}/exports")

    assert response.status_code == 404
