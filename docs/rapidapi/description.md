# TSFA — Time Series Forecasting API

**Predict future values with confidence intervals in 3 lines of code.**

TSFA is a production-ready time series forecasting API that handles all the complexity of preprocessing, model selection, and uncertainty quantification — so you can focus on your application.

---

## Quick Start

```python
import requests

response = requests.post(
    "https://tsfa.p.rapidapi.com/v1/forecast/univariate",
    headers={
        "X-RapidAPI-Key": "YOUR_API_KEY",
        "X-RapidAPI-Host": "tsfa.p.rapidapi.com",
    },
    json={
        "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168],
        "horizon": 7,
        "frequency": "D"
    }
)

data = response.json()
print(data["forecast"]["mean"])  # [171.2, 174.5, 177.8, ...]
```

---

## Endpoints

### `POST /v1/forecast/univariate`
Forecast a single time series. Returns point forecasts with 80% and 95% prediction intervals.

**Input:** Historical observations (10–50,000 values), forecast horizon (1–365 steps), optional timestamps and frequency.

**Output:** Forecast values, confidence bounds, series diagnostics (trend, seasonality, stationarity), and metadata.

### `POST /v1/forecast/batch` *(Pro / Ultra)*
Forecast up to 500 series in a single request using parallel processing.

- **Pro plan:** up to 50 series per request
- **Ultra plan:** up to 500 series per request

Individual series errors are isolated — a failing series returns `"status": "error"` without blocking the others.

### `POST /v1/validate`
Evaluate forecast accuracy using sliding-window backtesting. Returns MAE, RMSE, MAPE, and SMAPE for each backtest window.

### `GET /v1/models`
List all available forecasting models with descriptions and credit costs.

### `GET /v1/usage`
Check your current billing period's credit consumption and remaining quota.

---

## Models

| Model | Credits | Best For |
|-------|---------|----------|
| `auto` | 1 | Automatic selection (recommended) |
| `arima` | 1 | Stationary series, interpretable forecasts |
| `chronos` | 1 | General-purpose, pre-trained transformer |
| `lstm` | 2 | Long sequences with complex patterns |

*TiDE and Ensemble models are coming in Phase 2.*

---

## Credit System

Credits are consumed per forecast request based on the model used. Your monthly credit quota resets on the 1st of each month.

| Plan | Monthly Credits | Rate Limit |
|------|----------------|------------|
| Free | 100 | 10 req/min |
| Basic | 1,000 | 30 req/min |
| Pro | 10,000 | 100 req/min |
| Ultra | 100,000 | 500 req/min |

---

## Error Codes

| HTTP | Code | Meaning |
|------|------|---------|
| 400 | `INVALID_INPUT` | Malformed request body |
| 403 | `PLAN_RESTRICTION` | Feature not available on your plan |
| 422 | `VALIDATION_ERROR` | Input failed schema validation |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests — retry after 60s |
| 503 | `REQUEST_TIMEOUT` | Request exceeded 30s — retry |

---

## Support

- **Documentation:** Full OpenAPI spec available at `/docs`
- **Issues:** Contact support via RapidAPI
- **Status:** [status.tsfa.io](https://status.tsfa.io)
