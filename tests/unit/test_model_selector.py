"""Unit tests for the model selection logic.

Tests the select_model() function from app/services/model_selector.py.
In Phase 1, all non-arima selections are overridden to 'arima'.
"""

import pytest

from app.services.model_selector import select_model


# ---------------------------------------------------------------------------
# Phase 1 override tests — all results must be 'arima'
# ---------------------------------------------------------------------------


def test_short_series_returns_arima():
    """Series with fewer than 30 obs must return 'arima' (spec rule 1)."""
    result = select_model(
        series_length=15,
        horizon=7,
        has_covariates=False,
        has_seasonality=False,
        frequency="D",
    )
    assert result == "arima"


def test_has_covariates_phase1_returns_arima():
    """Has covariates selects 'tide' per spec, but Phase 1 forces 'arima'."""
    result = select_model(
        series_length=50,
        horizon=7,
        has_covariates=True,
        has_seasonality=False,
        frequency="D",
    )
    # Phase 1 override: tide → arima
    assert result == "arima"


def test_long_series_short_horizon_phase1_returns_arima():
    """Long series + short horizon selects 'chronos' per spec, Phase 1 forces 'arima'."""
    result = select_model(
        series_length=200,
        horizon=30,
        has_covariates=False,
        has_seasonality=True,
        frequency="D",
    )
    # Phase 1 override: chronos → arima
    assert result == "arima"


def test_long_horizon_phase1_returns_arima():
    """Horizon > 90 + long series selects 'lstm' per spec, Phase 1 forces 'arima'."""
    result = select_model(
        series_length=100,
        horizon=120,
        has_covariates=False,
        has_seasonality=False,
        frequency="D",
    )
    # Phase 1 override: lstm → arima
    assert result == "arima"


def test_default_case_phase1_returns_arima():
    """Default case selects 'chronos' per spec, Phase 1 forces 'arima'."""
    result = select_model(
        series_length=60,
        horizon=30,
        has_covariates=False,
        has_seasonality=False,
        frequency="D",
    )
    # Phase 1 override: chronos → arima
    assert result == "arima"


# ---------------------------------------------------------------------------
# Direct arima selection (no override needed)
# ---------------------------------------------------------------------------


def test_arima_selected_directly_for_very_short_series():
    """Series of exactly 10 observations should directly return 'arima'."""
    result = select_model(
        series_length=10,
        horizon=3,
        has_covariates=False,
        has_seasonality=False,
        frequency="D",
    )
    assert result == "arima"


def test_arima_selected_for_series_length_29():
    """Series of 29 observations (< 30) should return 'arima'."""
    result = select_model(
        series_length=29,
        horizon=7,
        has_covariates=False,
        has_seasonality=False,
        frequency="D",
    )
    assert result == "arima"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_series_length_30_with_covariates_phase1():
    """Exactly 30 obs with covariates: would be 'tide', Phase 1 gives 'arima'."""
    result = select_model(
        series_length=30,
        horizon=7,
        has_covariates=True,
        has_seasonality=True,
        frequency="W",
    )
    assert result == "arima"


def test_various_frequencies_all_return_arima():
    """All frequency strings should produce 'arima' in Phase 1."""
    for freq in ["T", "H", "D", "W", "M", "Q", "Y", "auto"]:
        result = select_model(
            series_length=200,
            horizon=90,
            has_covariates=False,
            has_seasonality=True,
            frequency=freq,
        )
        assert result == "arima", f"Expected 'arima' for frequency={freq}, got '{result}'"
