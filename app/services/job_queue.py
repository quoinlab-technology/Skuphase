"""Postgres-backed job queue for exam generation (no external broker).

Design:
- ``enqueue_generation_job`` inserts a pending row in the caller's session.
- A single asyncio worker (started in the app lifespan) polls every few
  seconds using ``FOR UPDATE SKIP LOCKED`` so multiple app instances are safe.
- Transient provider errors re-queue with exponential backoff; permanent
  validation/parse failures mark job + exam failed without retrying
  (retries never multiply LLM cost for deterministic errors).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select, update

from app.config.settings import get_settings
from app.models.exam import Exam
from app.models.job import GenerationJob
from app.schemas.exam import ExamGenerationRequest

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 2.0
_BATCH_SIZE = 5
_STALE_RUNNING_MINUTES = 10

# Error substrings that are worth retrying; everything else is permanent.
_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "connection",
    "rate limit",
    "429",
    "502",
    "503",
    "504",
    "temporarily",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_transient(error: Exception) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in _TRANSIENT_MARKERS)


async def enqueue_generation_job(
    session,
    *,
    exam_id: uuid.UUID,
    request_data: Dict[str, Any],
    school_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
) -> uuid.UUID:
    """Insert a pending generation job inside the caller's transaction."""
    settings = get_settings()
    job = GenerationJob(
        id=uuid.uuid4(),
        exam_id=exam_id,
        school_id=school_id,
        status="pending",
        attempts=0,
        max_attempts=max(1, settings.background_retry_attempts),
        run_at=utc_now(),
        request_data={
            **request_data,
            "__created_by_user_id": str(created_by_user_id),
        },
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(job)
    await session.flush()
    return job.id


async def _process_one(job_id: uuid.UUID) -> None:
    """Run one queued generation attempt with its own short sessions."""
    from app.core.database import get_async_session_maker
    from app.services.exam_generator import ExamGenerator

    session_maker = get_async_session_maker()

    async with session_maker() as db:
        result = await db.execute(
            select(GenerationJob).where(GenerationJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None or job.status not in {"pending", "running"}:
            return

        exam_id = job.exam_id
        school_id = job.school_id
        request_data = dict(job.request_data)
        created_by = uuid.UUID(request_data.pop("__created_by_user_id"))
        attempts = (job.attempts or 0) + 1

        job.attempts = attempts
        job.status = "running"
        job.updated_at = utc_now()
        await db.commit()

    try:
        request = ExamGenerationRequest(**request_data)
        generator = ExamGenerator()

        async with session_maker() as db:
            # Stage 1+2 happen inside generate_exam; it releases its read
            # transaction before the LLM call and commits writes itself.
            exam = await generator.generate_exam(
                request=request,
                school_id=school_id,
                created_by_user_id=created_by,
                db=db,
                exam_id=exam_id,
            )
            logger.info("Generation job succeeded for exam %s", exam.id)

        async with session_maker() as db:
            await db.execute(
                update(GenerationJob)
                .where(GenerationJob.id == job_id)
                .values(status="succeeded", updated_at=utc_now(), last_error=None)
            )
            await db.commit()

    except Exception as exc:
        logger.error(
            "Generation job failed for exam %s (attempt %s): %s",
            exam_id,
            attempts,
            exc,
        )
        retryable = _is_transient(exc) and attempts < 3
        async with session_maker() as db:
            job_row = (await db.execute(
                select(GenerationJob).where(GenerationJob.id == job_id)
            )).scalar_one_or_none()

            if retryable:
                base_delay = max(0.5, float(get_settings().background_retry_base_delay_seconds))
                delay = base_delay * (2 ** (attempts - 1))
                if job_row is not None:
                    job_row.status = "pending"
                    job_row.attempts = attempts
                    job_row.last_error = str(exc)[:2000]
                    job_row.run_at = utc_now() + timedelta(seconds=delay)
                    job_row.updated_at = utc_now()
                await db.commit()
                logger.info("Requeued exam %s in %.1fs (transient error)", exam_id, delay)
            else:
                # Permanent failure: mark job failed and surface on the exam.
                if job_row is not None:
                    job_row.status = "failed"
                    job_row.attempts = attempts
                    job_row.last_error = str(exc)[:2000]
                    job_row.updated_at = utc_now()
                exam_row = (await db.execute(
                    select(Exam).where(Exam.id == exam_id)
                )).scalar_one_or_none()
                if exam_row is not None:
                    exam_row.status = "failed"
                    exam_row.updated_at = utc_now()
                await db.commit()


async def _worker_loop(stop_event: asyncio.Event) -> None:
    """Poll for due jobs and execute them sequentially per batch."""
    from app.core.database import get_async_session_maker

    session_maker = get_async_session_maker()

    while not stop_event.is_set():
        try:
            now = utc_now()
            stale_cutoff = now - timedelta(minutes=_STALE_RUNNING_MINUTES)

            async with session_maker() as db:
                # Reap jobs stuck 'running' after a crash/restart.
                await db.execute(
                    update(GenerationJob)
                    .where(
                        GenerationJob.status == "running",
                        GenerationJob.updated_at < stale_cutoff,
                    )
                    .values(status="pending", updated_at=utc_now())
                )

                result = await db.execute(
                    select(GenerationJob.id)
                    .where(
                        GenerationJob.status == "pending",
                        GenerationJob.run_at <= now,
                    )
                    .order_by(GenerationJob.created_at)
                    .limit(_BATCH_SIZE)
                    .with_for_update(skip_locked=True)
                )
                job_ids = [row[0] for row in result.all()]
                await db.commit()

            for job_id in job_ids:
                await _process_one(job_id)

        except Exception:
            logger.exception("Job worker loop iteration failed")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS * 2)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=_POLL_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass


_worker_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


async def start_worker() -> None:
    """Start the background worker (idempotent)."""
    global _worker_task, _stop_event
    if _worker_task is not None and not _worker_task.done():
        return
    _stop_event = asyncio.Event()
    _worker_task = asyncio.create_task(_worker_loop(_stop_event))


async def stop_worker() -> None:
    """Signal the worker to stop and wait briefly."""
    global _worker_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _worker_task is not None:
        try:
            await asyncio.wait_for(_worker_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _worker_task.cancel()
    _worker_task = None
    _stop_event = None
