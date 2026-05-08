# Quickstart — TSFA in 5 minutes

Get your first forecast in under 5 minutes.

---

## 1. Start the API

```bash
git clone https://github.com/youruser/tsfa.git
cd tsfa
cp .env.example .env
docker compose up --build
```

Wait for the containers to start. You should see:

```
tsfa-api-1    | INFO: Uvicorn running on http://0.0.0.0:8000
tsfa-redis-1  | Ready to accept connections
```

---

## 2. Check the health endpoint

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "version": "1.0.0"}
```

---

## 3. Make your first forecast

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

The response will include:
- `forecast.mean` — 7 daily point forecasts
- `forecast.lower_95` / `forecast.upper_95` — 95% prediction intervals
- `diagnostics` — trend, seasonality, stationarity info
- `meta.inference_time_ms` — how long it took

---

## 4. Explore the interactive docs

Open your browser at `http://localhost:8000/docs` for the full Swagger UI.

---

## 5. Key parameters

| Parameter | Required | Description |
|---|---|---|
| `series` | Yes | Array of float values (min 10, max 50,000) |
| `horizon` | Yes | Steps to forecast (1–365) |
| `frequency` | No | `"D"`, `"H"`, `"W"`, `"M"`, `"auto"` |
| `model` | No | `"auto"` uses AutoARIMA in Phase 1 |
| `confidence_levels` | No | Default: `[0.8, 0.95]` |

---

## 6. Python client example

```python
import requests

API_URL = "http://localhost:8000/v1/forecast/univariate"

response = requests.post(
    API_URL,
    headers={"X-Plan": "free"},
    json={
        "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
        "horizon": 7,
        "frequency": "D",
        "model": "auto",
    },
)

data = response.json()
print("Forecast mean:", data["forecast"]["mean"])
print("Trend:", data["diagnostics"]["trend"])
print("Inference time:", data["meta"]["inference_time_ms"], "ms")
```

---

## Next steps

- See `docs/examples/` for more complete examples in Python, curl, and JavaScript
- Check `GET /v1/models` to see available models and Phase 2 roadmap
- Read the full API reference at `/docs`
