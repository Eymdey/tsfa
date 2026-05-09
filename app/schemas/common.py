"""Common Pydantic schemas shared across all endpoints.

Includes error responses, usage metadata, and model info structures.
"""

from typing import Any
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response body returned on all non-2xx responses."""

    status: str = Field(default="error", examples=["error"])
    code: str = Field(
        ...,
        description="Machine-readable error code.",
        examples=["SERIES_TOO_SHORT"],
    )
    message: str = Field(
        ...,
        description="Human-readable error description.",
        examples=["Series must have at least 10 observations."],
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional context about the error.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "code": "SERIES_TOO_SHORT",
                "message": "Series must have at least 10 observations.",
                "details": None,
            }
        }
    }


class UsageResponse(BaseModel):
    """Credits and usage information for the caller's current plan period."""

    plan: str = Field(..., examples=["pro"])
    period: str = Field(..., description="YYYY-MM format.", examples=["2026-05"])
    credits_used: int = Field(..., ge=0, examples=[1247])
    credits_limit: int = Field(..., ge=0, examples=[50000])
    credits_remaining: int = Field(..., ge=0, examples=[48753])
    reset_date: str = Field(..., description="ISO 8601 date.", examples=["2026-06-01"])
    requests_count: int = Field(..., ge=0, examples=[342])

    model_config = {
        "json_schema_extra": {
            "example": {
                "plan": "pro",
                "period": "2026-05",
                "credits_used": 1247,
                "credits_limit": 50000,
                "credits_remaining": 48753,
                "reset_date": "2026-06-01",
                "requests_count": 342,
            }
        }
    }


class ModelInfo(BaseModel):
    """Description of a single forecasting model exposed by the API."""

    id: str = Field(..., examples=["arima"])
    name: str = Field(..., examples=["AutoARIMA"])
    type: str = Field(..., examples=["statistical"])
    best_for: list[str] = Field(default_factory=list)
    min_series_length: int = Field(..., ge=1, examples=[10])
    max_horizon: int = Field(..., ge=1, examples=[180])
    avg_inference_ms: int = Field(..., ge=0, examples=[80])
    credits_per_call: int = Field(..., ge=1, examples=[1])
    available: bool = Field(default=True, description="Whether the model is operational.")
    backend: str | None = Field(default=None, description="Execution backend: 'local' or 'modal'.")
    coming: str | None = Field(default=None, description="Release phase if not yet available.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "arima",
                "name": "AutoARIMA",
                "type": "statistical",
                "best_for": ["short series", "stationary", "interpretability"],
                "min_series_length": 10,
                "max_horizon": 180,
                "avg_inference_ms": 80,
                "credits_per_call": 1,
                "available": True,
                "backend": "local",
                "coming": None,
            }
        }
    }


class Meta(BaseModel):
    """Request metadata appended to every successful response."""

    inference_time_ms: float = Field(..., ge=0, examples=[234.0])
    request_id: str = Field(..., examples=["req_abc123"])
    credits_used: int = Field(..., ge=0, examples=[1])
    fallback_used: bool | None = Field(default=None, description="True if a fallback model was used.")
    fallback_reason: str | None = Field(default=None, description="Reason the fallback was triggered.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "inference_time_ms": 234.0,
                "request_id": "req_abc123",
                "credits_used": 1,
                "fallback_used": None,
                "fallback_reason": None,
            }
        }
    }
