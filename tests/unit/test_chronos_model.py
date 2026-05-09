"""Unit tests for ChronosModel — ml/models/chronos_model.py.

All tests mock ChronosPipeline so no actual model is downloaded in CI.
`chronos` and `torch` are not installed in CI; they are stubbed via
sys.modules so that lazy imports inside model methods resolve to mocks.
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out optional heavy packages BEFORE importing the model.
# This allows @patch("chronos.ChronosPipeline") to work without the
# actual `chronos` package being installed.
# ---------------------------------------------------------------------------
for _mod in ("chronos", "torch", "torch.cuda"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Make torch.cuda.is_available() return False so device_map = "cpu"
sys.modules["torch"].cuda.is_available.return_value = False
sys.modules["torch"].float32 = "float32"
sys.modules["torch"].bfloat16 = "bfloat16"

from unittest.mock import patch

import numpy as np
import pytest

from ml.models.chronos_model import ChronosModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_pipeline(horizon: int = 7, num_samples: int = 20) -> MagicMock:
    """Return a mock ChronosPipeline that produces predictable numpy output.

    Uses numpy arrays (not torch tensors) so assertions work even when
    torch is mocked.  forecast[0].numpy() → ndarray of shape (num_samples, horizon).
    """
    samples_array = np.ones((num_samples, horizon)) * 42.0

    mock_slice = MagicMock()
    mock_slice.numpy.return_value = samples_array

    mock_forecast = MagicMock()
    mock_forecast.__getitem__ = MagicMock(return_value=mock_slice)

    mock_pipeline = MagicMock()
    mock_pipeline.predict.return_value = mock_forecast
    return mock_pipeline


# ---------------------------------------------------------------------------
# fit() tests
# ---------------------------------------------------------------------------


def test_fit_accepts_valid_series():
    """fit() should store series without raising for ≥ 12 observations."""
    model = ChronosModel()
    model.fit(list(range(20)), "D")  # no exception


def test_fit_raises_for_short_series():
    """fit() raises ValueError when fewer than 12 observations provided."""
    model = ChronosModel()
    with pytest.raises(ValueError, match="12"):
        model.fit(list(range(11)), "D")


def test_fit_accepts_exactly_12():
    """fit() accepts exactly 12 observations (minimum boundary)."""
    model = ChronosModel()
    model.fit(list(range(12)), "D")  # should not raise


# ---------------------------------------------------------------------------
# predict() tests (mocked pipeline)
# ---------------------------------------------------------------------------


@patch("chronos.ChronosPipeline")
def test_predict_returns_required_keys(mock_cls):
    """predict() result contains 'mean' and 'model_name' keys."""
    horizon = 5
    mock_cls.from_pretrained.return_value = _make_mock_pipeline(horizon=horizon)

    model = ChronosModel()
    model.fit(list(range(20)), "D")
    result = model.predict(horizon=horizon)

    assert "mean" in result
    assert "model_name" in result
    assert result["model_name"] == "chronos-t5-small"


@patch("chronos.ChronosPipeline")
def test_predict_mean_length_matches_horizon(mock_cls):
    """Length of mean forecast equals the requested horizon."""
    horizon = 10
    mock_cls.from_pretrained.return_value = _make_mock_pipeline(horizon=horizon)

    model = ChronosModel()
    model.fit(list(range(30)), "D")
    result = model.predict(horizon=horizon)

    assert len(result["mean"]) == horizon


@patch("chronos.ChronosPipeline")
def test_predict_quantiles_present(mock_cls):
    """predict() returns a 'quantiles' dict with expected keys."""
    horizon = 7
    mock_cls.from_pretrained.return_value = _make_mock_pipeline(horizon=horizon)

    model = ChronosModel()
    model.fit(list(range(20)), "D")
    result = model.predict(horizon=horizon, confidence_levels=[0.8, 0.95])

    assert "quantiles" in result
    quantiles = result["quantiles"]
    # 80% CI → 0.1 and 0.9
    assert "0.1" in quantiles
    assert "0.9" in quantiles
    # 95% CI → 0.025 and 0.975
    assert "0.025" in quantiles
    assert "0.975" in quantiles


@patch("chronos.ChronosPipeline")
def test_predict_raises_without_fit(mock_cls):
    """predict() raises RuntimeError when called before fit()."""
    model = ChronosModel()
    with pytest.raises(RuntimeError, match="fit"):
        model.predict(horizon=5)


@patch("chronos.ChronosPipeline")
def test_pipeline_loaded_lazily(mock_cls):
    """ChronosPipeline.from_pretrained is only called during predict, not fit."""
    mock_cls.from_pretrained.return_value = _make_mock_pipeline(horizon=5)

    model = ChronosModel()
    model.fit(list(range(20)), "D")

    # Not yet called after fit
    mock_cls.from_pretrained.assert_not_called()

    model.predict(horizon=5)

    # Called once during predict
    mock_cls.from_pretrained.assert_called_once()


@patch("chronos.ChronosPipeline")
def test_pipeline_loaded_only_once(mock_cls):
    """ChronosPipeline.from_pretrained is called at most once (cached)."""
    mock_cls.from_pretrained.return_value = _make_mock_pipeline(horizon=5)

    model = ChronosModel()
    model.fit(list(range(20)), "D")
    model.predict(horizon=5)
    model.predict(horizon=5)

    mock_cls.from_pretrained.assert_called_once()


# ---------------------------------------------------------------------------
# get_model_name()
# ---------------------------------------------------------------------------


def test_get_model_name():
    """get_model_name() returns 'chronos'."""
    assert ChronosModel().get_model_name() == "chronos"
