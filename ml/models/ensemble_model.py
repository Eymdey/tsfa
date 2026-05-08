"""Ensemble model stub — Phase 2.

This module will combine Chronos + LSTM + AutoARIMA predictions
using a weighted averaging strategy.
"""

import numpy as np

from ml.models.base_model import BaseModel


class EnsembleModel(BaseModel):
    """Stub for the Ensemble model (Phase 2).

    Will combine Chronos-T5-Small, LSTM, and AutoARIMA forecasts
    with learned or heuristic weighting.
    """

    def fit(self, values: list[float], frequency: str) -> None:
        """Not implemented — Phase 2.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "EnsembleModel is not available in Phase 1. Coming in Phase 2."
        )

    def predict(
        self,
        horizon: int,
        confidence_levels: list[float],
    ) -> dict[str, np.ndarray]:
        """Not implemented — Phase 2.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "EnsembleModel is not available in Phase 1. Coming in Phase 2."
        )

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return "ensemble"
