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


def test_refine_exam_endpoint_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )
    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        status="under_review",
        workflow_state="teacher_review",
        llm_call_count=1,
        llm_call_limit=3,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: exam))

    client = _build_test_app(db, current_user)
    with patch("app.api.v1.exams_router.ExamGenerator") as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.refine_exam = AsyncMock(
            return_value={
                "message": "Exam questions refined successfully",
                "exam_id": str(exam_id),
                "updated_questions": 2,
                "provider": "grok",
                "tokens_used": 123,
            }
        )

        response = client.post(
            f"/api/v1/exams/{exam_id}/refine",
            json={"feedback": "Simplify wording for JSS2", "question_ids": []},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["updated_questions"] == 2
    assert db.commit.await_count >= 2
    assert db.add.call_count >= 1


def test_approve_exam_endpoint_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )

    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        status="under_review",
        workflow_state="final_submitted_by_teacher",
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: exam))

    client = _build_test_app(db, current_user)
    response = client.post(f"/api/v1/exams/{exam_id}/approve")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert exam.status == "approved"
    assert db.commit.await_count == 1
    assert db.add.call_count >= 1


def test_export_exam_endpoint_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )

    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        subject="Biology",
        grade_level="SSS 1",
        status="approved",
        duration_minutes=90,
        total_marks=100,
        instructions="Answer all questions",
    )
    questions = [
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=1,
            question_text="What is photosynthesis?",
            marks=5,
            options=None,
            correct_answer=None,
            marking_scheme=["Definition", "Process"],
        )
    ]

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: exam),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: questions)),
        ]
    )

    client = _build_test_app(db, current_user)

    with patch("app.api.v1.exams_router.ExportService.export_exam_pdf") as mock_export:
        mock_export.return_value = "exports/exam_file.pdf"
        response = client.post(
            f"/api/v1/exams/{exam_id}/export",
            json={"format": "pdf", "include_answers": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "pdf"
    assert data["file_path"] == "exports/exam_file.pdf"
    assert db.commit.await_count == 1
    assert db.add.call_count >= 1


def test_refine_exam_endpoint_forbidden_for_non_admin():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, current_user)
    response = client.post(
        f"/api/v1/exams/{exam_id}/refine",
        json={"feedback": "Please simplify wording", "question_ids": []},
    )

    assert response.status_code == 403
    assert db.commit.await_count == 0
    assert db.add.call_count == 0


def test_approve_exam_endpoint_not_found():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))

    client = _build_test_app(db, current_user)
    response = client.post(f"/api/v1/exams/{exam_id}/approve")

    assert response.status_code == 404
    assert db.commit.await_count == 0
    assert db.add.call_count == 0


def test_export_exam_endpoint_rejects_non_pdf_format():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, current_user)
    response = client.post(
        f"/api/v1/exams/{exam_id}/export",
        json={"format": "docx", "include_answers": True},
    )

    assert response.status_code == 400
    assert db.commit.await_count == 0
    assert db.add.call_count == 0


