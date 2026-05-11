## What is TSFA?

TSFA (Time Series Forecasting API) is a REST API that runs ARIMA, Chronos-T5, and LSTM forecasting
models on your data. Send a list of numbers, get back point forecasts with 80% and 95% prediction
intervals. No infrastructure to set up, no model training required.

---

## Models

| Model | Type | Best for | Avg latency |
|---|---|---|---|
| `arima` | Statistical (AutoARIMA) | Short series (< 200 obs), interpretable output, daily/weekly data | < 300ms |
| `chronos` | Foundation model (Chronos-T5-Small, GPU) | General-purpose, zero-shot, mixed frequencies | 1–4s |
| `lstm` | Deep learning (custom) | Long series (> 500 obs), strong seasonal patterns | 1–3s |
| `auto` | Automatic selection | Unknown data — lets the API pick the best model | varies |

> Note: Chronos and LSTM run on Modal.com GPU on demand. ARIMA runs locally on the host CPU.
> If the GPU backend is unavailable, the API automatically falls back to ARIMA and sets `fallback_used: true` in the response.

---

## Benchmark Results

Evaluated with rolling-window backtesting (5 windows per dataset). All numbers are real — no cherry-picking.

| Dataset | Model | Horizon | MAE | RMSE | MAPE | sMAPE |
|---|---|---|---|---|---|---|
| ETT-h1 (electricity, hourly) | arima | 24 | 2.4524 | 2.9405 | 10.12% | 10.74% |
| Exchange Rate (FX, daily) | arima | 30 | 0.0085 | 0.0100 | 1.13% | 1.13% |
| M5-sample (retail demand, daily) | arima | 14 | 9.0427 | 10.5617 | 7.63% | 7.43% |

Benchmark methodology: [benchmarks/results/README.md](https://github.com/Eymdey/tsfa) — source code and raw results published.

---

## Use Cases

**1. Retail demand forecasting**
A grocery chain needs weekly demand forecasts for 200 SKUs. Send each product's 104-week sales history
to `/v1/forecast/batch`, get forecasts with prediction intervals back in a single call. Credit cost:
1 credit × 200 series = 200 credits on the PRO plan.

**2. Energy consumption prediction**
An energy platform forecasts hourly consumption for the next 24 hours. Hourly data (frequency `H`),
horizon 24, `chronos` model. The API returns `lower_80`/`upper_80` intervals for scheduling reserves.

**3. Financial time series**
A fintech app forecasts 30-day FX rate trends. Exchange rate data is near-stationary — ARIMA achieves
1.13% MAPE on this type of data (see benchmarks). Pass `model: "arima"` to force the statistical model.

---

## Quick Start

```python
import requests

RAPIDAPI_KEY = "your-rapidapi-key-here"
url = "https://tsfa.p.rapidapi.com/v1/forecast/univariate"

payload = {
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,
    "frequency": "D",
    "model": "auto",
}
headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "Content-Type": "application/json",
}

resp = requests.post(url, json=payload, headers=headers)
data = resp.json()
print(data["forecast"]["mean"])       # [176.3, 179.1, ...]
print(data["forecast"]["lower_95"])   # 95% lower bound
print(data["model_used"])             # "arima" or "chronos"
```

---

## Pricing

| Plan | Price | Requests/month | Batch | Rate limit |
|---|---|---|---|---|
| BASIC | $0 | 500 | No | 10 req/min |
| PRO | $49 | 10,000 | Up to 50 series | 30 req/min |
| ULTRA | $199 | 50,000 | Up to 500 series | 100 req/min |
| MEGA | $499 | 200,000 | Up to 500 series | 300 req/min |

Credit costs: `arima` = 1 credit, `chronos` = 1 credit, `lstm` = 2 credits, `ensemble` = 5 credits.
