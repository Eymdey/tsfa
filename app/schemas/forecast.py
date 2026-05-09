"""Pydantic schemas for forecast endpoints.

Covers univariate, multivariate, and batch forecast request/response models.
"""

from typing import Literal, Union
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Meta


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

FrequencyLiteral = Literal["T", "H", "D", "W", "M", "Q", "Y", "auto"]
ModelLiteral = Literal["auto", "chronos", "lstm", "tide", "arima", "ensemble"]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class UnivariateForecastRequest(BaseModel):
    """Request body for POST /v1/forecast/univariate."""

    series: list[float] = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Historical observations (min 10, max 50 000).",
        examples=[[120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175]],
    )
    timestamps: list[str] | None = Field(
        default=None,
        description="ISO 8601 timestamps aligned with `series`. Optional.",
        examples=[["2024-01-01", "2024-01-02"]],
    )
    horizon: int = Field(
        ...,
        ge=1,
        le=365,
        description="Number of future steps to forecast (1–365).",
        examples=[7],
    )
    frequency: FrequencyLiteral = Field(
        default="auto",
        description="Time series frequency. Use 'auto' to infer from timestamps.",
        examples=["D"],
    )
    model: ModelLiteral = Field(
        default="auto",
        description="Forecasting model to use. 'auto' triggers automatic selection.",
        examples=["auto"],
    )
    confidence_levels: list[float] = Field(
        default=[0.8, 0.95],
        description="Confidence interval levels (0–1).",
        examples=[[0.8, 0.95]],
    )
    seasonality: Union[str, int] = Field(
        default="auto",
        description="Seasonality period override. 'auto' for automatic detection.",
        examples=["auto"],
    )

    @field_validator("series")
    @classmethod
    def validate_series_finite(cls, v: list[float]) -> list[float]:
        """Ensure no NaN or infinite values are present in the series."""
        import math

        for i, val in enumerate(v):
            if not math.isfinite(val):
                raise ValueError(
                    f"series[{i}] contains a non-finite value ({val}). "
                    "Remove NaN and infinite values before sending."
                )
        return v

    @field_validator("confidence_levels")
    @classmethod
    def validate_confidence_levels(cls, v: list[float]) -> list[float]:
        """Ensure confidence levels are strictly between 0 and 1."""
        for level in v:
            if not (0.0 < level < 1.0):
                raise ValueError(
                    f"confidence_levels must be in (0, 1). Got {level}."
                )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
                "horizon": 7,
                "frequency": "D",
                "model": "auto",
                "confidence_levels": [0.8, 0.95],
                "seasonality": "auto",
            }
        }
    }


class CovariateInput(BaseModel):
    """A single covariate series for multivariate forecasting."""

    name: str = Field(..., description="Covariate name / label.")
    values: list[float] = Field(..., min_length=1)
    future_values: list[float] | None = Field(
        default=None,
        description="Future known values aligned with the forecast horizon.",
    )
    is_future_known: bool = Field(
        default=False,
        description="Whether this covariate is available during the forecast horizon.",
    )


class TargetInput(BaseModel):
    """Target time series for multivariate forecasting."""

    name: str
    values: list[float] = Field(..., min_length=10, max_length=50000)
    timestamps: list[str] | None = None


class MultivariateForecastRequest(BaseModel):
    """Request body for POST /v1/forecast/multivariate."""

    target: TargetInput
    covariates: list[CovariateInput] = Field(..., min_length=1, max_length=20)
    horizon: int = Field(..., ge=1, le=365)
    frequency: FrequencyLiteral = "auto"
    model: ModelLiteral = "auto"
    confidence_levels: list[float] = [0.8, 0.95]

    model_config = {
        "json_schema_extra": {
            "example": {
                "target": {
                    "name": "sales",
                    "values": [120.5, 132.1, 128.7, 145.0, 139.3, 152.8, 148.2,
                               160.0, 155.5, 168.0],
                    "timestamps": None,
                },
                "covariates": [
                    {
                        "name": "temperature",
                        "values": [18.2, 22.1, 19.5, 25.3, 20.1, 21.0, 23.2,
                                   24.5, 19.8, 22.3],
                        "is_future_known": False,
                    }
                ],
                "horizon": 7,
                "frequency": "D",
                "model": "auto",
            }
        }
    }