def test_auditor_can_submit_exam_audit_comment():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="auditor",
        email="auditor@test.edu",
        full_name="Auditor",
        is_active=True,
    )

    exam = SimpleNamespace(id=exam_id, school_id=school_id, status="completed")
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh_comment(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_refresh_comment)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: exam))

    client = _build_test_app(db, current_user)
    response = client.post(
        f"/api/v1/exams/{exam_id}/audit-comments",
        json={
            "comment_text": "Question 2 should be clearer for JSS1 students.",
            "suggested_question_text": "Explain photosynthesis in simple terms.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["exam_id"] == str(exam_id)
    assert payload["comment_text"].startswith("Question 2")
    assert payload["status"] == "open"
    assert db.commit.await_count == 1
    assert db.add.call_count == 1


def test_refine_from_comments_batches_feedback_for_admin():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    question_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )

    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        status="under_review",
        workflow_state="teacher_review",
        llm_call_count=1,
        llm_call_limit=3,
    )
    comment_one = SimpleNamespace(
        id=uuid.uuid4(),
        exam_id=exam_id,
        question_id=question_id,
        comment_text="Question has ambiguous wording.",
        suggested_question_text="State and explain two uses of chlorophyll.",
        suggested_marking_scheme='["Definition", "Two uses"]',
        status="open",
        resolved_by_user_id=None,
        resolved_at=None,
    )
    comment_two = SimpleNamespace(
        id=uuid.uuid4(),
        exam_id=exam_id,
        question_id=None,
        comment_text="Increase practical examples.",
        suggested_question_text=None,
        suggested_marking_scheme=None,
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
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [comment_one, comment_two])),
        ]
    )

    client = _build_test_app(db, current_user)

    with patch("app.api.v1.exams_router.ExamGenerator") as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.refine_exam = AsyncMock(
            return_value={
                "message": "Exam questions refined successfully",
                "exam_id": str(exam_id),
                "updated_questions": 1,
                "provider": "grok",
                "tokens_used": 77,
            }
        )

        response = client.post(
            f"/api/v1/exams/{exam_id}/refine-from-comments",
            json={"additional_feedback": "Keep complexity moderate."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["comments_processed"] == 2
    assert comment_one.status == "resolved"
    assert comment_two.status == "resolved"
    assert db.commit.await_count >= 2
    assert db.add.call_count >= 1


def test_refine_from_comments_forbidden_for_non_admin():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="auditor",
        email="auditor@test.edu",
        full_name="Auditor",
        is_active=True,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, current_user)
    response = client.post(
        f"/api/v1/exams/{exam_id}/refine-from-comments",
        json={},
    )

    assert response.status_code == 403
    assert db.commit.await_count == 0


def test_teacher_can_create_generation_proposal():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    document_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh_proposal(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_refresh_proposal)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: object()))

    client = _build_test_app(db, current_user)
    response = client.post(
        "/api/v1/exams/generation-proposals",
        json={
            "subject": "Biology",
            "grade_level": "SSS 1",
            "document_ids": [str(document_id)],
            "desired_outcomes": "Focus on cell biology and photosynthesis with practical examples.",
            "custom_instructions": "Align to school end-of-term format.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "Biology"
    assert payload["status"] == "open"
    assert payload["document_ids"] == [str(document_id)]
    assert db.commit.await_count == 1
    assert db.add.call_count == 1


def test_admin_can_generate_exam_from_proposal():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    document_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )

    proposal = SimpleNamespace(
        id=proposal_id,
        school_id=school_id,
        status="open",
        subject="Chemistry",
        grade_level="SSS 2",
        document_ids=[str(document_id)],
        desired_outcomes="Cover acids, bases, salts and balancing equations.",
        custom_instructions="Use WAEC-style command words.",
        draft_questions="Define acid and base with examples.",
        used_by_user_id=None,
        used_at=None,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: proposal),
            SimpleNamespace(scalar_one_or_none=lambda: object()),
            SimpleNamespace(scalar=lambda: 0),
        ]
    )

    client = _build_test_app(db, current_user)
    response = client.post(
        f"/api/v1/exams/generation-proposals/{proposal_id}/generate",
        json={
            "sections": [
                {
                    "section_number": 1,
                    "section_title": "SECTION A",
                    "question_type": "multiple_choice",
                    "num_questions": 10,
                    "marks_per_question": 1,
                    "instruction_type": "answer_all",
                    "sub_part_style": "none",
                }
            ],
            "duration_minutes": 60,
            "include_diagrams": False,
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "generating"
    assert proposal.status == "used"
    assert proposal.used_by_user_id == user_id
    assert db.commit.await_count == 1
    assert db.add.call_count >= 1


def test_non_admin_cannot_generate_exam_from_proposal():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="auditor",
        email="auditor@test.edu",
        full_name="Auditor",
        is_active=True,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, current_user)
    response = client.post(
        f"/api/v1/exams/generation-proposals/{proposal_id}/generate",
        json={
            "sections": [
                {
                    "section_number": 1,
                    "section_title": "SECTION A",
                    "question_type": "multiple_choice",
                    "num_questions": 5,
                    "marks_per_question": 1,
                    "instruction_type": "answer_all",
                    "sub_part_style": "none",
                }
            ],
        },
    )

    assert response.status_code == 403
    assert db.commit.await_count == 0


def test_teacher_can_submit_manual_exam():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )

    exam = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=school_id,
        created_by_user_id=user_id,
        subject="Physics",
        grade_level="SSS 1",
        status="under_review",
        workflow_state="final_submitted_by_teacher",
        total_marks=15,
        duration_minutes=90,
        instructions="Answer all questions.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    questions = [
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=1,
            type="essay",
            question_text="Define force and give two examples.",
            marks=10,
            difficulty="medium",
            bloom_level="understand",
            topic="Mechanics",
            options=None,
            correct_answer=None,
            explanation=None,
            marking_scheme=["Definition", "Two examples"],
            sub_parts=None,
            diagram_svg=None,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=2,
            type="short_answer",
            question_text="State Newton's first law.",
            marks=5,
            difficulty="easy",
            bloom_level="remember",
            topic="Mechanics",
            options=None,
            correct_answer=None,
            explanation=None,
            marking_scheme=["Accurate statement"],
            sub_parts=None,
            diagram_svg=None,
        ),
    ]

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=lambda: setattr(exam, "id", exam.id))
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)
    db.execute = AsyncMock(
        return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: questions))
    )

    def _capture_add(obj):
        from app.models.exam import Exam as ExamModel

        if isinstance(obj, ExamModel):
            obj.id = exam.id
            obj.school_id = exam.school_id
            obj.created_by_user_id = exam.created_by_user_id
            obj.subject = exam.subject
            obj.grade_level = exam.grade_level
            obj.status = exam.status
            obj.workflow_state = exam.workflow_state
            obj.total_marks = exam.total_marks
            obj.duration_minutes = exam.duration_minutes
            obj.instructions = exam.instructions
            obj.created_at = exam.created_at
            obj.updated_at = exam.updated_at

    db.add.side_effect = _capture_add

    client = _build_test_app(db, current_user)
    response = client.post(
        "/api/v1/exams/manual-submit",
        json={
            "subject": "Physics",
            "grade_level": "SSS 1",
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
    assert payload["status"] == "under_review"
    assert payload["total_marks"] == 15
    assert len(payload["questions"]) == 2


def test_teacher_can_submit_audit_comment():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    exam = SimpleNamespace(id=exam_id, school_id=school_id, status="under_review")
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    async def _refresh_comment(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)
    db.refresh = AsyncMock(side_effect=_refresh_comment)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: exam))

    client = _build_test_app(db, current_user)
    response = client.post(
        f"/api/v1/exams/{exam_id}/audit-comments",
        json={"comment_text": "Please change question 2"},
    )

    assert response.status_code == 200


