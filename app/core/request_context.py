"""Request-scoped context helpers for logging."""

from contextvars import ContextVar
import logging

_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    """Store the active request ID in context for the current task."""
    _request_id_ctx_var.set(request_id)


def get_request_id() -> str:
    """Fetch active request ID or fallback placeholder."""
    return _request_id_ctx_var.get()


class RequestIdFilter(logging.Filter):
    """Inject request_id into all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
