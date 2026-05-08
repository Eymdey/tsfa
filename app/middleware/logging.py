"""Structured request/response logging middleware.

Logs every HTTP request as a JSON event using structlog, including:
- Unique request_id (uuid4)
- HTTP method and path
- Response status code
- Request duration in milliseconds
"""

import time
import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


def configure_structlog() -> None:
    """Configure structlog for JSON output.

    Should be called once at application startup before any logging occurs.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that emits a structured log entry per request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process a request, log it, and forward the response.

        Args:
            request: Incoming Starlette/FastAPI request.
            call_next: Next middleware or route handler.

        Returns:
            The HTTP response.
        """
        request_id = str(uuid.uuid4())
        start = time.monotonic()

        # Bind request_id to structlog context variables so all log lines
        # within this request automatically include it.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Attach request_id to request state for downstream handlers
        request.state.request_id = request_id

        response: Response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000.0

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_host=request.client.host if request.client else None,
        )

        # Propagate request_id in response headers for client-side correlation
        response.headers["X-Request-ID"] = request_id

        return response
