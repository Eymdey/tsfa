"""Unit tests for Pydantic request/response schemas.

Covers validation constraints on UnivariateForecastRequest:
- Valid input passes
- Series too short raises ValidationError
- Horizon out of range raises ValidationError
- Invalid frequency raises ValidationError
- Invalid model raises ValidationError
- Default confidence_levels are [0.8, 0.95]
"""

import pytest
from pydantic import ValidationError

from app.schemas.forecast import UnivariateForecastRequest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SERIES = [120.0, 132.0, 128.0, 145.0, 139.0, 152.0, 148.0, 160.0, 155.0, 168.0, 163.0, 175.0]
VALID_HORIZON = 7


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_request_passes():
    """A well-formed request should parse without errors."""
    req = UnivariateForecastRequest(
        series=VALID_SERIES,
        horizon=VALID_HORIZON,
        frequency="D",
        model="auto",
    )
    assert len(req.series) == 12
    assert req.horizon == 7
    assert req.frequency == "D"
    assert req.model == "auto"


def test_default_confidence_levels():
    """confidence_levels should default to [0.8, 0.95]."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=VALID_HORIZON)
    assert req.confidence_levels == [0.8, 0.95]


def test_default_frequency_is_auto():
    """frequency should default to 'auto'."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=VALID_HORIZON)
    assert req.frequency == "auto"


def test_default_model_is_auto():
    """model should default to 'auto'."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=VALID_HORIZON)
    assert req.model == "auto"


def test_default_seasonality_is_auto():
    """seasonality should default to 'auto'."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=VALID_HORIZON)
    assert req.seasonality == "auto"


# ---------------------------------------------------------------------------
# Series validation
# ---------------------------------------------------------------------------


def test_series_too_short_raises():
    """A series with fewer than 10 observations must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        UnivariateForecastRequest(
            series=[1.0, 2.0, 3.0, 4.0, 5.0],  # Only 5 values
            horizon=3,
        )
    errors = exc_info.value.errors()
    assert any("series" in str(e["loc"]) for e in errors)


def test_series_exactly_10_passes():
    """A series with exactly 10 observations is valid."""
    req = UnivariateForecastRequest(
        series=[float(i) for i in range(10)],
        horizon=3,
    )
    assert len(req.series) == 10


def test_series_with_non_finite_raises():
    """A series containing infinity must raise ValidationError."""
    import math

    with pytest.raises(ValidationError):
        UnivariateForecastRequest(
            series=[1.0, 2.0, 3.0, math.inf, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            horizon=3,
        )


# ---------------------------------------------------------------------------
# Horizon validation
# ---------------------------------------------------------------------------


def test_horizon_zero_raises():
    """horizon=0 must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        UnivariateForecastRequest(series=VALID_SERIES, horizon=0)
    errors = exc_info.value.errors()
    assert any("horizon" in str(e["loc"]) for e in errors)


def test_horizon_too_large_raises():
    """horizon > 365 must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        UnivariateForecastRequest(series=VALID_SERIES, horizon=366)
    errors = exc_info.value.errors()
    assert any("horizon" in str(e["loc"]) for e in errors)


def test_horizon_exactly_365_passes():
    """horizon=365 is the maximum allowed value."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=365)
    assert req.horizon == 365


def test_horizon_exactly_1_passes():
    """horizon=1 is the minimum allowed value."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=1)
    assert req.horizon == 1


# ---------------------------------------------------------------------------
# Frequency validation
# ---------------------------------------------------------------------------


def test_invalid_frequency_raises():
    """An unsupported frequency string must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        UnivariateForecastRequest(
            series=VALID_SERIES,
            horizon=VALID_HORIZON,
            frequency="X",  # type: ignore[arg-type]
        )
    errors = exc_info.value.errors()
    assert any("frequency" in str(e["loc"]) for e in errors)


@pytest.mark.parametrize("freq", ["T", "H", "D", "W", "M", "Q", "Y", "auto"])
def test_all_valid_frequencies(freq: str):
    """All documented frequencies should be accepted."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=VALID_HORIZON, frequency=freq)
    assert req.frequency == freq


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------


def test_invalid_model_raises():
    """An unrecognised model name must raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        UnivariateForecastRequest(
            series=VALID_SERIES,
            horizon=VALID_HORIZON,
            model="gpt4",  # type: ignore[arg-type]
        )
    errors = exc_info.value.errors()
    assert any("model" in str(e["loc"]) for e in errors)


@pytest.mark.parametrize("model", ["auto", "chronos", "lstm", "tide", "arima", "ensemble"])
def test_all_valid_models(model: str):
    """All documented model names should be accepted."""
    req = UnivariateForecastRequest(series=VALID_SERIES, horizon=VALID_HORIZON, model=model)
    assert req.model == model


# ---------------------------------------------------------------------------
# Confidence levels validation
# ---------------------------------------------------------------------------


def test_confidence_level_out_of_range_raises():
    """Confidence levels outside (0, 1) must raise ValidationError."""
    with pytest.raises(ValidationError):
        UnivariateForecastRequest(
            series=VALID_SERIES,
            horizon=VALID_HORIZON,
            confidence_levels=[0.95, 1.5],  # 1.5 is invalid
        )
