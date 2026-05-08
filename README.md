# TSFA — Time Series Forecasting API

Professional REST API for time series forecasting. Get point forecasts with confidence intervals in 3 lines of code.

**Phase 1:** AutoARIMA (statsforecast) — fast, statistical, interpretable.  
**Phase 2:** Chronos-T5-Small, LSTM, TiDE, Ensemble (GPU via Modal.com).

---

## Prerequisites

- Docker + Docker Compose
- Python 3.11+ (for local development without Docker)

---

## Quick start

```bash
git clone https://github.com/youruser/tsfa.git
cd tsfa
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

---

## Environment variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Listen port |
| `DEBUG` | `false` | Enable debug mode (relaxed CORS) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `CACHE_TTL_SECONDS` | `900` | Result cache duration (15 min) |
| `SENTRY_DSN` | `` | Sentry error tracking DSN (optional) |
| `PLAN_FREE_CREDITS` | `500` | Monthly credits for free tier |
| `PLAN_BASIC_CREDITS` | `10000` | Monthly credits for basic tier |
| `PLAN_PRO_CREDITS` | `50000` | Monthly credits for pro tier |
| `PLAN_ULTRA_CREDITS` | `200000` | Monthly credits for ultra tier |

---

## API endpoints

| Method | Path | Status | Description |
|---|---|---|---|
| `POST` | `/v1/forecast/univariate` | Live | Single series forecast |
| `POST` | `/v1/forecast/multivariate` | Phase 2 | Forecast with covariates |
| `POST` | `/v1/forecast/batch` | Phase 2 | Multiple series at once |
| `POST` | `/v1/validate` | Phase 1 W3 | Backtesting / cross-validation |
| `GET` | `/v1/models` | Live | List available models |
| `GET` | `/v1/usage` | Live | Credit usage and limits |
| `GET` | `/health` | Live | Health check |

---

## Example — curl

```bash
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: free" \
  -d '{
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,
    "frequency": "D",
    "model": "auto"
  }'
```

Expected response:

```json
{
  "status": "success",
  "model_used": "arima",
  "forecast": {
    "timestamps": ["2024-01-13", "2024-01-14", "..."],
    "mean": [178.2, 181.5, 184.8, 188.1, 191.4, 194.7, 198.0],
    "lower_80": ["..."],
    "upper_80": ["..."],
    "lower_95": ["..."],
    "upper_95": ["..."]
  },
  "diagnostics": {
    "trend": "upward",
    "seasonality_detected": false,
    "seasonality_period": null,
    "series_length": 12,
    "missing_values": 0,
    "stationarity": "non_stationary"
  },
  "meta": {
    "inference_time_ms": 234.0,
    "request_id": "req_abc123",
    "credits_used": 1
  }
}
```

## Example — Python

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/forecast/univariate",
    headers={"X-Plan": "free"},
    json={
        "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
        "horizon": 7,
        "frequency": "D",
        "model": "auto",
    },
)
data = response.json()
print(data["forecast"]["mean"])
```

---

## Plans and credits

| Plan | Price/month | Credits/month | Max horizon |
|---|---|---|---|
| Free | $0 | 500 | 30 |
| Basic | $49 | 10,000 | 90 |
| Pro | $199 | 50,000 | 365 |
| Ultra | $499 | 200,000 | 365 |

Credits consumed per call:
- AutoARIMA: 1 credit
- Chronos: 1 credit (Phase 2)
- LSTM: 2 credits (Phase 2)
- TiDE: 3 credits (Phase 2)
- Ensemble: 5 credits (Phase 2)

---

## Running tests

```bash
# Install dependencies (without Docker)
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

---

## Development (without Docker)

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set REDIS_URL=redis://localhost:6379/0 and start Redis locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Project structure

```
tsfa/
├── app/                  # FastAPI application
│   ├── main.py           # Entry point
│   ├── config.py         # Settings (pydantic-settings)
│   ├── dependencies.py   # Plan resolution
│   ├── routers/          # API route handlers
│   ├── schemas/          # Pydantic request/response models
│   ├── services/         # Business logic
│   └── middleware/       # Logging, error handling
├── ml/                   # ML inference layer
│   ├── models/           # Model wrappers
│   ├── preprocessing/    # Cleaning, frequency detection
│   └── postprocessing/   # Diagnostics, confidence intervals
├── tests/                # Unit and integration tests
├── infra/                # nginx, prometheus, grafana configs
├── benchmarks/           # Public benchmark scripts and results
└── docs/                 # Developer documentation
```

---

## License

MIT