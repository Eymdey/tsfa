"""TiDE (Time-series Dense Encoder) model stub — Phase 2.

This module will wrap Google Research's TiDE model via neuralforecast,
designed for multivariate forecasting with covariates.
"""

import numpy as np

from ml.models.base_model import BaseModel


class TiDEModel(BaseModel):
    """Stub for the TiDE multivariate model (Phase 2).

    TiDE excels at long-horizon forecasting with multiple covariates.
    Will be deployed on Modal.com via neuralforecast.
    """

    def fit(self, values: list[float], frequency: str) -> None:
        """Not implemented — Phase 2.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "TiDEModel is not available in Phase 1. Coming in Phase 2."
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
            "TiDEModel is not available in Phase 1. Coming in Phase 2."
        )

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return "tide"
