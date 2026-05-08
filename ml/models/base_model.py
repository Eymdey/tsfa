"""Abstract base class for all forecasting models.

Every model wrapper must implement fit() and predict() to ensure a
consistent interface across statistical, deep learning, and ensemble models.
"""

from abc import ABC, abstractmethod
import numpy as np


class BaseModel(ABC):
    """Abstract forecasting model interface.

    Subclasses must implement fit() and predict() and may override
    get_model_name() to provide a descriptive label.
    """

    @abstractmethod
    def fit(self, values: list[float], frequency: str) -> None:
        """Fit the model on the provided time series.

        Args:
            values: Historical observations as a list of floats.
            frequency: Pandas-compatible frequency string (e.g. 'D', 'H', 'M').

        Raises:
            ValueError: If the series is too short or malformed.
        """
        ...

    @abstractmethod
    def predict(
        self,
        horizon: int,
        confidence_levels: list[float],
    ) -> dict[str, np.ndarray]:
        """Generate point forecasts and prediction intervals.

        Args:
            horizon: Number of future steps to forecast.
            confidence_levels: List of confidence level floats (e.g. [0.8, 0.95]).

        Returns:
            A dict with at least a "mean" key (np.ndarray of length *horizon*).
            Additional keys follow the pattern "lower_{level}" / "upper_{level}"
            where *level* is 80 or 95 (integer percentage).

        Raises:
            RuntimeError: If predict() is called before fit().
        """
        ...

    def get_model_name(self) -> str:
        """Return a human-readable model name.

        Returns:
            The class name by default; override for a friendlier label.
        """
        return self.__class__.__name__
