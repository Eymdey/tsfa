# Tutorial 2: Batch Forecasting for Inventory Planning

---

## Use Case

A retailer needs weekly demand forecasts for 50 products every Monday morning. Sending 50 individual
requests wastes rate limit quota and adds latency. The `/v1/forecast/batch` endpoint processes all
series concurrently and returns results in a single response.

---

## Requirements

- **PRO plan or higher** (BASIC plan does not support batch)
- PRO plan: up to 50 series per batch request
- ULTRA/MEGA plan: up to 500 series per batch request

---

## Full Python Example

```python
import requests
import random

RAPIDAPI_KEY = "your-rapidapi-key-here"
url = "https://tsfa.p.rapidapi.com/v1/forecast/batch"
headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "Content-Type": "application/json",
}

# --- Generate synthetic weekly demand data for 10 products ---
random.seed(42)

def generate_demand(base, n=52):
    """52 weeks of synthetic demand with trend and noise."""
    return [
        round(base + i * 0.5 + random.gauss(0, base * 0.05))
        for i in range(n)
    ]

series_list = [
    {
        "id": f"product_{i:03d}",
        "values": generate_demand(base=100 + i * 20),
        "horizon": 4,  # Forecast 4 weeks ahead
    }
    for i in range(10)
]

payload = {
    "series_list": series_list,
    "frequency": "W",    # Weekly data
    "model": "auto",
    "confidence_levels": [0.8, 0.95],
}

response = requests.post(url, json=payload, headers=headers)
response.raise_for_status()
data = response.json()

# --- Display results ---
print(f"Total credits used: {data['total_credits_used']}")
print(f"Processing time:    {data['processing_time_ms']:.0f} ms")
print()

for result in data["results"]:
    if result["status"] == "success":
        mean = [round(v, 1) for v in result["forecast"]["mean"]]
        print(f"{result['id']} | model={result['model_used']} | forecast={mean}")
    else:
        print(f"{result['id']} | ERROR: {result['error']}")
```

---

## Handling Partial Errors

The batch endpoint is designed to never fail completely. If one series is malformed (e.g., too short,
contains NaN), only that series returns `status: "error"`. The rest still succeed.

```python
successes = [r for r in data["results"] if r["status"] == "success"]
failures  = [r for r in data["results"] if r["status"] == "error"]

print(f"{len(successes)} succeeded, {len(failures)} failed")

for f in failures:
    print(f"  {f['id']}: {f['error']}")
```

Common per-series failure reasons:
- Series has fewer than 10 observations (minimum required)
- Series contains NaN or infinite values
- Horizon exceeds 365

---

## Cost Calculation

Credit cost for a batch call = `N_series × credits_per_model`

| Model | Credits/series | 10 series | 50 series |
|---|---|---|---|
| `arima` or `chronos` | 1 | 10 credits | 50 credits |
| `lstm` | 2 | 20 credits | 100 credits |
| `ensemble` | 5 | 50 credits | 250 credits |

**Example:** 50 products weekly with `auto` (selects ARIMA) = 50 credits/week = 200 credits/month.
On the PRO plan (10,000 credits/month), that leaves 9,800 credits for other calls.

The total is also returned in the response:
```python
print(data["total_credits_used"])  # e.g., 10
```
