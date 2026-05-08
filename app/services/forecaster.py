"""Forecast orchestration service.

Coordinates preprocessing, model selection, caching, inference,
postprocessing, and response assembly for univariate forecasts.
"""

import hashlib
import json
import time
import uuid
from typing import Any

import structlog

from app.config import settings
from app.schemas.forecast import UnivariateForecastRequest, ForecastResponse, ForecastResult, Diagnostics
from app.schemas.common import Meta
from app.services.model_selector import select_model
from app.services.credits import get_credits_for_model
from ml.preprocessing.cleaner import clean_series
from ml.preprocessing.frequency_detector import detect_frequency
from ml.postprocessing.diagnostics import compute_diagnostics
from ml.models.arima_model import ARIMAModel

logger = structlog.get_logger(__name__)


async def run_univariate_forecast(
    request: UnivariateForecastRequest,
    redis_client: Any | None,
) -> ForecastResponse:
    """Orchestrate a univariate forecast end-to-end.

    Pipeline:
    1. Clean and validate the input series.
    2. Detect (or use provided) frequency.
    3. Select the best model (auto-selection or explicit).
    4. Check Redis cache for an identical request.
    5. Run model inference if cache miss.
    6. Compute diagnostics.
    7. Store result in cache.
    8. Assemble and return ForecastResponse.

    Args:
        request: Validated UnivariateForecastRequest.
        redis_client: Optional Redis client for caching.

    Returns:
        A complete ForecastResponse.

    Raises:
        ValueError: On data quality issues that cannot be recovered.
    """
    start_time = time.monotonic()
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    log = logger.bind(request_id=request_id)
    log.info("forecast_started", series_length=len(request.series), horizon=request.horizon)

    # 1. Clean series
    cleaned = clean_series(request.series, request.timestamps)
    if cleaned.warnings:
        for warning in cleaned.warnings:
            log.warning("data_quality_warning", message=warning)

    # 2. Detect frequency
    effective_frequency: str
    if request.frequency == "auto":
        effective_frequency = detect_frequency(request.timestamps, fallback="D")
        log.info("frequency_detected", frequency=effective_frequency)
    else:
        effective_frequency = request.frequency

    # 3. Select model
    requested_model = request.model
    if requested_model == "auto":
        has_seasonality = len(cleaned.values_clean) >= 14  # heuristic for auto-detection
        model_name = select_model(
            series_length=len(cleaned.values_clean),
            horizon=request.horizon,
            has_covariates=False,
            has_seasonality=has_seasonality,
            frequency=effective_frequency,
        )
    else:
        # Explicit model requested — still force arima in Phase 1 if not arima
        if requested_model != "arima":
            log.warning(
                "phase1_explicit_model_override",
                requested=requested_model,
                forced="arima",
                reason="Only AutoARIMA is implemented in Phase 1.",
            )
        model_name = "arima"

    # 4. Cache lookup
    cache_key = _build_cache_key(request)
    if redis_client is not None:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                log.info("cache_hit", cache_key=cache_key)
                response_data = json.loads(cached)
                # Update request_id and keep fresh inference time from cache marker
                response_data["meta"]["request_id"] = request_id
                return ForecastResponse(**response_data)
        except Exception as exc:
            log.warning("cache_read_error", error=str(exc))

    # 5. Run inference
    log.info("inference_started", model=model_name)
    model = ARIMAModel()
    model.fit(cleaned.values_clean, effective_frequency)
    raw_result = model.predict(
        horizon=request.horizon,
        confidence_levels=request.confidence_levels,
    )

    # 6. Compute diagnostics
    diagnostics_result = compute_diagnostics(
        series=cleaned.values_clean,
        frequency=effective_frequency,
        missing_values=cleaned.missing_count,
    )

    # 7. Build forecast timestamps
    forecast_timestamps = _build_forecast_timestamps(
        request.timestamps,
        cleaned.values_clean,
        effective_frequency,
        request.horizon,
    )

    # Measure total time
    inference_time_ms = (time.monotonic() - start_time) * 1000.0

    # Assemble response
    credits = get_credits_for_model(model_name)

    def _to_list(arr: Any) -> list[float] | None:
        """Convert numpy array to Python list, or return None."""
        if arr is None:
            return None
        if hasattr(arr, "tolist"):
            return arr.tolist()
        return arr

    forecast_result = ForecastResult(
        timestamps=forecast_timestamps,
        mean=_to_list(raw_result["mean"]),
        lower_80=_to_list(raw_result.get("lower_80")),
        upper_80=_to_list(raw_result.get("upper_80")),
        lower_95=_to_list(raw_result.get("lower_95")),
        upper_95=_to_list(raw_result.get("upper_95")),
    )

    diagnostics = Diagnostics(
        trend=diagnostics_result.trend,
        seasonality_detected=diagnostics_result.seasonality_detected,
        seasonality_period=diagnostics_result.seasonality_period,
        series_length=diagnostics_result.series_length,
        missing_values=diagnostics_result.missing_values,
        stationarity=diagnostics_result.stationarity,
    )

    meta = Meta(
        inference_time_ms=round(inference_time_ms, 2),
        request_id=request_id,
        credits_used=credits,
    )

    response = ForecastResponse(
        status="success",
        model_used=model_name,
        forecast=forecast_result,
        diagnostics=diagnostics,
        meta=meta,
    )

    # 8. Store in cache
    if redis_client is not None:
        try:
            response_json = response.model_dump_json()
            await redis_client.set(cache_key, response_json, ex=settings.cache_ttl_seconds)
            log.info("cache_stored", cache_key=cache_key, ttl=settings.cache_ttl_seconds)
        except Exception as exc:
            log.warning("cache_write_error", error=str(exc))

    log.info(
        "forecast_completed",
        model=model_name,
        inference_time_ms=round(inference_time_ms, 2),
        credits=credits,
    )

    return response


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_cache_key(request: UnivariateForecastRequest) -> str:
    """Build a deterministic SHA-256 cache key from the request payload.

    Args:
        request: The forecast request.

    Returns:
        Hex digest string prefixed with 'tsfa:forecast:'.
    """
    payload = {
        "series": request.series,
        "horizon": request.horizon,
        "frequency": request.frequency,
        "model": request.model,
        "confidence_levels": sorted(request.confidence_levels),
        "seasonality": str(request.seasonality),
    }
    serialised = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(serialised.encode()).hexdigest()
    return f"tsfa:forecast:{digest}"


def _build_forecast_timestamps(
    input_timestamps: list[str] | None,
    values: list[float],
    frequency: str,
    horizon: int,
) -> list[str]:
    """Generate ISO 8601 forecast timestamps starting after the last observation.

    Args:
        input_timestamps: Original timestamps from the request (may be None).
        values: Cleaned series values (used to determine count when no timestamps).
        frequency: Resolved frequency string.
        horizon: Number of steps to forecast.

    Returns:
        List of ISO 8601 date strings of length *horizon*.
    """
    try:
        import pandas as pd
        from ml.models.arima_model import FREQ_MAP

        sf_freq = FREQ_MAP.get(frequency, "D")

        if input_timestamps and len(input_timestamps) > 0:
            last_ts = pd.Timestamp(input_timestamps[-1])
        else:
            n = len(values)
            last_ts = pd.date_range(start="2024-01-01", periods=n, freq=sf_freq)[-1]

        future_dates = pd.date_range(start=last_ts, periods=horizon + 1, freq=sf_freq)[1:]
        return [str(d.date()) for d in future_dates]

    except Exception:
        # Graceful fallback: return empty list
        return []
