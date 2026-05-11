# TSFA — Time Series Forecasting API

Professional REST API for time series forecasting. Get point forecasts with confidence intervals in 3 lines of code.

![Tests](https://img.shields.io/badge/tests-165%20passing-brightgreen)
[![RapidAPI](https://img.shields.io/badge/RapidAPI-Available-blue)](https://rapidapi.com/hub)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Eymdeyy%2Ftsfa--forecasting--api-yellow)](https://huggingface.co/Eymdeyy/tsfa-forecasting-api)

---

## Quick Start

```bash
curl -X POST https://tsfa.p.rapidapi.com/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: tsfa.p.rapidapi.com" \
  -d '{
    "series": [100, 102, 98, 105, 103, 107, 104, 109, 106, 111],
    "horizon": 7,
    "frequency": "D",
    "model": "auto"
  }'
```

Or run locally:

```bash
git clone https://github.com/Eymdey/tsfa.git
cd tsfa
cp .env.example .env
docker compose up --build
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: free" \
  -d '{"series":[100,102,98,105,103,107,104,109,106,111],"horizon":7,"frequency":"D","model":"auto"}'
```

---

## Models

| Model | Type | Best for | Horizon | Credits/call |
|---|---|---|---|---|
| **AutoARIMA** | Statistical | Short series, interpretability | ≤180 days | 1 |
| **Chronos-T5** | Foundation model | Zero-shot, general purpose | ≤365 days | 1 |
| **LSTM** | Deep learning | Noisy, non-linear, long horizon | ≤365 days | 2 |
| TiDE *(Phase 3)* | Deep learning | Multivariate with covariates | ≤365 days | 3 |
| Ensemble *(Phase 3)* | Ensemble | Highest accuracy | ≤180 days | 5 |

Auto-selection logic:
- Series ≥ 30 obs AND horizon ≤ 90 → **Chronos**
- Horizon > 90 → **LSTM**
- Otherwise → **AutoARIMA**

---

## Benchmarks

Results on public datasets (rolling-window backtesting, 5 windows):

| Dataset | Frequency | Model | MAE | RMSE | MAPE |
|---|---|---|---|---|---|
| ETT-h1 | Hourly | AutoARIMA | 2.4524 | 2.9405 | 10.12% |
| Exchange Rate | Daily | AutoARIMA | 0.0085 | 0.0100 | 1.13% |
| M5 Sample | Daily | AutoARIMA | 9.0427 | 10.5617 | 7.63% |

See [benchmarks/results/README.md](benchmarks/results/README.md) for full methodology.

---

## API Endpoints

| Method | Path | Status | Description |
|---|---|---|---|
| `POST` | `/v1/forecast/univariate` | **Live** | Single series forecast |
| `POST` | `/v1/forecast/batch` | **Live** | Multiple series at once (Pro/Ultra) |
| `POST` | `/v1/validate` | **Live** | Backtesting / cross-validation |
| `POST` | `/v1/forecast/multivariate` | Phase 3 | Forecast with covariates (TiDE) |
| `GET` | `/v1/models` | **Live** | List available models |
| `GET` | `/v1/usage` | **Live** | Credit usage and limits |
| `GET` | `/health` | **Live** | Health check |

---

## Plans and Credits

| Plan | Price/month | Credits/month | Max horizon | Batch |
|---|---|---|---|---|
| Free | $0 | 500 | 30 | ❌ |
| Basic | $49 | 10,000 | 90 | ❌ |
| Pro | $199 | 50,000 | 365 | ✅ (50 series) |
| Ultra | $499 | 200,000 | 365 | ✅ (500 series) |

---

## Prerequisites

- Docker + Docker Compose
- Python 3.11+ (for local development without Docker)

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Listen port |
| `DEBUG` | `false` | Enable debug mode |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `CACHE_TTL_SECONDS` | `900` | Result cache duration (15 min) |
| `USE_MODAL` | `false` | Enable Modal.com GPU inference |
| `ENVIRONMENT` | `development` | `production` enforces proxy secret |
| `SENTRY_DSN` | `` | Sentry error tracking (optional) |

---

## Example — Python

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/forecast/univariate",
    headers={"X-Plan": "free"},
    json={
        "series": [100, 102, 98, 105, 103, 107, 104, 109, 106, 111],
        "horizon": 7,
        "frequency": "D",
        "model": "auto",
    },
)
data = response.json()
print(data["forecast"]["mean"])
# [112.3, 113.1, 112.8, 114.2, 113.9, 115.1, 114.7]
```

---

## Running Tests

```bash
# With Docker (recommended)
docker compose run --rm api pytest tests/ -v

# Local (requires Python 3.11+)
pip install -r requirements.txt
pytest tests/ -v
```

---

## Development (without Docker)

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set REDIS_URL=redis://localhost:6379/0 and start Redis locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: `http://localhost:8000/docs`

---

## Project Structure

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
