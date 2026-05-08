"""LSTM custom model stub — Phase 2.

This module will wrap a fine-tuned LSTM model via neuralforecast,
deployed on Modal.com for GPU-accelerated inference.
"""

import numpy as np

from ml.models.base_model import BaseModel


class LSTMModel(BaseModel):
    """Stub for the custom LSTM model (Phase 2).

    Will use neuralforecast LSTM with custom training on domain datasets.
    """

    def fit(self, values: list[float], frequency: str) -> None:
        """Not implemented — Phase 2.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "LSTMModel is not available in Phase 1. Coming in Phase 2."
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
            "LSTMModel is not available in Phase 1. Coming in Phase 2."
        )

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return "lstm"
