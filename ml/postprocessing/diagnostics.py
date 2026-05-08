"""Time series diagnostics computation.

Provides trend detection (linear regression), seasonality detection (FFT/ACF),
and stationarity testing (ADF) for the diagnostics section of API responses.
"""

from dataclasses import dataclass
import math


@dataclass
class DiagnosticsResult:
    """Computed diagnostics for a time series."""

    trend: str
    """'upward', 'downward', or 'stable'."""

    seasonality_detected: bool
    """Whether a significant seasonal pattern was found."""

    seasonality_period: int | None
    """Dominant seasonal period in number of observations, or None."""

    stationarity: str
    """'stationary' or 'non_stationary' based on ADF test."""

    missing_values: int
    """Number of missing / imputed values in the original series."""

    series_length: int
    """Total number of observations."""


def compute_diagnostics(
    series: list[float],
    frequency: str,
    missing_values: int = 0,
) -> DiagnosticsResult:
    """Compute trend, seasonality, and stationarity diagnostics.

    Args:
        series: Clean (finite) series values.
        frequency: Frequency string (e.g. 'D', 'H', 'M').
        missing_values: Number of values that were imputed upstream.

    Returns:
        A DiagnosticsResult dataclass.
    """
    trend = _detect_trend(series)
    seasonality_detected, seasonality_period = _detect_seasonality(series, frequency)
    stationarity = _test_stationarity(series)

    return DiagnosticsResult(
        trend=trend,
        seasonality_detected=seasonality_detected,
        seasonality_period=seasonality_period,
        stationarity=stationarity,
        missing_values=missing_values,
        series_length=len(series),
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _detect_trend(series: list[float]) -> str:
    """Estimate the dominant trend via ordinary least squares.

    A slope greater than 1% of the mean absolute value per step is
    classified as upward or downward; otherwise stable.

    Args:
        series: Series values.

    Returns:
        'upward', 'downward', or 'stable'.
    """
    n = len(series)
    if n < 2:
        return "stable"

    x_mean = (n - 1) / 2.0
    y_mean = sum(series) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(series))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Threshold: 0.5% of mean absolute value per observation
    mean_abs = sum(abs(v) for v in series) / n
    threshold = 0.005 * mean_abs if mean_abs > 0 else 1e-10

    if slope > threshold:
        return "upward"
    if slope < -threshold:
        return "downward"
    return "stable"


def _detect_seasonality(
    series: list[float],
    frequency: str,
) -> tuple[bool, int | None]:
    """Detect dominant seasonality using ACF.

    Checks candidate seasonal periods based on the frequency and
    reports the one with the highest autocorrelation above a threshold.

    Args:
        series: Series values.
        frequency: Frequency string used to determine candidate periods.

    Returns:
        Tuple of (seasonality_detected, period | None).
    """
    n = len(series)
    if n < 12:
        return False, None

    # Candidate periods to check
    candidates: list[int] = _get_candidate_periods(frequency, n)

    mean = sum(series) / n
    variance = sum((v - mean) ** 2 for v in series) / n

    if variance == 0:
        return False, None

    best_lag: int | None = None
    best_acf: float = 0.0

    for lag in candidates:
        if lag >= n:
            continue
        acf_val = _autocorrelation(series, lag, mean, variance)
        if acf_val > best_acf:
            best_acf = acf_val
            best_lag = lag

    # Significance threshold: 2 / sqrt(n) (95% CI under white noise assumption)
    threshold = 2.0 / math.sqrt(n)

    if best_lag is not None and best_acf > threshold:
        return True, best_lag

    return False, None


def _autocorrelation(series: list[float], lag: int, mean: float, variance: float) -> float:
    """Compute autocorrelation at a given lag.

    Args:
        series: Series values.
        lag: Lag in number of observations.
        mean: Series mean.
        variance: Series variance.

    Returns:
        Autocorrelation coefficient in [-1, 1].
    """
    n = len(series)
    if variance == 0 or lag >= n:
        return 0.0

    cov = sum(
        (series[i] - mean) * (series[i - lag] - mean)
        for i in range(lag, n)
    ) / n

    return cov / variance


def _get_candidate_periods(frequency: str, n: int) -> list[int]:
    """Return candidate seasonal periods for the given frequency.

    Args:
        frequency: Frequency string.
        n: Series length (used to cap periods).

    Returns:
        List of integer candidate periods.
    """
    period_map: dict[str, list[int]] = {
        "T": [60, 1440],           # 1 hour, 1 day in minutes
        "H": [24, 168],            # 1 day, 1 week in hours
        "D": [7, 30, 365],         # weekly, monthly, yearly in days
        "W": [4, 13, 52],          # monthly, quarterly, yearly in weeks
        "M": [3, 6, 12],           # quarterly, semi-annual, annual in months
        "Q": [4],                  # annual in quarters
        "Y": [1],
        "auto": [7, 12, 24, 52],
    }
    candidates = period_map.get(frequency, [7, 12, 24])
    return [p for p in candidates if p < n]


def _test_stationarity(series: list[float]) -> str:
    """Perform an Augmented Dickey-Fuller test for stationarity.

    Uses statsmodels' adfuller implementation. Falls back to a
    simple variance-based heuristic if statsmodels is unavailable.

    Args:
        series: Series values.

    Returns:
        'stationary' if the ADF p-value < 0.05, else 'non_stationary'.
    """
    if len(series) < 10:
        return "non_stationary"

    try:
        from statsmodels.tsa.stattools import adfuller
        import numpy as np

        result = adfuller(np.array(series), autolag="AIC")
        p_value: float = result[1]
        return "stationary" if p_value < 0.05 else "non_stationary"

    except Exception:
        # Fallback: compare variance of first and second halves
        mid = len(series) // 2
        first_half = series[:mid]
        second_half = series[mid:]
        mean1 = sum(first_half) / len(first_half)
        mean2 = sum(second_half) / len(second_half)
        var1 = sum((v - mean1) ** 2 for v in first_half) / len(first_half)
        var2 = sum((v - mean2) ** 2 for v in second_half) / len(second_half)

        overall_mean = sum(series) / len(series)
        overall_var = sum((v - overall_mean) ** 2 for v in series) / len(series)

        if overall_var == 0:
            return "stationary"

        # If variance ratio is close to 1, likely stationary
        if abs(var1 - var2) / (overall_var + 1e-10) < 0.5:
            return "stationary"
        return "non_stationary"
