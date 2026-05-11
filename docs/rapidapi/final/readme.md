# TSFA — Time Series Forecasting API

![version](https://img.shields.io/badge/version-1.0.0-blue)
![tests](https://img.shields.io/badge/tests-165%20passing-brightgreen)
![model](https://img.shields.io/badge/powered%20by-Chronos--T5-orange)

---

## Overview

TSFA exposes ARIMA, Chronos-T5, and LSTM forecasting models behind a single REST endpoint.
Send a JSON array of historical values, get back a point forecast with calibrated 80% and 95%
prediction intervals. No SDK, no training pipeline, no infrastructure to manage.

Deployed on a Hetzner VPS (FastAPI + Uvicorn), GPU inference runs on Modal.com on demand.
Redis provides per-minute rate limiting and monthly credit tracking. All benchmark results
are published and reproducible.

---

## Why TSFA over Alternatives

| | TSFA | AWS Forecast | Azure Time Series Insights | Nixtla TimeGPT | DIY (statsforecast) |
|---|---|---|---|---|---|
| **Setup time** | < 5 min | Hours (IAM, S3, dataset groups) | Hours (Azure workspace) | Minutes | Days (infra + tuning) |
| **Pricing model** | Flat monthly | Per training hour + storage | Per query unit | Per API call (~$0.01/call) | Server cost |
| **PRO equivalent cost** | $49/month | $200-500+/month for comparable volume | $150-400+/month | $100+/month at 10K calls | $30-100/month (your time not included) |
| **Confidence intervals** | Yes, calibrated (80% + 95%) | Yes | Limited | Yes | Manual (model-dependent) |
| **Zero-shot forecasting** | Yes (Chronos) | No | No | Yes (TimeGPT) | No |
| **Public benchmarks** | Yes | No | No | Partial | N/A |
| **Fallback to ARIMA** | Automatic | N/A | N/A | No | Manual |

**Honest caveats:** TSFA does not yet support multivariate forecasting with covariates (Phase 2).
If you need exogenous variables today, use Nixtla or AWS Forecast. If you need univariate forecasting
fast and cheap, TSFA is the better fit.

---

## Available Models

| Model ID | Type | Credits/call | Best for |
|---|---|---|---|
| `arima` | AutoARIMA (statsforecast) | 1 | Short series, interpretable output, fast |
| `chronos` | Chronos-T5-Small (GPU) | 1 | General-purpose, zero-shot, any frequency |
| `lstm` | Custom LSTM | 2 | Long series (500+ obs) with strong seasonality |
| `tide` | TiDE (GPU) | 3 | Reserved for Phase 2 (multivariate) |
| `ensemble` | Weighted ensemble | 5 | Maximum accuracy, higher cost |
| `auto` | Automatic selection | varies | Let the API choose |

**Phase 2 (coming):** `multivariate` endpoint with covariate support via TiDE.

---

## API Endpoints

| Method | Path | Plan | Description |
|---|---|---|---|
| `POST` | `/v1/forecast/univariate` | All | Forecast a single time series |
| `POST` | `/v1/forecast/batch` | PRO+ | Forecast multiple series in one call |
| `POST` | `/v1/forecast/multivariate` | Phase 2 | Forecast with covariates (stub — 501) |
| `POST` | `/v1/validate` | All | Backtest a model on historical data |
| `GET` | `/v1/models` | All | List available models and status |
| `GET` | `/v1/usage` | All | Current credit and request usage |

**Base URL:** `https://tsfa.p.rapidapi.com`

---

## Authentication

All requests require your RapidAPI key in the `X-RapidAPI-Key` header:

```
X-RapidAPI-Key: your-key-here
Content-Type: application/json
```

The subscription plan is forwarded automatically by the RapidAPI gateway via `X-RapidAPI-Subscription`.

---

## Plans & Pricing

| Plan | Price | Credits/month | Batch | Rate limit |
|---|---|---|---|---|
| BASIC | $0/month | 500 | No | 10 req/min |
| PRO | $49/month | 10,000 | Up to 50 series/batch | 30 req/min |
| ULTRA | $199/month | 50,000 | Up to 500 series/batch | 100 req/min |
| MEGA | $499/month | 200,000 | Up to 500 series/batch | 300 req/min |

Credit costs per call: `arima`=1, `chronos`=1, `lstm`=2, `tide`=3, `ensemble`=5.
Batch: N series × model credits. Validate: N windows × model credits.

Current credit usage is returned in the response headers:
```
X-Credits-Used: 1
X-Credits-Remaining: 9999
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29
```

---

## Benchmark Results

Rolling-window backtesting, 5 windows per dataset. Source: `benchmarks/results/benchmark_results.json`.

| Dataset | Model | Horizon | MAE | RMSE | MAPE | sMAPE | Windows |
|---|---|---|---|---|---|---|---|
| ETT-h1 (electricity, hourly) | arima | 24h | 2.4524 | 2.9405 | 10.12% | 10.74% | 5 |
| Exchange Rate (FX daily) | arima | 30d | 0.0085 | 0.0100 | 1.13% | 1.13% | 5 |
| M5-sample (retail daily) | arima | 14d | 9.0427 | 10.5617 | 7.63% | 7.43% | 5 |

> Chronos and LSTM benchmarks are run with `--local-only` flag disabled (requires GPU). The benchmark
> runner currently outputs ARIMA results for all three datasets. Full GPU benchmark results will be
> added in a future update.

---

## Code Examples

### Python

```python
import requests

url = "https://tsfa.p.rapidapi.com/v1/forecast/univariate"
headers = {
    "X-RapidAPI-Key": "YOUR_KEY",
    "Content-Type": "application/json",
}
payload = {
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,
    "frequency": "D",
    "model": "auto",
    "confidence_levels": [0.8, 0.95],
}

resp = requests.post(url, json=payload, headers=headers)
data = resp.json()

print(data["model_used"])               # "arima" or "chronos"
print(data["forecast"]["mean"])         # [176.3, 179.1, ...]
print(data["forecast"]["lower_95"])     # 95% lower bound
print(data["diagnostics"]["trend"])     # "upward" / "downward" / "stable"
print(data["meta"]["credits_used"])     # 1
```

### JavaScript

```javascript
const resp = await fetch("https://tsfa.p.rapidapi.com/v1/forecast/univariate", {
  method: "POST",
  headers: {
    "X-RapidAPI-Key": "YOUR_KEY",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    series: [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    horizon: 7,
    frequency: "D",
    model: "auto",
  }),
});
const data = await resp.json();
console.log(data.forecast.mean);
```

### cURL

```bash
curl -X POST "https://tsfa.p.rapidapi.com/v1/forecast/univariate" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,
    "frequency": "D",
    "model": "auto"
  }'
```

---

## Error Reference

All error responses follow the same structure:
```json
{"status": "error", "code": "ERROR_CODE", "message": "Human-readable message", "details": null}
```

| Code | HTTP | Source | Description |
|---|---|---|---|
| `VALIDATION_ERROR` | 400 | All endpoints | Series contains NaN/Inf, confidence level out of range, or other input validation failure |
| `FORBIDDEN` | 403 | All endpoints | Direct API access without RapidAPI proxy (production only) |
| `PLAN_RESTRICTION` | 403 | `/forecast/batch` | Batch forecasting requires PRO or ULTRA plan |
| `RATE_LIMIT_EXCEEDED` | 429 | All endpoints | Per-minute rate limit exceeded for your plan. Header `Retry-After: 60` is included |
| `CREDIT_LIMIT_EXCEEDED` | 429 | All endpoints | Monthly credit quota exhausted. Resets at the start of the next billing period |
| `SERIES_TOO_SHORT` | 422 | `/validate` | Series is too short for the requested horizon × n_windows combination |
| `TOO_MANY_SERIES` | 422 | `/forecast/batch` | Series count exceeds plan batch limit (PRO: 50, ULTRA/MEGA: 500) |
| `NOT_IMPLEMENTED` | 501 | `/forecast/multivariate` | Feature not yet available — coming in Phase 2 |
| `INFERENCE_TIMEOUT` | 503 | `/forecast/*` | GPU inference call exceeded timeout. Safe to retry |
| `MODAL_UNAVAILABLE` | 503 | `/forecast/*` | GPU backend unreachable. API automatically falls back to ARIMA in most cases |
| `INTERNAL_SERVER_ERROR` | 500 | All endpoints | Unexpected server error. Please retry or contact support |

---

## Changelog

### v1.0.0 — 2026-05-08
- Initial public release
- Endpoints: `/v1/forecast/univariate`, `/v1/forecast/batch`, `/v1/validate`, `/v1/models`, `/v1/usage`
- Models: ARIMA (local), Chronos-T5-Small (GPU via Modal), LSTM
- Redis-backed rate limiting and monthly credit tracking
- Automatic ARIMA fallback on GPU backend failure
- 165 tests passing (unit + integration)

---

## Support

- **Issues:** Open a ticket via the RapidAPI discussion tab
- **Workspace:** dorianmrt on RapidAPI Hub
- **Domain:** eymdey-network.com
