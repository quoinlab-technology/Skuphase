"""DB-backed login throttling tests (audit F-07)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import rate_limit
from app.models.login_attempt import LoginAttempt


def _db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_is_locked_out_true_after_five_failures():
    db = _db()
    result = MagicMock()
    result.scalar.return_value = 5
    db.execute = AsyncMock(return_value=result)

    assert await rate_limit.is_locked_out(db, "User@Example.com", "1.2.3.4") is True


@pytest.mark.asyncio
async def test_is_locked_out_false_below_threshold():
    db = _db()
    result = MagicMock()
    result.scalar.return_value = 4
    db.execute = AsyncMock(return_value=result)

    assert await rate_limit.is_locked_out(db, "user@example.com", "1.2.3.4") is False


@pytest.mark.asyncio
async def test_record_failure_prunes_and_inserts():
    db = _db()
    db.execute = AsyncMock()
    db.execute.side_effect = [MagicMock(), MagicMock()]

    await rate_limit.record_failure(db, "user@example.com", "1.2.3.4")

    # One prune DELETE then one INSERT committed.
    assert db.add.call_count == 1
    assert db.commit.await_count == 1
    added = db.add.call_args[0][0]
    assert isinstance(added, LoginAttempt)
    assert added.email_lower == "user@example.com"
    assert added.ip == "1.2.3.4"
    assert added.success is False


@pytest.mark.asyncio
async def test_record_success_clears_failures():
    db = _db()
    db.execute = AsyncMock()
    await rate_limit.record_success(db, "user@example.com", "1.2.3.4")

    assert db.commit.await_count == 1


def test_normalize_lowercases_email_and_defaults_ip():
    assert rate_limit._normalize("  User@Example.com ", None) == ("user@example.com", "unknown")