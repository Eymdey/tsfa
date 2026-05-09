"""Chronos-T5-Small model wrapper — Phase 2.

Wraps the Amazon Chronos-T5-Small foundation model for local (CPU/GPU) inference.
In production, inference is dispatched to Modal.com via the ChronosWorker class
in ml/modal_app.py. This local wrapper is used for testing and fallback.
"""

from ml.models.base_model import BaseModel


class ChronosModel(BaseModel):
    """Chronos-T5-Small zero-shot forecasting model.

    Loads the Hugging Face model lazily on first predict() call.
    Requires at least 12 observations (Chronos internal constraint).

    When USE_MODAL=true, inference is dispatched to the ChronosWorker
    on Modal.com instead of running locally.
    """

    model_id = "amazon/chronos-t5-small"

    def __init__(self) -> None:
        self._pipeline = None
        self._series: list[float] = []

    def _load(self):
        """Lazily load the Chronos pipeline (once per process)."""
        if self._pipeline is not None:
            return self._pipeline

        import torch
        from chronos import ChronosPipeline  # type: ignore[import]

        device_map = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

        self._pipeline = ChronosPipeline.from_pretrained(
            self.model_id,
            device_map=device_map,
            torch_dtype=torch_dtype,
        )
        return self._pipeline

    # ------------------------------------------------------------------
    # BaseModel interface
    # ------------------------------------------------------------------

    def fit(self, values: list[float], frequency: str) -> None:
        """Store series for predict() — Chronos is zero-shot (no training).

        Args:
            values: Historical observations.
            frequency: Frequency string (unused by Chronos but kept for interface compatibility).
        """
        if len(values) < 12:
            raise ValueError(
                f"ChronosModel requires at least 12 observations; got {len(values)}."
            )
        self._series = list(values)

    def predict(
        self,
        horizon: int,
        confidence_levels: list[float] | None = None,
        num_samples: int = 20,
    ) -> dict:
        """Run Chronos forecast and return mean + quantile intervals.

        Args:
            horizon: Number of steps to forecast.
            confidence_levels: List of confidence level floats (e.g. [0.8, 0.95]).
            num_samples: Number of Monte Carlo samples for quantile estimation.

        Returns:
            Dict with keys:
                - "mean": list[float] of length horizon
                - "quantiles": dict mapping quantile strings to list[float]
                - "model_name": "chronos-t5-small"

        Raises:
            RuntimeError: If predict() is called before fit().
        """
        if not self._series:
            raise RuntimeError("Call fit() before predict().")

        if confidence_levels is None:
            confidence_levels = [0.8, 0.95]

        import numpy as np
        import torch

        pipeline = self._load()
        context = torch.tensor(self._series, dtype=torch.float32)

        forecast = pipeline.predict(
            context=context.unsqueeze(0),
            prediction_length=horizon,
            num_samples=num_samples,
        )
        samples = forecast[0].numpy()  # shape: (num_samples, horizon)
        mean = samples.mean(axis=0).tolist()

        quantiles: dict[str, list] = {}
        for level in confidence_levels:
            low_q = round((1.0 - level) / 2, 4)
            high_q = round(1.0 - low_q, 4)
            quantiles[str(low_q)] = np.quantile(samples, low_q, axis=0).tolist()
            quantiles[str(high_q)] = np.quantile(samples, high_q, axis=0).tolist()

        return {
            "mean": mean,
            "quantiles": quantiles,
            "model_name": "chronos-t5-small",
        }

    def get_model_name(self) -> str:
        return "chronos"
