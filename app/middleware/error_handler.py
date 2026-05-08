"""Global exception handler for FastAPI.

Converts Python exceptions into structured JSON error responses:
- ValueError         → HTTP 400 Bad Request
- NotImplementedError → HTTP 501 Not Implemented
- Exception          → HTTP 500 Internal Server Error
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to a FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle validation / business logic errors as 400 Bad Request.

        Args:
            request: Incoming request.
            exc: The ValueError that was raised.

        Returns:
            JSON error response with HTTP 400.
        """
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
        """Handle unimplemented features as 501 Not Implemented.

        Args:
            request: Incoming request.
            exc: The NotImplementedError that was raised.

        Returns:
            JSON error response with HTTP 501.
        """
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
                "message": str(exc) or "This feature is coming in Phase 2.",
                "details": None,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions as 500 Internal Server Error.

        Args:
            request: Incoming request.
            exc: Any unhandled exception.

        Returns:
            JSON error response with HTTP 500.
        """
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
