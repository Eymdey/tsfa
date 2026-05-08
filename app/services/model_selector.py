"""Model selection logic for the 'auto' model mode.

Implements the selection rules defined in the project specifications (section 6).
In Phase 1, all non-arima selections are silently overridden to 'arima'
since it is the only fully implemented model.
"""

import structlog

logger = structlog.get_logger(__name__)


def select_model(
    series_length: int,
    horizon: int,
    has_covariates: bool,
    has_seasonality: bool,
    frequency: str,
) -> str:
    """Select the most appropriate model based on series characteristics.

    Applies the decision rules from spec section 6:

    1. series_length < 30 → arima
    2. has_covariates     → tide
    3. series_length >= 100 and horizon <= 90 → chronos
    4. horizon > 90 and series_length >= 50   → lstm
    5. default                                → chronos

    Phase 1 override: if the selected model is not 'arima', it is forced
    to 'arima' with a log warning, because other models are not yet
    implemented.

    Args:
        series_length: Number of observations in the cleaned series.
        horizon: Number of steps to forecast.
        has_covariates: Whether covariate features are present.
        has_seasonality: Whether a seasonal pattern was detected.
        frequency: Resolved frequency string (e.g. 'D', 'H').

    Returns:
        The name of the selected model as a lowercase string.
    """
    # --- Spec section 6 rules ---
    if series_length < 30:
        ideal_model = "arima"
    elif has_covariates:
        ideal_model = "tide"
    elif series_length >= 100 and horizon <= 90:
        ideal_model = "chronos"
    elif horizon > 90 and series_length >= 50:
        ideal_model = "lstm"
    else:
        ideal_model = "chronos"

    # --- Phase 1 override ---
    if ideal_model != "arima":
        logger.info(
            "phase1_model_override",
            ideal_model=ideal_model,
            forced_model="arima",
            reason=(
                f"'{ideal_model}' is not implemented in Phase 1. "
                "Falling back to AutoARIMA."
            ),
            series_length=series_length,
            horizon=horizon,
        )
        return "arima"

    return ideal_model
