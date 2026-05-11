## TSFA — Time Series Forecasting API

**Predict future values with calibrated confidence intervals in 3 lines of code. No ML expertise required.**

TSFA is a production-grade REST API that handles the full forecasting pipeline: automatic preprocessing, model selection, uncertainty quantification, and diagnostics — so you focus on your application, not the math.

---

### Use Cases

**Inventory & Supply Chain** — Forecast weekly demand for thousands of SKUs to optimize reorder points and reduce stockouts. Feed historical sales data; get 14-day demand curves with 80/95% confidence bands.

**Energy & Utilities** — Predict hourly electricity consumption or renewable generation. TSFA detects daily and weekly seasonality automatically and returns actionable intervals for grid scheduling.

**Finance & Risk** — Forecast FX rates, asset prices, or transaction volumes. Exchange Rate benchmark: ARIMA achieves **MAPE 1.13%** on 30-day horizons. Use the `/validate` endpoint to backtest before going live.

---

### Models

| Model | Credits | Strengths |
|-------|---------|-----------|
| `arima` | 1 | Interpretable, fast, handles trends and seasonality. Ideal for stationary and near-stationary series. |
| `chronos` | 1 | Amazon's pre-trained T5 transformer. Zero-shot generalization across domains — no training needed. |
| `lstm` | 2 | Deep learning for long sequences with complex non-linear patterns. Best with 500+ observations. |
| `auto` | 1 | Automatic model selection — recommended when unsure. |

Benchmarks (M5, ETT-h1, Exchange Rate) → [HuggingFace Hub](https://huggingface.co/Eymdeyy/tsfa-forecasting-api)

---

### Zero Setup Required

No model training. No infrastructure. No dependencies. Call the API, get forecasts.

```python
import requests
resp = requests.post(
    "https://tsfa.p.rapidapi.com/v1/forecast/univariate",
    headers={"X-RapidAPI-Key": "YOUR_KEY", "X-RapidAPI-Host": "tsfa.p.rapidapi.com"},
    json={"series": [120, 132, 128, 145, 139, 152], "horizon": 7}
)
print(resp.json()["forecast"]["mean"])
```
