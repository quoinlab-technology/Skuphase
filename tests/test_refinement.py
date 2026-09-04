"""Refinement workflow-state guard tests (audit F-02).

Refinement must be impossible from terminal/invalid states — approved exams are
immutable, and `generation_requested`/`failed` exams have no final questions.
These guards run BEFORE the LLM call budget is consumed.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import exams_router
from app.core.database import get_db_session
from app.core.dependencies import get_current_user

from tests.test_exams_router import _admin, _build_test_app


def _exam(workflow_state: str, status: str = "under_review") -> SimpleNamespace:
    user = _admin()
    return SimpleNamespace(
        id=uuid.uuid4(),
        school_id=user.school_id,
        created_by_user_id=user.user_id,
        status=status,
        workflow_state=workflow_state,
        llm_call_count=1,
        llm_call_limit=3,
    )


def _db_returning(obj) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _execute(stmt, *args, **kwargs):
        class _Result:
            def scalar_one_or_none(self_inner):
                return obj

        return _Result()

    db.execute = AsyncMock(side_effect=_execute)
    return db


def test_refine_rejects_approved_exam_with_409():
    user = _admin()
    exam = _exam("approved", status="approved")
    client = _build_test_app(_db_returning(exam), user)

    response = client.post(
        f"/api/v1/exams/{exam.id}/refine",
        json={"feedback": "make it harder"},
    )

    assert response.status_code == 409
    # Guard fires before the budget is consumed.
    assert exam.llm_call_count == 1


def test_refine_rejects_generation_requested_exam_with_400():
    user = _admin()
    exam = _exam("generation_requested", status="draft")
    client = _build_test_app(_db_returning(exam), user)

    response = client.post(
        f"/api/v1/exams/{exam.id}/refine",
        json={"feedback": "make it harder"},
    )

    assert response.status_code == 400
    assert exam.llm_call_count == 1


def test_refine_from_comments_rejects_approved_exam_with_409():
    user = _admin()
    exam = _exam("approved", status="approved")
    client = _build_test_app(_db_returning(exam), user)

    response = client.post(
        f"/api/v1/exams/{exam.id}/refine-from-comments",
        json={},
    )

    assert response.status_code == 409
    assert exam.llm_call_count == 1


def test_submit_final_rejects_approved_exam_with_409():
    user = _admin()
    exam = _exam("approved", status="approved")
    client = _build_test_app(_db_returning(exam), user)

    response = client.post(f"/api/v1/exams/{exam.id}/submit-final")

    assert response.status_code == 409


def test_submit_final_rejects_generation_requested_exam_with_400():
    user = _admin()
    exam = _exam("generation_requested", status="draft")
    client = _build_test_app(_db_returning(exam), user)

    response = client.post(f"/api/v1/exams/{exam.id}/submit-final")

    assert response.status_code == 400