def test_quality_report_endpoint_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )

    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        subject="English Language",
        grade_level="Primary 4",
    )
    questions = [
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=1,
            type="multiple_choice",
            question_text="In Abuja, which word is a noun?",
            marks=1,
            difficulty="easy",
            bloom_level="remember",
            options=["A. run", "B. market", "C. quickly", "D. under"],
            correct_answer="B",
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=2,
            type="essay",
            question_text="Write five sentences about your community in Nigeria.",
            marks=5,
            difficulty="medium",
            bloom_level="apply",
            options=None,
            correct_answer=None,
        ),
    ]
    contexts = [
        SimpleNamespace(extracted_context="Community, grammar, nouns, sentences, Nigeria, Abuja")
    ]

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: exam),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: questions)),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: contexts)),
        ]
    )

    client = _build_test_app(db, current_user)
    response = client.get(f"/api/v1/exams/{exam_id}/quality-report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "English Language"
    assert payload["coverage"]["score"] >= 0
    assert "distribution" in payload
    assert payload["quality_status"] in {"green", "amber", "red"}
    assert "overall_score" in payload


def test_quality_report_forbidden_for_unknown_role():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="parent",
        email="parent@test.edu",
        full_name="Parent",
        is_active=True,
    )
    db = AsyncMock()
    db.execute = AsyncMock()

    client = _build_test_app(db, current_user)
    response = client.get(f"/api/v1/exams/{exam_id}/quality-report")

    assert response.status_code == 403


def test_quality_report_snapshot_persistence():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )
    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        subject="Mathematics",
        grade_level="Primary 5",
    )
    questions = [
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=1,
            type="multiple_choice",
            question_text="A student in Abuja bought 3 books for 300 naira. What is one book?",
            marks=2,
            difficulty="easy",
            bloom_level="apply",
            options=["A. 50", "B. 75", "C. 100", "D. 150"],
            correct_answer="C",
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=2,
            type="multiple_choice",
            question_text="Which number is divisible by 5?",
            marks=2,
            difficulty="easy",
            bloom_level="remember",
            options=["A. 23", "B. 30", "C. 17", "D. 41"],
            correct_answer="B",
        ),
    ]
    contexts = [
        SimpleNamespace(extracted_context="numbers divisible Abuja naira primary mathematics")
    ]

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: exam),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: questions)),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: contexts)),
        ]
    )

    client = _build_test_app(db, current_user)
    response = client.get(f"/api/v1/exams/{exam_id}/quality-report?save_snapshot=true")

    assert response.status_code == 200
    assert db.add.call_count == 1
    assert db.commit.await_count == 1


def test_list_quality_snapshots_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    exam = SimpleNamespace(id=exam_id, school_id=school_id)
    snapshots = [
        SimpleNamespace(
            id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            quality_status="amber",
            overall_score="42.5",
            report_data={"coverage": {"score": 55.0}},
        )
    ]

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: exam),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: snapshots)),
        ]
    )

    client = _build_test_app(db, current_user)
    response = client.get(f"/api/v1/exams/{exam_id}/quality-reports")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["snapshots"][0]["quality_status"] == "amber"


