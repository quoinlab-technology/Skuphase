"""Request correlation for pilot support and incident investigation."""
from __future__ import annotations
import logging
import time
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("skuphase.request")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%s", request_id, request.method, request.url.path, response.status_code, elapsed_ms)
        return response
