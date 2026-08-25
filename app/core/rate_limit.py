"""In-process login throttling (MVP: single-instance sliding window).

For multi-instance deployments move this to a shared store (Postgres or
Redis). Kept dependency-free intentionally for the pilot.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

_MAX_FAILURES = 5
_WINDOW_SECONDS = 900  # 15 minutes
_LOCKOUT_SECONDS = 900

_failures: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
_lockouts: Dict[Tuple[str, str], float] = {}


def _key(email: str, ip: str) -> Tuple[str, str]:
    return (email.strip().lower(), ip or "unknown")


def is_locked_out(email: str, ip: str) -> bool:
    """True when this email+ip is currently locked out."""
    key = _key(email, ip)
    until = _lockouts.get(key)
    if until is None:
        return False
    if time.monotonic() >= until:
        _lockouts.pop(key, None)
        _failures.pop(key, None)
        return False
    return True


def record_failure(email: str, ip: str) -> None:
    """Record a failed login; lock the key after too many failures."""
    key = _key(email, ip)
    now = time.monotonic()
    window = _failures[key]
    window.append(now)
    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()
    if len(window) >= _MAX_FAILURES:
        _lockouts[key] = now + _LOCKOUT_SECONDS
        _failures.pop(key, None)


def record_success(email: str, ip: str) -> None:
    """Clear failure state on successful login."""
    key = _key(email, ip)
    _failures.pop(key, None)
    _lockouts.pop(key, None)


def reset_all() -> None:
    """Test helper."""
    _failures.clear()
    _lockouts.clear()
