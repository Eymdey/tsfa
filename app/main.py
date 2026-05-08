"""FastAPI application entry point.

Sets up the application with:
- Lifespan context manager (Redis startup/shutdown)
- CORS middleware
- Structured request logging middleware
- Global exception handlers
- All API routers mounted under /v1
- Health check endpoint at /health
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware, configure_structlog
from app.middleware.error_handler import register_error_handlers
from app.routers import forecast, validate, models, usage

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle.

    On startup:
    - Configure structlog
    - Connect to Redis
    - Log startup info

    On shutdown:
    - Close Redis connection

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to the application while it is running.
    """
    # Configure structured logging
    configure_structlog()

    # Connect to Redis
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
            message="Proceeding without Redis cache. Requests will not be cached.",
        )
        app.state.redis = None

    # Initialise Sentry if DSN is configured
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

    yield  # Application runs here

    # Shutdown
    if redis_client is not None:
        await redis_client.aclose()
        logger.info("redis_disconnected")

    logger.info("application_shutdown")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance ready for serving.
    """
    app = FastAPI(
        title="TSFA — Time Series Forecasting API",
        description=(
            "Professional time series forecasting API. "
            "Predict future values with confidence intervals in 3 lines of code. "
            "Phase 1: AutoARIMA. Phase 2: Chronos, LSTM, TiDE, Ensemble."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS — allow all origins in development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://api.tsfa.io"],
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
    async def health_check() -> dict[str, str]:
        """Return API health status.

        Returns:
            JSON object with status and version fields.
        """
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
