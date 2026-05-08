"""AutoARIMA model wrapper using statsforecast.

This is the ONLY fully functional model in Phase 1.
All other models are stubs that raise NotImplementedError.
"""

import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA

from ml.models.base_model import BaseModel


# Mapping from our frequency strings to pandas/statsforecast freq aliases
FREQ_MAP: dict[str, str] = {
    "T": "T",
    "H": "h",
    "D": "D",
    "W": "W",
    "M": "MS",
    "Q": "QS",
    "Y": "YS",
    "auto": "D",  # Fallback; frequency_detector should have resolved this earlier
}


class ARIMAModel(BaseModel):
    """Wrapper around statsforecast AutoARIMA.

    Usage:
        model = ARIMAModel()
        model.fit(values, frequency="D")
        result = model.predict(horizon=7, confidence_levels=[0.8, 0.95])
    """

    def __init__(self) -> None:
        """Initialise an unfitted ARIMAModel."""
        self._sf: StatsForecast | None = None
        self._horizon: int = 0
        self._frequency: str = "D"
        self._fitted: bool = False

    def fit(self, values: list[float], frequency: str) -> None:
        """Fit AutoARIMA on the provided series.

        Args:
            values: Historical observations.
            frequency: Time series frequency string (e.g. 'D', 'H', 'M').

        Raises:
            ValueError: If the series has fewer than 10 observations.
        """
        if len(values) < 10:
            raise ValueError(
                f"AutoARIMA requires at least 10 observations; got {len(values)}."
            )

        sf_freq = FREQ_MAP.get(frequency, frequency)

        df = pd.DataFrame(
            {
                "unique_id": ["series_1"] * len(values),
                "ds": pd.date_range(start="2024-01-01", periods=len(values), freq=sf_freq),
                "y": values,
            }
        )

        self._sf = StatsForecast(
            models=[AutoARIMA(season_length=self._infer_season_length(frequency))],
            freq=sf_freq,
        )
        self._sf.fit(df)
        self._frequency = frequency
        self._fitted = True

    def predict(
        self,
        horizon: int,
        confidence_levels: list[float],
    ) -> dict[str, np.ndarray]:
        """Generate forecasts and prediction intervals.

        Args:
            horizon: Number of future steps to forecast.
            confidence_levels: Confidence levels, e.g. [0.8, 0.95].

        Returns:
            Dict with keys: mean, lower_80, upper_80, lower_95, upper_95.
            Keys for levels not requested are still included but set to None.

        Raises:
            RuntimeError: If called before fit().
        """
        if not self._fitted or self._sf is None:
            raise RuntimeError("Model must be fitted before calling predict().")

        # statsforecast expects integer percentage levels (80, 95)
        int_levels: list[int] = [int(round(lvl * 100)) for lvl in confidence_levels]
        # Always request 80 and 95 for a consistent response schema
        request_levels = sorted(set(int_levels + [80, 95]))

        forecast_df: pd.DataFrame = self._sf.predict(h=horizon, level=request_levels)

        mean_col = "AutoARIMA"
        mean_values = forecast_df[mean_col].values.astype(float)

        result: dict[str, np.ndarray] = {"mean": mean_values}

        for level in request_levels:
            lo_col = f"AutoARIMA-lo-{level}"
            hi_col = f"AutoARIMA-hi-{level}"
            if lo_col in forecast_df.columns:
                result[f"lower_{level}"] = forecast_df[lo_col].values.astype(float)
            if hi_col in forecast_df.columns:
                result[f"upper_{level}"] = forecast_df[hi_col].values.astype(float)

        return result

    def get_model_name(self) -> str:
        """Return the model identifier used in API responses."""
        return "arima"

    @staticmethod
    def _infer_season_length(frequency: str) -> int:
        """Return a sensible default season length for the given frequency.

        Args:
            frequency: Frequency string.

        Returns:
            Integer season length.
        """
        season_map: dict[str, int] = {
            "T": 60,   # 60 minutes
            "H": 24,   # 24 hours
            "D": 7,    # 7 days (weekly)
            "W": 52,   # 52 weeks
            "M": 12,   # 12 months
            "Q": 4,    # 4 quarters
            "Y": 1,
            "auto": 7,
        }
        return season_map.get(frequency, 7)
