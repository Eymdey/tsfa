"""Pydantic schemas for the /v1/validate (backtesting) endpoint."""

from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.forecast import FrequencyLiteral, ModelLiteral
from app.schemas.common import Meta


class ValidateRequest(BaseModel):
    """Request body for POST /v1/validate (backtesting)."""

    series: list[float] = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Historical observations.",
    )
    timestamps: list[str] | None = Field(default=None)
    horizon: int = Field(..., ge=1, le=365)
    frequency: FrequencyLiteral = "auto"
    model: ModelLiteral = "auto"
    n_windows: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of cross-validation windows.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168],
                "horizon": 3,
                "frequency": "D",
                "model": "auto",
                "n_windows": 3,
            }
        }
    }


class BacktestWindow(BaseModel):
    """Metrics for a single backtesting window."""

    window: int = Field(..., ge=1)
    mae: float = Field(..., ge=0)
    rmse: float = Field(..., ge=0)
    mape: float = Field(..., ge=0)
    smape: float = Field(..., ge=0)


class BacktestMetrics(BaseModel):
    """Aggregate backtesting metrics across all windows."""

    mae: float = Field(..., ge=0, description="Mean Absolute Error.")
    rmse: float = Field(..., ge=0, description="Root Mean Squared Error.")
    mape: float = Field(..., ge=0, description="Mean Absolute Percentage Error.")
    smape: float = Field(..., ge=0, description="Symmetric MAPE.")
    coverage_80: float = Field(..., ge=0, le=1, description="Empirical 80% PI coverage.")
    coverage_95: float = Field(..., ge=0, le=1, description="Empirical 95% PI coverage.")


class ValidateResponse(BaseModel):
    """Response for POST /v1/validate."""

    status: str = "success"
    backtest_metrics: BacktestMetrics
    windows: list[BacktestWindow]
    meta: Meta
