"""Time series cleaning pipeline.

Performs type checking, length validation, missing value imputation,
and outlier detection before model inference.
"""

import math
from dataclasses import dataclass, field


@dataclass
class CleanedSeries:
    """Result of the cleaning pipeline."""

    values_clean: list[float]
    """Cleaned values ready for model input."""

    missing_count: int
    """Number of NaN / inf values that were imputed."""

    outlier_indices: list[int]
    """Indices of detected outliers (non-destructive — values are kept)."""

    warnings: list[str]
    """Human-readable warnings about data quality."""


def clean_series(
    values: list[float],
    timestamps: list[str] | None = None,
) -> CleanedSeries:
    """Clean and validate a raw time series.

    Pipeline:
    1. Type check — all values must be numeric (float/int).
    2. Length check — at least 10 observations.
    3. Non-finite detection — replace NaN / inf with imputed values.
    4. Outlier detection via IQR method (non-destructive).

    Args:
        values: Raw observed values.
        timestamps: Optional ISO 8601 timestamp strings (not mutated).

    Returns:
        A CleanedSeries dataclass with cleaned values and diagnostics.

    Raises:
        ValueError: If the series is too short or contains non-numeric data.
    """
    warnings: list[str] = []

    # 1. Type check
    coerced: list[float] = []
    for i, v in enumerate(values):
        try:
            coerced.append(float(v))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Non-numeric value at index {i}: {v!r}. "
                "All series values must be numeric."
            ) from exc

    # 2. Length check
    if len(coerced) < 10:
        raise ValueError(
            f"Series has only {len(coerced)} observations. "
            "A minimum of 10 is required."
        )

    # 3. Non-finite handling (NaN, ±inf)
    non_finite_indices: list[int] = [
        i for i, v in enumerate(coerced) if not math.isfinite(v)
    ]
    missing_count = len(non_finite_indices)

    if missing_count > 0:
        missing_pct = missing_count / len(coerced)
        if missing_pct > 0.1:
            warnings.append(
                f"{missing_count} non-finite values ({missing_pct:.1%}) detected. "
                "High missing rate may degrade forecast quality."
            )

        # Imputation strategy: linear interpolation if <5%, forward-fill otherwise
        imputed = coerced[:]
        if missing_pct < 0.05:
            imputed = _linear_interpolate(imputed, non_finite_indices)
        else:
            imputed = _forward_fill(imputed)

        coerced = imputed

    # 4. Outlier detection (IQR, non-destructive)
    outlier_indices = _detect_outliers_iqr(coerced)
    if outlier_indices:
        warnings.append(
            f"{len(outlier_indices)} potential outlier(s) detected at indices "
            f"{outlier_indices[:10]}{'...' if len(outlier_indices) > 10 else ''}. "
            "Outliers are retained in the series."
        )

    return CleanedSeries(
        values_clean=coerced,
        missing_count=missing_count,
        outlier_indices=outlier_indices,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _linear_interpolate(values: list[float], bad_indices: set[int] | list[int]) -> list[float]:
    """Replace non-finite values with linearly interpolated estimates.

    Args:
        values: Series with potential non-finite values.
        bad_indices: Indices of non-finite values to replace.

    Returns:
        Series with interpolated values.
    """
    bad_set = set(bad_indices)
    result = values[:]
    n = len(result)

    for i in bad_set:
        # Find nearest valid left and right neighbours
        left_val: float | None = None
        right_val: float | None = None
        left_idx: int = i - 1
        right_idx: int = i + 1

        while left_idx >= 0:
            if left_idx not in bad_set and math.isfinite(result[left_idx]):
                left_val = result[left_idx]
                break
            left_idx -= 1

        while right_idx < n:
            if right_idx not in bad_set and math.isfinite(result[right_idx]):
                right_val = result[right_idx]
                break
            right_idx += 1

        if left_val is not None and right_val is not None:
            # Linear interpolation
            span = right_idx - left_idx
            result[i] = left_val + (right_val - left_val) * (i - left_idx) / span
        elif left_val is not None:
            result[i] = left_val
        elif right_val is not None:
            result[i] = right_val
        else:
            result[i] = 0.0  # Last-resort fallback

    return result


def _forward_fill(values: list[float]) -> list[float]:
    """Replace non-finite values with the last valid observation.

    Args:
        values: Series potentially containing non-finite values.

    Returns:
        Forward-filled series.
    """
    result = values[:]
    last_valid: float | None = None

    for i, v in enumerate(result):
        if math.isfinite(v):
            last_valid = v
        else:
            if last_valid is not None:
                result[i] = last_valid
            else:
                # No valid value seen yet — look ahead
                for j in range(i + 1, len(result)):
                    if math.isfinite(result[j]):
                        result[i] = result[j]
                        break
                else:
                    result[i] = 0.0

    return result


def _detect_outliers_iqr(values: list[float]) -> list[int]:
    """Identify outlier indices using the IQR method.

    Values outside [Q1 - 3*IQR, Q3 + 3*IQR] are flagged as outliers.
    The threshold is 3× IQR (conservative) to avoid flagging legitimate
    extreme but valid observations.

    Args:
        values: Clean (finite) series values.

    Returns:
        List of outlier indices (may be empty).
    """
    if len(values) < 4:
        return []

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    q1 = sorted_vals[n // 4]
    q3 = sorted_vals[(3 * n) // 4]
    iqr = q3 - q1

    if iqr == 0:
        return []

    lower_bound = q1 - 3.0 * iqr
    upper_bound = q3 + 3.0 * iqr

    return [i for i, v in enumerate(values) if v < lower_bound or v > upper_bound]
