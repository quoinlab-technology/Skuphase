"""DB-backed login throttling (shared across workers and instances).

Any IP string may be passed; callers resolve proxy headers (e.g.
``X-Forwarded-For``) before calling. Five failures for the same (email, ip)
within a 15-minute rolling window locks that pair out until the window clears.

Kept in Postgres (not memory) so throttling survives deploys/restarts and is
shared across uvicorn workers and multiple app instances.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_attempt import LoginAttempt

_MAX_FAILURES = 5
_WINDOW_SECONDS = 900  # 15 minutes


def _normalize(email: str, ip: str) -> Tuple[str, str]:
    return (email or "").strip().lower(), (ip or "unknown")


async def is_locked_out(db: AsyncSession, email: str, ip: str) -> bool:
    """True when this email+ip has too many recent failures."""
    email_lower, ip_key = _normalize(email, ip)
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=_WINDOW_SECONDS)
    result = await db.execute(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            and_(
                LoginAttempt.email_lower == email_lower,
                LoginAttempt.ip == ip_key,
                LoginAttempt.success.is_(False),
                LoginAttempt.attempted_at >= cutoff,
            )
        )
    )
    return (result.scalar() or 0) >= _MAX_FAILURES


async def record_failure(db: AsyncSession, email: str, ip: str) -> None:
    """Record a failed login (prunes out-of-window rows for the same key)."""
    email_lower, ip_key = _normalize(email, ip)
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.email_lower == email_lower,
            LoginAttempt.ip == ip_key,
            LoginAttempt.attempted_at < now - timedelta(seconds=_WINDOW_SECONDS),
        )
    )
    db.add(
        LoginAttempt(
            id=uuid.uuid4(),
            email_lower=email_lower,
            ip=ip_key,
            attempted_at=now,
            success=False,
        )
    )
    await db.commit()


async def record_success(db: AsyncSession, email: str, ip: str) -> None:
    """Clear failure state for this key on successful login."""
    email_lower, ip_key = _normalize(email, ip)
    await db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.email_lower == email_lower,
            LoginAttempt.ip == ip_key,
        )
    )
    await db.commit()
