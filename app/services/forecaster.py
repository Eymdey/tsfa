"""Forecast orchestration service.

Coordinates preprocessing, model selection, caching, inference,
postprocessing, and response assembly for univariate forecasts.

Phase 2 dispatch logic:
- USE_MODAL=false  → all models fall back to ARIMA locally (dev/CI)
- USE_MODAL=true   → chronos/lstm dispatched to Modal.com GPU workers
  - ModalConnectionError → caught here, ARIMA fallback (meta.fallback_used=True)
  - ModalTimeoutError    → propagates to error handler (HTTP 503)
"""

import hashlib
import json
import time
import uuid
from typing import Any

import structlog

from app.config import settings
from app.middleware.error_handler import ModalConnectionError, ModalTimeoutError
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
    5. Run model inference (local or Modal dispatch).
    6. Compute diagnostics.
    7. Store result in cache.
    8. Assemble and return ForecastResponse.

    Args:
        request: Validated UnivariateForecastRequest.
        redis_client: Optional Redis client for caching.

    Returns:
        A complete ForecastResponse.

    Raises:
        NotImplementedError: When tide or ensemble model is requested.
        ModalTimeoutError: When Modal inference exceeds its timeout.
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
    model_id, selection_reason = select_model(
        series_length=len(cleaned.values_clean),
        horizon=request.horizon,
        has_covariates=False,
        frequency=effective_frequency,
        requested_model=request.model,
    )
    log.info("model_selected", model=model_id, reason=selection_reason)

    # Handle Phase 3 stubs immediately (before cache lookup)
    if model_id == "tide":
        raise NotImplementedError("TiDE model is available in Phase 3.")
    if model_id == "ensemble":
        raise NotImplementedError("Ensemble model is available in Phase 3.")

    # 4. Cache lookup
    cache_key = _build_cache_key(request)
    if redis_client is not None:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                log.info("cache_hit", cache_key=cache_key)
                response_data = json.loads(cached)
                response_data["meta"]["request_id"] = request_id
                return ForecastResponse(**response_data)
        except Exception as exc:
            log.warning("cache_read_error", error=str(exc))

    # 5. Run inference
    log.info("inference_started", model=model_id, use_modal=settings.use_modal)

    fallback_used: bool | None = None
    fallback_reason_str: str | None = None
    actual_model = model_id

    if model_id == "arima":
        raw_result = _run_arima_local(
            cleaned.values_clean, effective_frequency,
            request.horizon, request.confidence_levels,
        )

    elif model_id == "chronos":
        if settings.use_modal:
            try:
                raw_result = await _dispatch_chronos(
                    cleaned.values_clean, effective_frequency,
                    request.horizon, request.confidence_levels,
                )
                raw_result = _convert_chronos_result(raw_result)
            except (ModalConnectionError, Exception) as exc:
                # Catch ModalConnectionError (custom) and modal.exception.ExecutionError
                # (raised when Modal app is not running in CI/test environments).
                # Re-raise ModalTimeoutError so the global handler returns HTTP 503.
                from app.middleware.error_handler import ModalTimeoutError as _MTE
                if isinstance(exc, _MTE):
                    raise
                log.warning("modal_connection_fallback", model="chronos", error=str(exc))
                raw_result = _run_arima_local(
                    cleaned.values_clean, effective_frequency,
                    request.horizon, request.confidence_levels,
                )
                actual_model = "arima"
                fallback_used = True
                fallback_reason_str = "modal_unavailable"
        else:
            log.info("modal_disabled_fallback", requested="chronos", fallback="arima")
            raw_result = _run_arima_local(
                cleaned.values_clean, effective_frequency,
                request.horizon, request.confidence_levels,
            )
            actual_model = "arima"
            fallback_used = True
            fallback_reason_str = "modal_unavailable"

    elif model_id == "lstm":
        if settings.use_modal:
            try:
                raw_result = await _dispatch_lstm(
                    cleaned.values_clean, effective_frequency,
                    request.horizon, request.confidence_levels,
                )
            except (ModalConnectionError, Exception) as exc:
                # Catch ModalConnectionError (custom) and modal.exception.ExecutionError
                # (raised when Modal app is not running in CI/test environments).
                # Re-raise ModalTimeoutError so the global handler returns HTTP 503.
                from app.middleware.error_handler import ModalTimeoutError as _MTE
                if isinstance(exc, _MTE):
                    raise
                log.warning("modal_connection_fallback", model="lstm", error=str(exc))
                raw_result = _run_arima_local(
                    cleaned.values_clean, effective_frequency,
                    request.horizon, request.confidence_levels,
                )
                actual_model = "arima"
                fallback_used = True
                fallback_reason_str = "modal_unavailable"
        else:
            log.info("modal_disabled_fallback", requested="lstm", fallback="arima")
            raw_result = _run_arima_local(
                cleaned.values_clean, effective_frequency,
                request.horizon, request.confidence_levels,
            )
            actual_model = "arima"
            fallback_used = True
            fallback_reason_str = "modal_unavailable"

    else:
        # Unknown model — safe fallback
        log.warning("unknown_model_fallback", model=model_id, fallback="arima")
        raw_result = _run_arima_local(
            cleaned.values_clean, effective_frequency,
            request.horizon, request.confidence_levels,
        )
        actual_model = "arima"
        fallback_used = True
        fallback_reason_str = "unknown_model"

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
    credits = get_credits_for_model(actual_model)

    def _to_list(arr: Any) -> list[float] | None:
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
        fallback_used=fallback_used,
        fallback_reason=fallback_reason_str,
    )

    response = ForecastResponse(
        status="success",
        model_used=actual_model,
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
        model=actual_model,
        selected_model=model_id,
        fallback_used=fallback_used,
        inference_time_ms=round(inference_time_ms, 2),
        credits=credits,
    )

    return response


