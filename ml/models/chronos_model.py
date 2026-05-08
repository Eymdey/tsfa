"""Chronos-T5 model stub — Phase 2.

This module will wrap the Amazon Chronos-T5-Small foundation model
deployed on Modal.com for GPU-accelerated inference.
"""

import numpy as np

from ml.models.base_model import BaseModel


class ChronosModel(BaseModel):
    """Stub for Chronos-T5-Small (Phase 2).

    Will leverage the Hugging Face model amazon/chronos-t5-small
    via Modal.com on-demand GPU inference.
    """

    def fit(self, values: list[float], frequency: str) -> None:
        """Not implemented — Chronos is a zero-shot model (Phase 2).

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "ChronosModel is not available in Phase 1. Coming in Phase 2."
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
            "ChronosModel is not available in Phase 1. Coming in Phase 2."
        )

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return "chronos"
