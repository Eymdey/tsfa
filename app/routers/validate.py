"""Validate router — POST /v1/validate endpoint.

Backtesting / cross-validation of forecasting models using
sliding window evaluation.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.dependencies import get_plan, verify_rapidapi_proxy
from app.schemas.validate import ValidateRequest, ValidateResponse
from app.services.validator import run_backtest

router = APIRouter(prefix="/validate", tags=["Validate"])


@router.post(
    "",
    response_model=ValidateResponse,
    summary="Backtest a forecasting model",
    description=(
        "Cross-validate a model on historical data using sliding window evaluation. "
        "Computes MAE, RMSE, MAPE, sMAPE, and empirical prediction interval coverage "
        "for each window and as aggregate metrics."
    ),
    responses={
        422: {"description": "Series too short or invalid request"},
        429: {"description": "Rate limit or credit limit exceeded"},
    },
)
async def validate_model(
    payload: ValidateRequest,
    request: Request,
    plan: str = Depends(get_plan),
    _: None = Depends(verify_rapidapi_proxy),
) -> ValidateResponse:
    """Backtesting endpoint.

    Runs sliding-window cross-validation and returns per-window and aggregate metrics.

    Args:
        payload: Validated request body.
        request: FastAPI request (used to access redis from app.state).
        plan: Resolved subscription plan.

    Returns:
        ValidateResponse with backtest_metrics, windows, and meta.

    Raises:
        HTTPException 422: When the series is too short for the configuration.
    """
    redis_client: Any | None = getattr(request.app.state, "redis", None)

    try:
        return await run_backtest(payload, redis_client)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "code": "SERIES_TOO_SHORT",
                "message": str(exc),
                "details": {
                    "series_length": len(payload.series),
                    "horizon": payload.horizon,
                    "n_windows": payload.n_windows,
                    "min_required": payload.horizon * payload.n_windows * 2,
                },
            },
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "status": "error",
                "code": "NOT_IMPLEMENTED",
                "message": str(exc),
                "details": None,
            },
        ) from exc
