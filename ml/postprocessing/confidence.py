"""Confidence interval computation for forecast outputs.

Provides utilities to compute or widen prediction intervals based on
residual standard deviation or model-based estimates.
"""

import math
import numpy as np


def compute_confidence_intervals(
    mean: np.ndarray,
    residuals: np.ndarray | None,
    levels: list[float],
) -> dict[str, np.ndarray]:
    """Compute symmetric prediction intervals around the forecast mean.

    When residuals are available, the standard deviation is derived from them.
    Otherwise, a conservative estimate is used (5% of absolute mean per level).

    Args:
        mean: Point forecast array of shape (horizon,).
        residuals: In-sample residuals array of arbitrary length, or None.
        levels: Confidence levels in (0, 1), e.g. [0.8, 0.95].

    Returns:
        Dict with keys like "lower_80", "upper_80", "lower_95", "upper_95"
        for each requested level.  Keys are integer-percentage strings.
    """
    horizon = len(mean)
    result: dict[str, np.ndarray] = {}

    # Estimate residual standard deviation
    if residuals is not None and len(residuals) > 0:
        std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else float(np.std(residuals))
    else:
        # Fallback: 3% of mean absolute value
        abs_mean = float(np.mean(np.abs(mean)))
        std = abs_mean * 0.03 if abs_mean > 0 else 1.0

    for level in levels:
        z = _normal_quantile(level)
        int_level = int(round(level * 100))

        lower = mean - z * std
        upper = mean + z * std

        result[f"lower_{int_level}"] = lower
        result[f"upper_{int_level}"] = upper

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _normal_quantile(confidence_level: float) -> float:
    """Return the z-score corresponding to a two-sided confidence level.

    Uses a rational approximation of the normal quantile function.

    Args:
        confidence_level: Confidence level in (0, 1), e.g. 0.95.

    Returns:
        Positive z-score such that P(-z < Z < z) ≈ confidence_level.
    """
    # Known exact values for common levels
    lookup: dict[int, float] = {
        80: 1.2816,
        90: 1.6449,
        95: 1.9600,
        99: 2.5758,
    }
    int_level = int(round(confidence_level * 100))
    if int_level in lookup:
        return lookup[int_level]

    # Use scipy if available
    try:
        from scipy.stats import norm
        alpha = 1.0 - confidence_level
        return float(norm.ppf(1 - alpha / 2))
    except ImportError:
        pass

    # Rational approximation (Abramowitz & Stegun 26.2.17)
    p = (1.0 + confidence_level) / 2.0
    if p >= 1.0:
        return 4.0
    if p <= 0.0:
        return -4.0

    t = math.sqrt(-2.0 * math.log(1.0 - p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    numerator = c0 + c1 * t + c2 * t ** 2
    denominator = 1.0 + d1 * t + d2 * t ** 2 + d3 * t ** 3
    z = t - numerator / denominator
    return z
