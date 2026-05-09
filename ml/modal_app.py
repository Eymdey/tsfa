"""Modal.com application for GPU-accelerated ML inference.

Defines three deployable functions:
- ChronosWorker: class-based, loads Chronos-T5-Small once per container
- run_lstm: stateless function, trains LSTM on the fly per request
- run_arima: stateless function, AutoARIMA inference via statsforecast

All callables accept a JSON-serialisable dict and return a dict.
No numpy/pandas objects in arguments — serialise to Python lists before calling.
"""

import modal

app = modal.App("tsfa-inference")

inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install([
        "chronos-forecasting==1.4.0",
        "neuralforecast==1.7.5",
        "statsforecast==1.7.5",
        "torch==2.4.0",
        "transformers==4.46.0",
        "pandas==2.2.3",
        "numpy==1.26.4",
    ])
)

# ---------------------------------------------------------------------------
# Chronos — class-based so the model loads once per container
# ---------------------------------------------------------------------------


@app.cls(image=inference_image, gpu="T4")
class ChronosWorker:
    """Chronos-T5-Small inference worker.

    The model is downloaded and loaded into GPU memory once when the container
    starts (via @modal.enter), then reused across all calls to predict().
    """

    @modal.enter()
    def setup(self) -> None:
        """Load Chronos pipeline into GPU memory (called once per container)."""
        import torch
        from chronos import ChronosPipeline

        self.pipeline = ChronosPipeline.from_pretrained(
            "amazon/chronos-t5-small",
            device_map="cuda",
            torch_dtype=torch.bfloat16,
        )

    @modal.method()
    def predict(self, payload: dict) -> dict:
        """Run Chronos forecast.

        Args:
            payload: dict with keys:
                - series: list[float]
                - horizon: int
                - num_samples: int (default 20)
                - confidence_levels: list[float] (default [0.8, 0.95])

        Returns:
            dict with keys: mean, quantiles, model_name
        """
        import numpy as np
        import torch

        series = payload["series"]
        horizon = payload["horizon"]
        num_samples = payload.get("num_samples", 20)
        confidence_levels = payload.get("confidence_levels", [0.8, 0.95])

        context = torch.tensor(series, dtype=torch.float32)
        forecast = self.pipeline.predict(
            context=context.unsqueeze(0),
            prediction_length=horizon,
            num_samples=num_samples,
        )
        samples = forecast[0].numpy()
        mean = samples.mean(axis=0).tolist()

        quantiles: dict[str, list] = {}
        for level in confidence_levels:
            low_q = round((1.0 - level) / 2, 4)
            high_q = round(1.0 - low_q, 4)
            quantiles[str(low_q)] = np.quantile(samples, low_q, axis=0).tolist()
            quantiles[str(high_q)] = np.quantile(samples, high_q, axis=0).tolist()

        return {"mean": mean, "quantiles": quantiles, "model_name": "chronos-t5-small"}


# ---------------------------------------------------------------------------
# LSTM — stateless function, trains on the fly per request
# ---------------------------------------------------------------------------

_LSTM_FREQ_MAP: dict[str, str] = {
    "T": "T", "H": "h", "D": "D", "W": "W",
    "M": "MS", "Q": "QS", "Y": "YS", "auto": "D",
}


@app.function(image=inference_image, gpu="T4")
def run_lstm(payload: dict) -> dict:
    """Train and run LSTM forecast via neuralforecast.

    Args:
        payload: dict with keys:
            - series: list[float]
            - horizon: int
            - frequency: str (default "D")
            - confidence_levels: list[float] (default [0.8, 0.95])

    Returns:
        dict with keys: mean, lower_80, upper_80, lower_95, upper_95, model_name
    """
    import pandas as pd
    from neuralforecast import NeuralForecast
    from neuralforecast.models import LSTM

    series = payload["series"]
    horizon = payload["horizon"]
    frequency = payload.get("frequency", "D")
    confidence_levels = payload.get("confidence_levels", [0.8, 0.95])

    pd_freq = _LSTM_FREQ_MAP.get(frequency, "D")
    n = len(series)

    df = pd.DataFrame({
        "unique_id": ["series_1"] * n,
        "ds": pd.date_range(start="2024-01-01", periods=n, freq=pd_freq),
        "y": series,
    })

    int_levels = sorted(set([int(round(l * 100)) for l in confidence_levels] + [80, 95]))
    input_size = min(24, max(1, n // 2))

    model = LSTM(h=horizon, max_steps=50, input_size=input_size, level=int_levels)
    nf = NeuralForecast(models=[model], freq=pd_freq)
    nf.fit(df=df)
    future = nf.predict()

    result: dict = {"mean": future["LSTM"].values.tolist(), "model_name": "lstm"}
    for lvl in int_levels:
        if f"LSTM-lo-{lvl}" in future.columns:
            result[f"lower_{lvl}"] = future[f"LSTM-lo-{lvl}"].values.tolist()
        if f"LSTM-hi-{lvl}" in future.columns:
            result[f"upper_{lvl}"] = future[f"LSTM-hi-{lvl}"].values.tolist()

    return result


# ---------------------------------------------------------------------------
# AutoARIMA — stateless function (also runs locally via arima_model.py)
# ---------------------------------------------------------------------------

_ARIMA_FREQ_MAP: dict[str, str] = {
    "T": "T", "H": "h", "D": "D", "W": "W",
    "M": "MS", "Q": "QS", "Y": "YS", "auto": "D",
}

_ARIMA_SEASON_MAP: dict[str, int] = {
    "T": 60, "H": 24, "D": 7, "W": 52,
    "M": 12, "Q": 4, "Y": 1, "auto": 7,
}


@app.function(image=inference_image)
def run_arima(payload: dict) -> dict:
    """Run AutoARIMA forecast via statsforecast.

    Args:
        payload: dict with keys:
            - series: list[float]
            - horizon: int
            - frequency: str (default "D")
            - confidence_levels: list[float] (default [0.8, 0.95])

    Returns:
        dict with keys: mean, lower_80, upper_80, lower_95, upper_95, model_name
    """
    import pandas as pd
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA

    series = payload["series"]
    horizon = payload["horizon"]
    frequency = payload.get("frequency", "D")
    confidence_levels = payload.get("confidence_levels", [0.8, 0.95])

    sf_freq = _ARIMA_FREQ_MAP.get(frequency, "D")
    season_length = _ARIMA_SEASON_MAP.get(frequency, 7)
    n = len(series)

    df = pd.DataFrame({
        "unique_id": ["series_1"] * n,
        "ds": pd.date_range(start="2024-01-01", periods=n, freq=sf_freq),
        "y": series,
    })

    int_levels = sorted(set([int(round(l * 100)) for l in confidence_levels] + [80, 95]))

    sf = StatsForecast(
        models=[AutoARIMA(season_length=season_length)],
        freq=sf_freq,
    )
    sf.fit(df)
    forecast_df = sf.predict(h=horizon, level=int_levels)

    result: dict = {
        "mean": forecast_df["AutoARIMA"].values.tolist(),
        "model_name": "arima",
    }
    for lvl in int_levels:
        lo_col = f"AutoARIMA-lo-{lvl}"
        hi_col = f"AutoARIMA-hi-{lvl}"
        if lo_col in forecast_df.columns:
            result[f"lower_{lvl}"] = forecast_df[lo_col].values.tolist()
        if hi_col in forecast_df.columns:
            result[f"upper_{lvl}"] = forecast_df[hi_col].values.tolist()

    return result
