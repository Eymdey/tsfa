"""Unit tests for the model selection logic — Phase 2.

Tests the select_model() function from app/services/model_selector.py.
Returns (model_id, reason) tuple. 7 priority rules.
"""

import pytest

from app.services.model_selector import select_model


# ---------------------------------------------------------------------------
# Rule 1 — explicit model request
# ---------------------------------------------------------------------------


def test_explicit_arima_request():
    """Explicit model='arima' is returned regardless of series characteristics."""
    model_id, reason = select_model(
        series_length=200,
        horizon=30,
        has_covariates=False,
        frequency="D",
        requested_model="arima",
    )
    assert model_id == "arima"
    assert reason == "explicit_request"


def test_explicit_chronos_request():
    """Explicit model='chronos' is returned directly."""
    model_id, reason = select_model(
        series_length=5,
        horizon=7,
        has_covariates=False,
        frequency="D",
        requested_model="chronos",
    )
    assert model_id == "chronos"
    assert reason == "explicit_request"


def test_explicit_lstm_request():
    """Explicit model='lstm' is returned directly."""
    model_id, reason = select_model(
        series_length=5,
        horizon=7,
        has_covariates=False,
        frequency="D",
        requested_model="lstm",
    )
    assert model_id == "lstm"
    assert reason == "explicit_request"


# ---------------------------------------------------------------------------
# Rule 2 — series too short for Chronos (< 12)
# ---------------------------------------------------------------------------


def test_series_length_10_returns_arima():
    """10 observations → arima (series_too_short_for_chronos)."""
    model_id, reason = select_model(
        series_length=10,
        horizon=3,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "arima"
    assert reason == "series_too_short_for_chronos"


def test_series_length_11_returns_arima():
    """11 observations → arima (series_too_short_for_chronos)."""
    model_id, reason = select_model(
        series_length=11,
        horizon=7,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "arima"
    assert reason == "series_too_short_for_chronos"


# ---------------------------------------------------------------------------
# Rule 3 — series too short for LSTM (12 ≤ length < 30)
# ---------------------------------------------------------------------------


def test_series_length_12_returns_arima():
    """12 observations → arima (series_too_short_for_lstm)."""
    model_id, reason = select_model(
        series_length=12,
        horizon=7,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "arima"
    assert reason == "series_too_short_for_lstm"


def test_series_length_29_returns_arima():
    """29 observations → arima (series_too_short_for_lstm)."""
    model_id, reason = select_model(
        series_length=29,
        horizon=7,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "arima"
    assert reason == "series_too_short_for_lstm"


# ---------------------------------------------------------------------------
# Rule 4 — covariates present → tide
# ---------------------------------------------------------------------------


def test_covariates_returns_tide():
    """has_covariates=True with long series → tide."""
    model_id, reason = select_model(
        series_length=50,
        horizon=30,
        has_covariates=True,
        frequency="D",
    )
    assert model_id == "tide"
    assert reason == "covariates_present"


# ---------------------------------------------------------------------------
# Rule 5 — long series + short horizon → chronos
# ---------------------------------------------------------------------------


def test_long_series_short_horizon_returns_chronos():
    """series_length=100, horizon=30 → chronos."""
    model_id, reason = select_model(
        series_length=100,
        horizon=30,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "chronos"
    assert reason == "long_series_short_horizon"


def test_series_length_200_horizon_90_returns_chronos():
    """series_length=200, horizon=90 (boundary) → chronos."""
    model_id, reason = select_model(
        series_length=200,
        horizon=90,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "chronos"
    assert reason == "long_series_short_horizon"


# ---------------------------------------------------------------------------
# Rule 6 — long horizon → lstm
# ---------------------------------------------------------------------------


def test_long_horizon_returns_lstm():
    """horizon=120, series_length=50 → lstm."""
    model_id, reason = select_model(
        series_length=50,
        horizon=120,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "lstm"
    assert reason == "long_horizon"


def test_horizon_91_series_50_returns_lstm():
    """horizon=91 (boundary above 90), series_length=50 → lstm."""
    model_id, reason = select_model(
        series_length=50,
        horizon=91,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "lstm"
    assert reason == "long_horizon"


# ---------------------------------------------------------------------------
# Rule 7 — default → chronos
# ---------------------------------------------------------------------------


def test_default_case_returns_chronos():
    """series_length=60, horizon=30 (no other rule matches) → chronos."""
    model_id, reason = select_model(
        series_length=60,
        horizon=30,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "chronos"
    assert reason == "default"


def test_default_case_series_99_horizon_30():
    """series_length=99 (< 100, rule 5 doesn't apply), horizon=30 → chronos (default)."""
    model_id, reason = select_model(
        series_length=99,
        horizon=30,
        has_covariates=False,
        frequency="D",
    )
    assert model_id == "chronos"
    assert reason == "default"


# ---------------------------------------------------------------------------
# Return type validation
# ---------------------------------------------------------------------------


def test_returns_tuple_of_two_strings():
    """select_model() always returns a (str, str) tuple."""
    result = select_model(
        series_length=50,
        horizon=10,
        has_covariates=False,
        frequency="D",
    )
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(v, str) for v in result)


# ---------------------------------------------------------------------------
# Frequency doesn't affect model selection logic
# ---------------------------------------------------------------------------


def test_various_frequencies_long_series_short_horizon():
    """Frequency string doesn't change rule 5 outcome."""
    for freq in ["H", "D", "W", "M", "Q"]:
        model_id, _ = select_model(
            series_length=100,
            horizon=30,
            has_covariates=False,
            frequency=freq,
        )
        assert model_id == "chronos", f"Expected chronos for freq={freq}, got {model_id}"