class BatchSeriesItem(BaseModel):
    """One series entry in a batch forecast request."""

    id: str = Field(..., description="Unique identifier for this series.")
    values: list[float] = Field(..., min_length=10, max_length=50000)
    horizon: int = Field(..., ge=1, le=365)
    timestamps: list[str] | None = None


class BatchForecastRequest(BaseModel):
    """Request body for POST /v1/forecast/batch."""

    series_list: list[BatchSeriesItem] = Field(..., min_length=1, max_length=500)
    frequency: FrequencyLiteral = "auto"
    model: ModelLiteral = "auto"
    confidence_levels: list[float] = [0.8, 0.95]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class BatchSeriesResult(BaseModel):
    """Result for a single series in a batch forecast request."""

    id: str = Field(..., description="Series identifier from the request.")
    status: Literal["success", "error"] = Field(...)
    forecast: "ForecastResult | None" = Field(default=None)
    model_used: str | None = Field(default=None)
    meta: Meta | None = Field(default=None)
    error: str | None = Field(default=None)


class BatchForecastResponse(BaseModel):
    """Response for POST /v1/forecast/batch."""

    status: str = Field(default="success")
    results: list[BatchSeriesResult]
    total_credits_used: int = Field(..., ge=0)
    processing_time_ms: float = Field(..., ge=0)


class ForecastResult(BaseModel):
    """The forecast values and associated confidence intervals."""

    timestamps: list[str] = Field(
        default_factory=list,
        description="ISO 8601 forecast timestamps.",
    )
    mean: list[float] = Field(..., description="Point forecast (mean).")
    lower_80: list[float] | None = Field(default=None, description="80% lower bound.")
    upper_80: list[float] | None = Field(default=None, description="80% upper bound.")
    lower_95: list[float] | None = Field(default=None, description="95% lower bound.")
    upper_95: list[float] | None = Field(default=None, description="95% upper bound.")


class Diagnostics(BaseModel):
    """Series diagnostics computed before inference."""

    trend: Literal["upward", "downward", "stable"] = Field(
        ..., description="Dominant linear trend direction."
    )
    seasonality_detected: bool = Field(
        ..., description="Whether a significant seasonal pattern was found."
    )
    seasonality_period: int | None = Field(
        default=None, description="Dominant seasonal period (in observations)."
    )
    series_length: int = Field(..., ge=1)
    missing_values: int = Field(..., ge=0)
    stationarity: Literal["stationary", "non_stationary"] = Field(
        ..., description="ADF test result."
    )


class ForecastResponse(BaseModel):
    """Full response for a successful univariate forecast."""

    status: str = Field(default="success")
    model_used: str = Field(..., examples=["arima"])
    forecast: ForecastResult
    diagnostics: Diagnostics
    meta: Meta

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "model_used": "arima",
                "forecast": {
                    "timestamps": ["2024-01-13", "2024-01-14", "2024-01-15"],
                    "mean": [178.2, 181.5, 184.8],
                    "lower_80": [171.0, 173.5, 176.0],
                    "upper_80": [185.4, 189.5, 193.6],
                    "lower_95": [164.5, 166.8, 169.2],
                    "upper_95": [191.9, 196.2, 200.4],
                },
                "diagnostics": {
                    "trend": "upward",
                    "seasonality_detected": False,
                    "seasonality_period": None,
                    "series_length": 12,
                    "missing_values": 0,
                    "stationarity": "non_stationary",
                },
                "meta": {
                    "inference_time_ms": 234.0,
                    "request_id": "req_abc123",
                    "credits_used": 1,
                },
            }
        }
    }


# Resolve forward references now that all models are defined
BatchSeriesResult.model_rebuild()
BatchForecastResponse.model_rebuild()
