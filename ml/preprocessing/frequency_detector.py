"""Automatic time series frequency detection.

Infers the dominant observation frequency from a list of ISO 8601 timestamps.
Falls back to a configurable default when timestamps are absent or ambiguous.
"""

from datetime import datetime, timezone


def detect_frequency(
    timestamps: list[str] | None,
    fallback: str = "D",
) -> str:
    """Infer the time series frequency from ISO 8601 timestamp strings.

    The algorithm computes the median gap between consecutive timestamps
    and maps it to the closest standard frequency alias.

    Args:
        timestamps: List of ISO 8601 timestamp strings, e.g. ["2024-01-01", ...].
                    Must have at least 2 entries for frequency detection.
        fallback: Frequency to return when detection is not possible.
                  Defaults to "D" (daily).

    Returns:
        A frequency string: one of "T", "H", "D", "W", "M", "Q", "Y".
    """
    if not timestamps or len(timestamps) < 2:
        return fallback

    # Parse timestamps — support date-only and datetime formats
    parsed: list[datetime] = []
    for ts in timestamps:
        try:
            dt = _parse_timestamp(ts)
            parsed.append(dt)
        except (ValueError, TypeError):
            return fallback

    if len(parsed) < 2:
        return fallback

    # Compute gaps in seconds between consecutive timestamps
    gaps_seconds: list[float] = []
    for i in range(1, len(parsed)):
        delta = (parsed[i] - parsed[i - 1]).total_seconds()
        if delta > 0:
            gaps_seconds.append(delta)

    if not gaps_seconds:
        return fallback

    median_gap = _median(gaps_seconds)

    return _seconds_to_frequency(median_gap)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_timestamp(ts: str) -> datetime:
    """Parse an ISO 8601 string into a timezone-naive datetime.

    Args:
        ts: ISO 8601 timestamp string.

    Returns:
        Parsed datetime (UTC-normalized, timezone-naive).

    Raises:
        ValueError: If the string cannot be parsed.
    """
    # Try common formats in order of specificity
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts.split("+")[0].split("Z")[0].strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: {ts!r}")


def _median(values: list[float]) -> float:
    """Compute the median of a list of floats.

    Args:
        values: Non-empty list of numbers.

    Returns:
        The median value.
    """
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return sorted_vals[mid]


def _seconds_to_frequency(seconds: float) -> str:
    """Map a median gap in seconds to the closest frequency alias.

    Thresholds (based on typical data science conventions):
    - < 90 s → "T" (minute-level)
    - < 3600 s (1 h) → "H"
    - < 3 days → "D"
    - < 10 days → "W"
    - < 45 days → "M"
    - < 120 days → "Q"
    - else → "Y"

    Args:
        seconds: Median inter-observation gap in seconds.

    Returns:
        Frequency alias string.
    """
    minute = 60.0
    hour = 3600.0
    day = 86400.0

    if seconds < 90:
        return "T"
    if seconds < hour:
        return "H"
    if seconds < 3 * day:
        return "D"
    if seconds < 10 * day:
        return "W"
    if seconds < 45 * day:
        return "M"
    if seconds < 120 * day:
        return "Q"
    return "Y"
