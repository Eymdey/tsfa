"""Forecast router — /v1/forecast/* endpoints.

Phase 1: POST /v1/forecast/univariate is fully functional.
Phase 2: POST /v1/forecast/multivariate and /v1/forecast/batch.
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.dependencies import get_plan
from app.schemas.forecast import (
    UnivariateForecastRequest,
    MultivariateForecastRequest,
    BatchForecastRequest,
    ForecastResponse,
)
from app.services.forecaster import run_univariate_forecast

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.post(
    "/univariate",
    response_model=ForecastResponse,
    summary="Univariate time series forecast",
    description=(
        "Generate a point forecast with prediction intervals for a single time series. "
        "Uses AutoARIMA in Phase 1. Supports automatic frequency and model selection."
    ),
    responses={
        400: {"description": "Invalid input data"},
        422: {"description": "Validation error"},
    },
)
async def forecast_univariate(
    payload: UnivariateForecastRequest,
    request: Request,
    plan: str = Depends(get_plan),
) -> ForecastResponse:
    """Generate a univariate time series forecast.

    Args:
        payload: Validated request body.
        request: FastAPI Request (used to access Redis client from app state).
        plan: Resolved subscription plan from request headers.

    Returns:
        ForecastResponse with forecast values, diagnostics, and metadata.
    """
    redis_client: Any | None = getattr(request.app.state, "redis", None)

    log = logger.bind(plan=plan, series_length=len(payload.series))
    log.info("univariate_forecast_request", horizon=payload.horizon, model=payload.model)

    response = await run_univariate_forecast(payload, redis_client)
    return response


@router.post(
    "/multivariate",
    summary="Multivariate time series forecast (Phase 2)",
    description="Forecast with covariates using TiDE. Available in Phase 2.",
    responses={
        501: {"description": "Not implemented — coming in Phase 2"},
    },
    status_code=501,
)
async def forecast_multivariate(
    payload: MultivariateForecastRequest,
    plan: str = Depends(get_plan),
) -> JSONResponse:
    """Multivariate forecast endpoint — Phase 2 stub.

    Args:
        payload: Validated request body.
        plan: Resolved subscription plan.

    Returns:
        501 JSON response.
    """
    return JSONResponse(
        status_code=501,
        content={
            "status": "error",
            "code": "NOT_IMPLEMENTED",
            "message": "Multivariate forecasting with covariates is coming in Phase 2.",
            "details": None,
        },
    )


@router.post(
    "/batch",
    summary="Batch forecast for multiple series (Phase 2)",
    description="Forecast multiple series in a single request. Available in Phase 2 for Pro/Ultra plans.",
    responses={
        501: {"description": "Not implemented — coming in Phase 2"},
    },
    status_code=501,
)
async def forecast_batch(
    payload: BatchForecastRequest,
    plan: str = Depends(get_plan),
) -> JSONResponse:
    """Batch forecast endpoint — Phase 2 stub.

    Args:
        payload: Validated request body.
        plan: Resolved subscription plan.

    Returns:
        501 JSON response.
    """
    return JSONResponse(
        status_code=501,
        content={
            "status": "error",
            "code": "NOT_IMPLEMENTED",
            "message": "Batch forecasting is coming in Phase 2 for Pro and Ultra plans.",
            "details": None,
        },
    )
