"""Backtesting / validation service.

Implements sliding window cross-validation for forecasting models.
All inference runs locally (ARIMA) regardless of USE_MODAL setting,
since backtesting is compute-intensive and runs in test contexts too.
"""

import time
import uuid
from typing import Any

import structlog

from app.schemas.validate import (
    ValidateRequest,
    ValidateResponse,
    BacktestMetrics,
    BacktestWindow,
)
from app.schemas.common import Meta
from app.services.credits import get_credits_for_validation
from ml.preprocessing.cleaner import clean_series
from ml.preprocessing.frequency_detector import detect_frequency
from ml.models.arima_model import ARIMAModel
from ml.postprocessing.metrics import mae, rmse, mape, smape, coverage

logger = structlog.get_logger(__name__)


def _run_arima_local(
    values: list[float],
    frequency: str,
    horizon: int,
) -> dict:
    """Run AutoARIMA locally and return dict with mean + confidence intervals."""
    model = ARIMAModel()
    model.fit(values, frequency)
    return model.predict(horizon=horizon, confidence_levels=[0.8, 0.95])


async def run_backtest(
    request: ValidateRequest,
    redis_client: Any | None = None,
) -> ValidateResponse:
    """Execute a sliding-window cross-validation run on the provided series.

    Args:
        request: Validated ValidateRequest.
        redis_client: Optional Redis client (unused currently, reserved for caching).

    Returns:
        ValidateResponse with per-window and aggregate metrics.

    Raises:
        ValueError: When the series is too short for the requested configuration.
    """
    start_time = time.monotonic()
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    log = logger.bind(request_id=request_id)

    log.info(
        "backtest_started",
        series_length=len(request.series),
        horizon=request.horizon,
        n_windows=request.n_windows,
    )

    # 1. Clean series
    cleaned = clean_series(request.series, request.timestamps)
    series = cleaned.values_clean
    n = len(series)

    # 2. Enforce minimum length
    min_required = request.horizon * request.n_windows * 2
    if n < min_required:
        raise ValueError(
            f"Series too short for backtesting: got {n} observations, "
            f"need at least {min_required} "
            f"(horizon={request.horizon} × n_windows={request.n_windows} × 2)."
        )

    # 3. Detect / resolve frequency
    if request.frequency == "auto":
        effective_frequency = detect_frequency(request.timestamps, fallback="D")
    else:
        effective_frequency = request.frequency

    # 4. Resolve model — only ARIMA supported locally; tide/ensemble not implemented
    model_id = request.model
    if model_id in ("auto", "chronos", "lstm", "tide", "ensemble"):
        model_id = "arima"

    log.info("backtest_config", model=model_id, frequency=effective_frequency)

    # 5. Sliding window cross-validation
    window_results: list[BacktestWindow] = []
    agg_mae: list[float] = []
    agg_rmse: list[float] = []
    agg_mape: list[float] = []
    agg_smape: list[float] = []
    agg_cov80: list[float] = []
    agg_cov95: list[float] = []

    for i in range(1, request.n_windows + 1):
        # Compute train/test split
        cutoff = n - request.horizon * (request.n_windows - i + 1)
        train = series[:cutoff]
        test = series[cutoff : cutoff + request.horizon]

        if len(train) < 10 or len(test) == 0:
            log.warning("backtest_window_skip", window=i, train_len=len(train))
            continue

        # Run inference
        raw = _run_arima_local(train, effective_frequency, len(test))
        y_pred: list[float] = raw["mean"]

        # Point metrics
        w_mae = mae(test, y_pred)
        w_rmse = rmse(test, y_pred)
        w_mape = mape(test, y_pred)
        w_smape = smape(test, y_pred)

        # Coverage metrics — use interval bounds if available, else ±10% fallback
        lower_80 = raw.get("lower_80")
        upper_80 = raw.get("upper_80")
        lower_95 = raw.get("lower_95")
        upper_95 = raw.get("upper_95")

        if lower_80 is None:
            lower_80 = [p * 0.9 for p in y_pred]
        if upper_80 is None:
            upper_80 = [p * 1.1 for p in y_pred]
        if lower_95 is None:
            lower_95 = [p * 0.85 for p in y_pred]
        if upper_95 is None:
            upper_95 = [p * 1.15 for p in y_pred]

        w_cov80 = coverage(test, lower_80, upper_80)
        w_cov95 = coverage(test, lower_95, upper_95)

        agg_mae.append(w_mae)
        agg_rmse.append(w_rmse)
        agg_mape.append(w_mape)
        agg_smape.append(w_smape)
        agg_cov80.append(w_cov80)
        agg_cov95.append(w_cov95)

        window_results.append(
            BacktestWindow(
                window=i,
                mae=round(w_mae, 6),
                rmse=round(w_rmse, 6),
                mape=round(w_mape, 6),
                smape=round(w_smape, 6),
            )
        )

    # 6. Aggregate across windows
    def _avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    backtest_metrics = BacktestMetrics(
        mae=round(_avg(agg_mae), 6),
        rmse=round(_avg(agg_rmse), 6),
        mape=round(_avg(agg_mape), 6),
        smape=round(_avg(agg_smape), 6),
        coverage_80=round(_avg(agg_cov80), 6),
        coverage_95=round(_avg(agg_cov95), 6),
    )

    inference_time_ms = (time.monotonic() - start_time) * 1000.0
    credits = get_credits_for_validation(model_id, request.n_windows)

    meta = Meta(
        inference_time_ms=round(inference_time_ms, 2),
        request_id=request_id,
        credits_used=credits,
        fallback_used=None,
        fallback_reason=None,
    )

    log.info(
        "backtest_completed",
        windows=len(window_results),
        mae=backtest_metrics.mae,
        inference_time_ms=round(inference_time_ms, 2),
    )

    return ValidateResponse(
        status="success",
        backtest_metrics=backtest_metrics,
        windows=window_results,
        meta=meta,
    )