# ---------------------------------------------------------------------------
# Local inference helpers
# ---------------------------------------------------------------------------


def _run_arima_local(
    values: list[float],
    frequency: str,
    horizon: int,
    confidence_levels: list[float],
) -> dict:
    """Run AutoARIMA inference locally via statsforecast.

    Args:
        values: Cleaned series values.
        frequency: Resolved frequency string.
        horizon: Number of steps to forecast.
        confidence_levels: Confidence interval levels.

    Returns:
        Dict with mean, lower_80, upper_80, lower_95, upper_95.
    """
    model = ARIMAModel()
    model.fit(values, frequency)
    return model.predict(horizon=horizon, confidence_levels=confidence_levels)


# ---------------------------------------------------------------------------
# Modal dispatch helpers
# ---------------------------------------------------------------------------


async def _dispatch_chronos(
    values: list[float],
    frequency: str,
    horizon: int,
    confidence_levels: list[float],
) -> dict:
    """Dispatch Chronos inference to Modal.com GPU worker.

    Args:
        values: Cleaned series values.
        frequency: Resolved frequency string (unused by Chronos but forwarded).
        horizon: Number of steps to forecast.
        confidence_levels: Confidence interval levels.

    Returns:
        Raw Chronos result dict with mean and quantiles.

    Raises:
        ModalTimeoutError: If the Modal call exceeds its timeout.
        ModalConnectionError: If the Modal backend is unreachable.
    """
    from ml.modal_app import ChronosWorker

    payload = {
        "series": values,
        "horizon": horizon,
        "confidence_levels": confidence_levels,
        "num_samples": 20,
    }
    return await ChronosWorker().predict.remote(payload)


async def _dispatch_lstm(
    values: list[float],
    frequency: str,
    horizon: int,
    confidence_levels: list[float],
) -> dict:
    """Dispatch LSTM inference to Modal.com GPU worker.

    Args:
        values: Cleaned series values.
        frequency: Resolved frequency string.
        horizon: Number of steps to forecast.
        confidence_levels: Confidence interval levels.

    Returns:
        Raw LSTM result dict with mean, lower_80, upper_80, lower_95, upper_95.

    Raises:
        ModalTimeoutError: If the Modal call exceeds its timeout.
        ModalConnectionError: If the Modal backend is unreachable.
    """
    from ml.modal_app import run_lstm

    payload = {
        "series": values,
        "horizon": horizon,
        "frequency": frequency,
        "confidence_levels": confidence_levels,
    }
    return await run_lstm.remote(payload)


# ---------------------------------------------------------------------------
# Result conversion helpers
# ---------------------------------------------------------------------------


def _convert_chronos_result(raw: dict) -> dict:
    """Convert Chronos quantile format to the standard lower_N/upper_N format.

    Chronos returns:
        {"mean": [...], "quantiles": {"0.1": [...], "0.9": [...], ...}}

    Standard format expected by ForecastResult:
        {"mean": [...], "lower_80": [...], "upper_80": [...], ...}

    Args:
        raw: Raw Chronos result dict.

    Returns:
        Dict in standard forecast format.
    """
    quantiles = raw.get("quantiles", {})
    result: dict = {"mean": raw["mean"]}

    # Map well-known quantile pairs to named interval fields
    _QUANTILE_MAP: dict[tuple[str, str], tuple[str, str]] = {
        ("0.1", "0.9"): ("lower_80", "upper_80"),
        ("0.025", "0.975"): ("lower_95", "upper_95"),
        ("0.05", "0.95"): ("lower_90", "upper_90"),
    }
    for (lo_key, hi_key), (lo_field, hi_field) in _QUANTILE_MAP.items():
        if lo_key in quantiles:
            result[lo_field] = quantiles[lo_key]
        if hi_key in quantiles:
            result[hi_field] = quantiles[hi_key]

    return result


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
        return []
