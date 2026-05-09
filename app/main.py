"""FastAPI application entry point.

Sets up the application with:
- Lifespan context manager (Redis startup/shutdown)
- GZip compression middleware
- 30-second global timeout middleware (→ HTTP 503)
- CORS middleware (always wildcard)
- Structured request logging middleware
- Global exception handlers
- All API routers mounted under /v1
- Health check endpoint at /health
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware, configure_structlog
from app.middleware.error_handler import register_error_handlers
from app.routers import forecast, validate, models, usage

logger = structlog.get_logger(__name__)

# Captured at import time for uptime calculation
_app_start_time: float = time.monotonic()


# ---------------------------------------------------------------------------
# Timeout middleware
# ---------------------------------------------------------------------------


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Return HTTP 503 if a request takes longer than `timeout` seconds."""

    def __init__(self, app, timeout: float = 30.0) -> None:
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "code": "REQUEST_TIMEOUT",
                    "message": f"Request exceeded the {int(self.timeout)}s timeout.",
                },
            )


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    configure_structlog()

    redis_client = None
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("redis_connected", url=settings.redis_url)
    except Exception as exc:
        logger.warning(
            "redis_unavailable",
            error=str(exc),
            message="Proceeding without Redis cache.",
        )
        app.state.redis = None

    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[FastApiIntegration()],
                traces_sample_rate=0.1,
            )
            logger.info("sentry_initialised")
        except Exception as exc:
            logger.warning("sentry_init_failed", error=str(exc))

    logger.info(
        "application_startup",
        version="1.0.0",
        debug=settings.debug,
        redis_url=settings.redis_url,
    )

    yield

    if redis_client is not None:
        await redis_client.aclose()
        logger.info("redis_disconnected")

    logger.info("application_shutdown")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TSFA — Time Series Forecasting API",
        description=(
            "Professional time series forecasting API. "
            "Predict future values with confidence intervals in 3 lines of code."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # GZip compression for responses ≥ 1 KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 30-second global request timeout
    app.add_middleware(TimeoutMiddleware, timeout=30.0)

    # CORS — always wildcard (required for RapidAPI proxy)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structured request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Global error handlers
    register_error_handlers(app)

    # API routers — all mounted under /v1
    app.include_router(forecast.router, prefix="/v1")
    app.include_router(validate.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(usage.router, prefix="/v1")

    # Health check — no prefix, no auth required
    @app.get("/health", tags=["Health"])
    async def health_check(request: Request) -> dict:
        """Return API health status with Redis connectivity and uptime."""
        redis_client = getattr(request.app.state, "redis", None)
        redis_connected = False
        if redis_client is not None:
            try:
                await redis_client.ping()
                redis_connected = True
            except Exception:
                redis_connected = False

        return {
            "status": "ok",
            "version": "1.0.0",
            "redis_connected": redis_connected,
            "uptime_seconds": round(time.monotonic() - _app_start_time, 1),
        }

    return app


app = create_app()
