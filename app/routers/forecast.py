"""Forecast router — /v1/forecast/* endpoints."""

import asyncio
import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.dependencies import get_plan, check_rate_limit
from app.schemas.forecast import (
    UnivariateForecastRequest,
    MultivariateForecastRequest,
    BatchForecastRequest,
    BatchForecastResponse,
    BatchSeriesResult,
    ForecastResponse,
)
from app.services.forecaster import run_univariate_forecast

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/forecast", tags=["Forecast"])

# Batch size limits per plan
_BATCH_LIMITS: dict[str, int] = {
    "pro": 50,
    "ultra": 500,
}


@router.post(
    "/univariate",
    response_model=ForecastResponse,
    summary="Univariate time series forecast",
    description=(
        "Generate a point forecast with prediction intervals for a single time series. "
        "Supports automatic frequency and model selection."
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
    _: None = Depends(check_rate_limit),
) -> ForecastResponse:
    """Generate a univariate time series forecast."""
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
    """Multivariate forecast endpoint — Phase 2 stub."""
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
    response_model=BatchForecastResponse,
    summary="Batch forecast for multiple series",
    description=(
        "Forecast multiple series in a single request. "
        "Available for Pro (max 50 series) and Ultra (max 500 series) plans."
    ),
    responses={
        403: {"description": "Plan does not support batch forecasting"},
        422: {"description": "Too many series for plan"},
    },
)
async def forecast_batch(
    payload: BatchForecastRequest,
    request: Request,
    plan: str = Depends(get_plan),
) -> BatchForecastResponse:
    """Batch forecast endpoint — runs all series concurrently."""
    # Plan restriction: free and basic cannot use batch
    if plan in ("free", "basic"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PLAN_RESTRICTION",
                "message": "Batch forecasting requires a Pro or Ultra plan.",
            },
        )

    # Series count limit per plan
    max_series = _BATCH_LIMITS.get(plan, 500)
    if len(payload.series_list) > max_series:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TOO_MANY_SERIES",
                "message": f"Your {plan} plan allows at most {max_series} series per batch request.",
            },
        )

    redis_client: Any | None = getattr(request.app.state, "redis", None)
    t_start = time.monotonic()

    logger.info(
        "batch_forecast_request",
        plan=plan,
        n_series=len(payload.series_list),
    )

    async def _forecast_one(item) -> BatchSeriesResult:
        """Run forecast for a single series, isolating errors."""
        try:
            req = UnivariateForecastRequest(
                series=item.values,
                timestamps=item.timestamps,
                horizon=item.horizon,
                frequency=payload.frequency,
                model=payload.model,
                confidence_levels=payload.confidence_levels,
            )
            resp = await run_univariate_forecast(req, redis_client)
            return BatchSeriesResult(
                id=item.id,
                status="success",
                forecast=resp.forecast,
                model_used=resp.model_used,
                meta=resp.meta,
                error=None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("batch_series_error", series_id=item.id, error=str(exc))
            return BatchSeriesResult(
                id=item.id,
                status="error",
                forecast=None,
                model_used=None,
                meta=None,
                error=str(exc),
            )

    results = await asyncio.gather(*[_forecast_one(item) for item in payload.series_list])

    total_credits = sum(
        r.meta.credits_used for r in results if r.meta is not None
    )
    processing_time_ms = (time.monotonic() - t_start) * 1000.0

    return BatchForecastResponse(
        status="success",
        results=list(results),
        total_credits_used=total_credits,
        processing_time_ms=processing_time_ms,
    )
