"""Forecast accuracy metrics for backtesting and model evaluation."""

import math
from typing import Sequence


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean Absolute Error.

    Args:
        y_true: Actual observed values.
        y_pred: Predicted values.

    Returns:
        MAE (always >= 0).
    """
    n = len(y_true)
    if n == 0:
        return 0.0
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / n


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Root Mean Squared Error.

    Args:
        y_true: Actual observed values.
        y_pred: Predicted values.

    Returns:
        RMSE (always >= 0).
    """
    n = len(y_true)
    if n == 0:
        return 0.0
    mse = sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / n
    return math.sqrt(mse)


def mape(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean Absolute Percentage Error.

    Skips pairs where y_true == 0 to avoid division by zero.
    Returns 0.0 if all true values are zero.

    Args:
        y_true: Actual observed values.
        y_pred: Predicted values.

    Returns:
        MAPE as a decimal (e.g. 0.05 = 5%). Always >= 0.
    """
    valid = [(t, p) for t, p in zip(y_true, y_pred) if t != 0.0]
    if not valid:
        return 0.0
    return sum(abs((t - p) / t) for t, p in valid) / len(valid)


def smape(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Symmetric Mean Absolute Percentage Error.

    Uses the standard definition: 2*|y-yhat| / (|y| + |yhat|).
    Skips pairs where both values are zero to avoid division by zero.

    Args:
        y_true: Actual observed values.
        y_pred: Predicted values.

    Returns:
        sMAPE as a decimal (e.g. 0.05 = 5%). Always >= 0.
    """
    total = 0.0
    count = 0
    for t, p in zip(y_true, y_pred):
        denom = abs(t) + abs(p)
        if denom == 0.0:
            continue
        total += 2.0 * abs(t - p) / denom
        count += 1
    if count == 0:
        return 0.0
    return total / count


def coverage(
    y_true: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> float:
    """Empirical coverage: fraction of true values within [lower, upper].

    Args:
        y_true: Actual observed values.
        lower: Lower bound of the prediction interval.
        upper: Upper bound of the prediction interval.

    Returns:
        Coverage fraction in [0, 1].
    """
    n = len(y_true)
    if n == 0:
        return 0.0
    inside = sum(1 for t, lo, hi in zip(y_true, lower, upper) if lo <= t <= hi)
    return inside / n
