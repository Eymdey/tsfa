"""Model selection logic for the 'auto' model mode.

Implements the selection rules defined in the project specifications (section 6).
Returns a (model_id, reason) tuple so callers can log/expose the selection rationale.
"""

import structlog

logger = structlog.get_logger(__name__)


def select_model(
    series_length: int,
    horizon: int,
    has_covariates: bool,
    frequency: str,
    requested_model: str = "auto",
) -> tuple[str, str]:
    """Select the most appropriate model based on series characteristics.

    Priority rules (evaluated in order):
    1. requested_model != "auto"  → return the requested model directly
    2. series_length < 12         → "arima"   (Chronos requires >= 12 obs)
    3. series_length < 30         → "arima"   (LSTM requires >= 30 obs)
    4. has_covariates             → "tide"    (Phase 3; returns 501 in forecaster)
    5. series_length >= 100 and horizon <= 90 → "chronos"
    6. horizon > 90 and series_length >= 50   → "lstm"
    7. default                    → "chronos"

    Args:
        series_length: Number of observations in the cleaned series.
        horizon: Number of steps to forecast.
        has_covariates: Whether covariate features are present.
        frequency: Resolved frequency string (e.g. 'D', 'H').
        requested_model: Explicit model name or "auto".

    Returns:
        (model_id, reason) tuple where reason is a short string explaining the choice.
    """
    # Rule 1 — explicit model request
    if requested_model != "auto":
        logger.info(
            "model_selection",
            model=requested_model,
            reason="explicit_request",
            series_length=series_length,
            horizon=horizon,
        )
        return requested_model, "explicit_request"

    # Rule 2 — too short for Chronos
    if series_length < 12:
        _log("arima", "series_too_short_for_chronos", series_length, horizon)
        return "arima", "series_too_short_for_chronos"

    # Rule 3 — too short for LSTM
    if series_length < 30:
        _log("arima", "series_too_short_for_lstm", series_length, horizon)
        return "arima", "series_too_short_for_lstm"

    # Rule 4 — covariates present → TiDE (Phase 3 stub)
    if has_covariates:
        _log("tide", "covariates_present", series_length, horizon)
        return "tide", "covariates_present"

    # Rule 5 — long series + short horizon → Chronos (zero-shot foundation model)
    if series_length >= 100 and horizon <= 90:
        _log("chronos", "long_series_short_horizon", series_length, horizon)
        return "chronos", "long_series_short_horizon"

    # Rule 6 — long horizon → LSTM
    if horizon > 90 and series_length >= 50:
        _log("lstm", "long_horizon", series_length, horizon)
        return "lstm", "long_horizon"

    # Rule 7 — default
    _log("chronos", "default", series_length, horizon)
    return "chronos", "default"


def _log(model: str, reason: str, series_length: int, horizon: int) -> None:
    logger.info(
        "model_selection",
        model=model,
        reason=reason,
        series_length=series_length,
        horizon=horizon,
    )
