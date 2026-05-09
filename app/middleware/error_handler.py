"""Global exception handler for FastAPI.

Converts Python exceptions into structured JSON error responses:
- ValueError          → HTTP 400 Bad Request
- NotImplementedError → HTTP 501 Not Implemented
- ModalTimeoutError   → HTTP 503 Service Unavailable
- ModalConnectionError → HTTP 503 Service Unavailable
- Exception           → HTTP 500 Internal Server Error
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class ModalTimeoutError(Exception):
    """Raised when a Modal.com inference call exceeds its timeout."""


class ModalConnectionError(Exception):
    """Raised when the Modal.com backend is unreachable."""


def register_error_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to a FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(ModalTimeoutError)
    async def modal_timeout_handler(request: Request, exc: ModalTimeoutError) -> JSONResponse:
        """Handle Modal inference timeout as 503 Service Unavailable."""
        logger.error(
            "modal_timeout",
            path=request.url.path,
            message=str(exc),
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "code": "INFERENCE_TIMEOUT",
                "message": "ML inference timeout. Please retry.",
                "details": None,
            },
        )

    @app.exception_handler(ModalConnectionError)
    async def modal_connection_handler(request: Request, exc: ModalConnectionError) -> JSONResponse:
        """Handle Modal connection failure as 503 Service Unavailable.

        Note: In most cases the forecaster catches ModalConnectionError and
        falls back to ARIMA automatically (returning 200 with fallback_used=true).
        This handler is a safety net for unhandled propagation.
        """
        logger.error(
            "modal_connection_error",
            path=request.url.path,
            message=str(exc),
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "code": "MODAL_UNAVAILABLE",
                "message": "ML backend unavailable. Please retry.",
                "details": None,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle validation / business logic errors as 400 Bad Request."""
        logger.warning(
            "value_error",
            path=request.url.path,
            message=str(exc),
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "details": None,
            },
        )

    @app.exception_handler(NotImplementedError)
    async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
        """Handle unimplemented features as 501 Not Implemented."""
        logger.info(
            "not_implemented",
            path=request.url.path,
            message=str(exc),
        )
        return JSONResponse(
            status_code=501,
            content={
                "status": "error",
                "code": "NOT_IMPLEMENTED",
                "message": str(exc) or "This feature is coming in a future phase.",
                "details": None,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions as 500 Internal Server Error."""
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            exception_type=type(exc).__name__,
            message=str(exc),
            request_id=getattr(request.state, "request_id", None),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": None,
            },
        )