def test_save_exam_questions_to_bank_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    exam = SimpleNamespace(id=exam_id, school_id=school_id, subject="Maths", grade_level="Primary 4")
    questions = [
        SimpleNamespace(
            id=uuid.uuid4(),
            question_number=1,
            topic="Fractions",
            difficulty="easy",
            type="multiple_choice",
            question_text="Which is one-half?",
            marks=1,
            options=["A. 1/2", "B. 1/3", "C. 1/4", "D. 2/3"],
            correct_answer="A",
            explanation=None,
            marking_scheme=None,
            sub_parts=None,
            diagram_svg=None,
        )
    ]
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: exam),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: questions)),
        ]
    )

    client = _build_test_app(db, current_user)
    response = client.post(f"/api/v1/exams/{exam_id}/question-bank/save", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved_count"] == 1
    assert db.add.call_count == 1


def test_list_question_bank_items_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    item = SimpleNamespace(
        id=uuid.uuid4(),
        school_id=school_id,
        source_exam_id=None,
        source_question_id=None,
        created_by_user_id=user_id,
        subject="English",
        grade_level="Primary 4",
        topic="Comprehension",
        difficulty="medium",
        question_type="essay",
        question_text="Write five sentences.",
        marks=5,
        options=None,
        correct_answer=None,
        explanation=None,
        marking_scheme=["Clarity", "Grammar"],
        sub_parts=None,
        diagram_svg=None,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [item])))

    client = _build_test_app(db, current_user)
    response = client.get("/api/v1/exams/question-bank/items?subject=English")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["subject"] == "English"


def test_update_question_bank_item_success():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    item_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    item = SimpleNamespace(
        id=item_id,
        school_id=school_id,
        source_exam_id=None,
        source_question_id=None,
        created_by_user_id=user_id,
        subject="English",
        grade_level="Primary 4",
        topic="Comprehension",
        difficulty="medium",
        question_type="essay",
        question_text="Write five sentences.",
        marks=5,
        options=None,
        correct_answer=None,
        explanation=None,
        marking_scheme=["Clarity"],
        sub_parts=None,
        diagram_svg=None,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: item))

    client = _build_test_app(db, current_user)
    response = client.patch(
        f"/api/v1/exams/question-bank/items/{item_id}",
        json={"question_text": "Write six meaningful sentences.", "marks": 6},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["question_text"] == "Write six meaningful sentences."
    assert payload["marks"] == 6


def test_teacher_cannot_call_direct_generate():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    client = _build_test_app(db, current_user)
    response = client.post(
        "/api/v1/exams/generate",
        json={
            "subject": "English",
            "grade_level": "Primary 4",
            "document_ids": [str(uuid.uuid4())],
            "sections": [
                {
                    "section_number": 1,
                    "section_title": "SECTION A",
                    "question_type": "multiple_choice",
                    "num_questions": 5,
                    "marks_per_question": 1,
                    "instruction_type": "answer_all",
                    "sub_part_style": "none",
                }
            ],
            "duration_minutes": 60,
        },
    )

    assert response.status_code == 403


def test_approve_requires_teacher_final_submission_state():
    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    current_user = SimpleNamespace(
        user_id=user_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )
    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        status="under_review",
        workflow_state="teacher_review",
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: exam))

    client = _build_test_app(db, current_user)
    response = client.post(f"/api/v1/exams/{exam_id}/approve")

    assert response.status_code == 400


def test_teacher_can_submit_final_then_admin_can_approve():
    school_id = uuid.uuid4()
    teacher_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    exam_id = uuid.uuid4()
    exam = SimpleNamespace(
        id=exam_id,
        school_id=school_id,
        created_by_user_id=teacher_id,
        status="under_review",
        workflow_state="teacher_review",
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: exam))

    teacher_user = SimpleNamespace(
        user_id=teacher_id,
        school_id=school_id,
        role="teacher",
        email="teacher@test.edu",
        full_name="Teacher",
        is_active=True,
    )
    teacher_client = _build_test_app(db, teacher_user)
    submit_response = teacher_client.post(f"/api/v1/exams/{exam_id}/submit-final")
    assert submit_response.status_code == 200
    assert exam.workflow_state == "final_submitted_by_teacher"

    admin_user = SimpleNamespace(
        user_id=admin_id,
        school_id=school_id,
        role="school_admin",
        email="admin@test.edu",
        full_name="Admin",
        is_active=True,
    )
    admin_client = _build_test_app(db, admin_user)
    approve_response = admin_client.post(f"/api/v1/exams/{exam_id}/approve")
    assert approve_response.status_code == 200
