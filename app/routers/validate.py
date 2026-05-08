"""Validate router — /v1/validate endpoint.

Backtesting / cross-validation of forecasting models.
Full implementation planned for Phase 1 Week 3.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import get_plan
from app.schemas.validate import ValidateRequest

router = APIRouter(prefix="/validate", tags=["Validate"])


@router.post(
    "",
    summary="Backtest a forecasting model (Phase 1 Week 3)",
    description=(
        "Cross-validate a model on historical data and compute MAE, RMSE, MAPE, SMAPE, "
        "and empirical prediction interval coverage. Coming in Phase 1 Week 3."
    ),
    responses={
        501: {"description": "Not implemented yet"},
    },
    status_code=501,
)
async def validate_model(
    payload: ValidateRequest,
    plan: str = Depends(get_plan),
) -> JSONResponse:
    """Backtesting endpoint stub.

    Args:
        payload: Validated request body.
        plan: Resolved subscription plan.

    Returns:
        501 JSON response indicating the feature is coming soon.
    """
    return JSONResponse(
        status_code=501,
        content={
            "status": "error",
            "code": "NOT_IMPLEMENTED",
            "message": (
                "Backtesting (/v1/validate) is not yet implemented. "
                "Coming in Phase 1 Week 3."
            ),
            "details": None,
        },
    )
