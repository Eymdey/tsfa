"""Unit tests for LSTMModel — ml/models/lstm_model.py.

All tests mock neuralforecast so no actual training occurs in CI.
`neuralforecast` is not installed in CI; it is stubbed via sys.modules so
that lazy imports inside model methods resolve to mocks.
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out optional heavy packages BEFORE importing the model.
# ---------------------------------------------------------------------------
for _mod in ("neuralforecast", "neuralforecast.models"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from unittest.mock import patch

import pytest

from ml.models.lstm_model import LSTMModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_nf(horizon: int = 7) -> MagicMock:
    """Return a mock NeuralForecast instance with predictable output."""
    import pandas as pd
    import numpy as np

    cols = {
        "unique_id": ["series_1"] * horizon,
        "ds": pd.date_range("2024-06-01", periods=horizon),
        "LSTM": np.ones(horizon) * 42.0,
        "LSTM-lo-80": np.ones(horizon) * 38.0,
        "LSTM-hi-80": np.ones(horizon) * 46.0,
        "LSTM-lo-95": np.ones(horizon) * 35.0,
        "LSTM-hi-95": np.ones(horizon) * 49.0,
    }
    future_df = pd.DataFrame(cols)

    mock_nf = MagicMock()
    mock_nf.predict.return_value = future_df
    return mock_nf


# ---------------------------------------------------------------------------
# fit() tests
# ---------------------------------------------------------------------------


def test_fit_accepts_valid_series():
    """fit() accepts ≥ 30 observations without raising."""
    model = LSTMModel()
    model.fit(list(range(30)), "D")  # no exception


def test_fit_raises_for_short_series():
    """fit() raises ValueError when fewer than 30 observations provided."""
    model = LSTMModel()
    with pytest.raises(ValueError, match="30"):
        model.fit(list(range(29)), "D")


def test_fit_accepts_exactly_30():
    """fit() accepts exactly 30 observations (minimum boundary)."""
    model = LSTMModel()
    model.fit(list(range(30)), "D")  # should not raise


# ---------------------------------------------------------------------------
# predict() tests (mocked neuralforecast)
# ---------------------------------------------------------------------------


@patch("neuralforecast.NeuralForecast")
@patch("neuralforecast.models.LSTM")
def test_predict_returns_required_keys(mock_lstm_cls, mock_nf_cls):
    """predict() result contains 'mean' and 'model_name' keys."""
    horizon = 7
    mock_nf_cls.return_value = _make_mock_nf(horizon=horizon)

    model = LSTMModel()
    model.fit(list(range(40)), "D")
    result = model.predict(horizon=horizon)

    assert "mean" in result
    assert "model_name" in result
    assert result["model_name"] == "lstm"


@patch("neuralforecast.NeuralForecast")
@patch("neuralforecast.models.LSTM")
def test_predict_mean_length_matches_horizon(mock_lstm_cls, mock_nf_cls):
    """Length of mean forecast equals the requested horizon."""
    horizon = 7
    mock_nf_cls.return_value = _make_mock_nf(horizon=horizon)

    model = LSTMModel()
    model.fit(list(range(40)), "D")
    result = model.predict(horizon=horizon)

    assert len(result["mean"]) == horizon


@patch("neuralforecast.NeuralForecast")
@patch("neuralforecast.models.LSTM")
def test_predict_confidence_intervals_present(mock_lstm_cls, mock_nf_cls):
    """predict() returns lower_80, upper_80, lower_95, upper_95 keys."""
    horizon = 7
    mock_nf_cls.return_value = _make_mock_nf(horizon=horizon)

    model = LSTMModel()
    model.fit(list(range(40)), "D")
    result = model.predict(horizon=horizon, confidence_levels=[0.8, 0.95])

    assert "lower_80" in result
    assert "upper_80" in result
    assert "lower_95" in result
    assert "upper_95" in result


@patch("neuralforecast.NeuralForecast")
@patch("neuralforecast.models.LSTM")
def test_predict_interval_lengths_match_horizon(mock_lstm_cls, mock_nf_cls):
    """All CI arrays have the same length as horizon."""
    horizon = 5
    mock_nf_cls.return_value = _make_mock_nf(horizon=horizon)

    model = LSTMModel()
    model.fit(list(range(40)), "D")
    result = model.predict(horizon=horizon)

    for key in ("lower_80", "upper_80", "lower_95", "upper_95"):
        assert len(result[key]) == horizon, f"{key} has wrong length"


def test_predict_raises_without_fit():
    """predict() raises RuntimeError when called before fit()."""
    model = LSTMModel()
    with pytest.raises(RuntimeError, match="fit"):
        model.predict(horizon=5)


# ---------------------------------------------------------------------------
# Frequency mapping
# ---------------------------------------------------------------------------


@patch("neuralforecast.NeuralForecast")
@patch("neuralforecast.models.LSTM")
def test_predict_accepts_all_frequencies(mock_lstm_cls, mock_nf_cls):
    """predict() works for all supported frequency strings."""
    horizon = 3
    for freq in ["T", "H", "D", "W", "M", "Q", "Y", "auto"]:
        mock_nf_cls.return_value = _make_mock_nf(horizon=horizon)
        model = LSTMModel()
        model.fit(list(range(40)), freq)
        result = model.predict(horizon=horizon)
        assert "mean" in result, f"Failed for freq={freq}"


# ---------------------------------------------------------------------------
# get_model_name()
# ---------------------------------------------------------------------------


def test_get_model_name():
    """get_model_name() returns 'lstm'."""
    assert LSTMModel().get_model_name() == "lstm"
