"""Postgres-backed job queue unit tests (mocked session)."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import job_queue
from app.schemas.exam import ExamGenerationRequest, SectionConfig


def test_is_transient_classification():
    assert job_queue._is_transient(RuntimeError("connection reset by peer"))
    assert job_queue._is_transient(RuntimeError("HTTP 429 rate limit"))
    assert job_queue._is_transient(RuntimeError("request timed out"))
    assert not job_queue._is_transient(RuntimeError("Generated exam failed quality validation"))
    assert not job_queue._is_transient(RuntimeError("Invalid JSON response"))


@pytest.mark.asyncio
async def test_enqueue_generation_job_inserts_pending_row():
    added = []
    session = MagicMock()
    session.add = MagicMock(side_effect=lambda obj: added.append(obj))

    async def _flush():
        added[-1].id = uuid.uuid4()

    session.flush = AsyncMock(side_effect=_flush)

    request = ExamGenerationRequest(
        subject="Basic Science",
        grade_level="Primary 4",
        term="First Term",
        selected_weeks=[1],
        sections=[
            SectionConfig(
                section_number=1,
                section_title="SECTION A",
                question_type="multiple_choice",
                num_questions=2,
                marks_per_question=2,
                instruction_type="answer_all",
                sub_part_style="none",
            )
        ],
    )

    school_id = uuid.uuid4()
    user_id = uuid.uuid4()
    exam_id = uuid.uuid4()

    job_id = await job_queue.enqueue_generation_job(
        session,
        exam_id=exam_id,
        request_data=request.model_dump(mode="json"),
        school_id=school_id,
        created_by_user_id=user_id,
    )

    assert job_id == added[-1].id
    job = added[-1]
    assert job.status == "pending"
    assert job.attempts == 0
    assert job.exam_id == exam_id
    assert job.school_id == school_id
    # The creating user id rides along inside request_data for the worker.
    assert job.request_data["__created_by_user_id"] == str(user_id)


def test_claim_statement_is_atomic_and_locked():
    """Structural guard: claim must be UPDATE...RETURNING with SKIP LOCKED."""
    import inspect

    source = inspect.getsource(job_queue._claim_jobs)
    assert "skip_locked=True" in source
    assert ".returning(" in source
    assert '.values(status="running"' in source


def test_worker_concurrency_is_bounded():
    """Structural guard: worker uses a semaphore, not unbounded gather."""
    import inspect

    source = inspect.getsource(job_queue._worker_loop)
    assert "Semaphore" in source
    assert "asyncio.gather" in source


def test_stale_reap_threshold_exceeds_llm_timeout():
    """A running job must never be reaped while its LLM call can still be live."""
    from app.config.settings import get_settings

    settings = get_settings()
    llm_timeout_seconds = settings.llm_timeout_seconds + 30
    assert job_queue._STALE_RUNNING_MINUTES * 60 > llm_timeout_seconds
