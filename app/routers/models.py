"""Models router — GET /v1/models endpoint.

Returns the static catalogue of forecasting models, their characteristics,
and availability status. Phase 2: AutoARIMA, Chronos, and LSTM are available.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.common import ModelInfo

router = APIRouter(prefix="/models", tags=["Models"])


class ModelsResponse(BaseModel):
    """Response body for GET /v1/models."""

    models: list[ModelInfo]


# Static model catalogue — kept in sync with spec section 2.5
_MODEL_CATALOGUE: list[ModelInfo] = [
    ModelInfo(
        id="arima",
        name="AutoARIMA",
        type="statistical",
        best_for=["short series", "stationary", "interpretability"],
        min_series_length=10,
        max_horizon=180,
        avg_inference_ms=80,
        credits_per_call=1,
        available=True,
        backend="local",
    ),
    ModelInfo(
        id="chronos",
        name="Chronos-T5 (Small)",
        type="foundation_model",
        best_for=["univariate", "zero-shot", "general purpose"],
        min_series_length=12,
        max_horizon=365,
        avg_inference_ms=250,
        credits_per_call=1,
        available=True,
        backend="modal",
    ),
    ModelInfo(
        id="lstm",
        name="LSTM Custom (fine-tuned)",
        type="deep_learning",
        best_for=["noisy series", "non-linear patterns", "long horizons"],
        min_series_length=30,
        max_horizon=90,
        avg_inference_ms=320,
        credits_per_call=2,
        available=True,
        backend="modal",
    ),
    ModelInfo(
        id="tide",
        name="TiDE",
        type="deep_learning",
        best_for=["multivariate", "long horizon", "many covariates"],
        min_series_length=50,
        max_horizon=365,
        avg_inference_ms=400,
        credits_per_call=3,
        available=False,
        backend="modal",
        coming="phase_3",
    ),
    ModelInfo(
        id="ensemble",
        name="Ensemble (Chronos + LSTM + ARIMA)",
        type="ensemble",
        best_for=["highest accuracy", "production use"],
        min_series_length=30,
        max_horizon=180,
        avg_inference_ms=650,
        credits_per_call=5,
        available=False,
        backend="modal",
        coming="phase_3",
    ),
]


@router.get(
    "",
    response_model=ModelsResponse,
    summary="List available forecasting models",
    description=(
        "Returns all models in the catalogue with their specifications and "
        "current availability status. AutoARIMA, Chronos, and LSTM are available."
    ),
    responses={
        503: {"description": "Service temporarily unavailable"},
    },
)
async def list_models() -> ModelsResponse:
    """Return the static model catalogue.

    Returns:
        ModelsResponse containing all model descriptors.
    """
    return ModelsResponse(models=_MODEL_CATALOGUE)
