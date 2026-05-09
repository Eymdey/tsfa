"""LSTM model wrapper via neuralforecast — Phase 2.

Trains an LSTM on-the-fly per request using the neuralforecast library.
max_steps=50 is a deliberate speed/quality trade-off to keep latency < 5s.
In production, inference is dispatched to Modal.com (GPU) via run_lstm()
in ml/modal_app.py. This local wrapper is used for testing and fallback.
"""

from ml.models.base_model import BaseModel

_FREQ_MAP: dict[str, str] = {
    "T": "T",
    "H": "h",
    "D": "D",
    "W": "W",
    "M": "MS",
    "Q": "QS",
    "Y": "YS",
    "auto": "D",
}


class LSTMModel(BaseModel):
    """neuralforecast LSTM forecasting model.

    Trains from scratch on each series (on-the-fly).
    Requires at least 30 observations.
    """

    def __init__(self) -> None:
        self._series: list[float] = []
        self._frequency: str = "D"

    # ------------------------------------------------------------------
    # BaseModel interface
    # ------------------------------------------------------------------

    def fit(self, values: list[float], frequency: str) -> None:
        """Store series and frequency for predict().

        Args:
            values: Historical observations.
            frequency: Frequency string (e.g. 'D', 'H', 'M').

        Raises:
            ValueError: If fewer than 30 observations are provided.
        """
        if len(values) < 30:
            raise ValueError(
                f"LSTMModel requires at least 30 observations; got {len(values)}."
            )
        self._series = list(values)
        self._frequency = frequency

    def predict(
        self,
        horizon: int,
        confidence_levels: list[float] | None = None,
    ) -> dict:
        """Train LSTM and generate forecasts with confidence intervals.

        Args:
            horizon: Number of steps to forecast.
            confidence_levels: List of confidence level floats (e.g. [0.8, 0.95]).

        Returns:
            Dict with keys:
                - "mean": list[float] of length horizon
                - "lower_80", "upper_80", "lower_95", "upper_95": list[float]
                - "model_name": "lstm"

        Raises:
            RuntimeError: If predict() is called before fit().
        """
        if not self._series:
            raise RuntimeError("Call fit() before predict().")

        if confidence_levels is None:
            confidence_levels = [0.8, 0.95]

        import pandas as pd
        from neuralforecast import NeuralForecast  # type: ignore[import]
        from neuralforecast.models import LSTM  # type: ignore[import]

        pd_freq = _FREQ_MAP.get(self._frequency, "D")
        n = len(self._series)

        df = pd.DataFrame({
            "unique_id": ["series_1"] * n,
            "ds": pd.date_range(start="2024-01-01", periods=n, freq=pd_freq),
            "y": self._series,
        })

        int_levels = sorted(
            set([int(round(lvl * 100)) for lvl in confidence_levels] + [80, 95])
        )
        input_size = min(24, max(1, n // 2))

        model = LSTM(h=horizon, max_steps=50, input_size=input_size, level=int_levels)
        nf = NeuralForecast(models=[model], freq=pd_freq)
        nf.fit(df=df)
        future = nf.predict()

        result: dict = {
            "mean": future["LSTM"].values.tolist(),
            "model_name": "lstm",
        }
        for lvl in int_levels:
            lo_col = f"LSTM-lo-{lvl}"
            hi_col = f"LSTM-hi-{lvl}"
            if lo_col in future.columns:
                result[f"lower_{lvl}"] = future[lo_col].values.tolist()
            if hi_col in future.columns:
                result[f"upper_{lvl}"] = future[hi_col].values.tolist()

        return result

    def get_model_name(self) -> str:
        return "lstm"
