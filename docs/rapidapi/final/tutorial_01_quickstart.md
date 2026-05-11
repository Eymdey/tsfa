# Tutorial 1: Your First Forecast in 5 Minutes

---

## Prerequisites

- A RapidAPI account (free)
- Python 3.8+ with `requests` installed (`pip install requests`)
- No ML knowledge required

---

## Step 1: Subscribe to TSFA on RapidAPI

1. Go to the TSFA listing on RapidAPI Hub (workspace: **dorianmrt**)
2. Click **Subscribe to Test** — choose the BASIC plan (free, no credit card)
3. Copy your `X-RapidAPI-Key` from the dashboard

---

## Step 2: Make Your First API Call

```python
import requests

# Replace with your key from the RapidAPI dashboard
RAPIDAPI_KEY = "your-rapidapi-key-here"

url = "https://tsfa.p.rapidapi.com/v1/forecast/univariate"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,        # Your RapidAPI key
    "Content-Type": "application/json",    # Always required
}

payload = {
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,       # Forecast 7 days ahead
    "frequency": "D",   # Daily data
    "model": "auto",    # Let the API choose the best model
}

response = requests.post(url, json=payload, headers=headers)
response.raise_for_status()  # Raises an exception on 4xx/5xx errors

data = response.json()
print(data)
```

---

## Step 3: Understand the Response

```json
{
  "status": "success",
  "model_used": "arima",
  "forecast": {
    "timestamps": ["2024-01-13", "2024-01-14", "2024-01-15", "..."],
    "mean":      [178.2, 181.5, 184.8, 188.1, 191.4, 194.7, 198.0],
    "lower_80":  [171.0, 173.5, 176.0, 178.5, 181.0, 183.5, 186.0],
    "upper_80":  [185.4, 189.5, 193.6, 197.7, 201.8, 205.9, 210.0],
    "lower_95":  [164.5, 166.8, 169.2, 171.5, 173.9, 176.2, 178.6],
    "upper_95":  [191.9, 196.2, 200.4, 204.7, 208.9, 213.2, 217.4]
  },
  "diagnostics": {
    "trend": "upward",               // "upward", "downward", or "stable"
    "seasonality_detected": false,   // true if a seasonal pattern was found
    "seasonality_period": null,      // e.g., 7 for weekly seasonality
    "series_length": 12,             // number of observations you sent
    "missing_values": 0,             // NaN count (must be 0 — clean your data first)
    "stationarity": "non_stationary" // ADF test result
  },
  "meta": {
    "inference_time_ms": 234.0,  // How long inference took
    "request_id": "req_abc123",  // Use this in bug reports
    "credits_used": 1            // Credits deducted from your plan
  }
}
```

Key fields to read:
- `forecast.mean` — your point forecast (use this for planning)
- `forecast.lower_95` / `upper_95` — 95% prediction interval (use for safety stock, worst-case scenarios)
- `model_used` — which model the API selected when you passed `"model": "auto"`
- `meta.credits_used` — deducted from your monthly quota

---

## Step 4: Choose the Right Model

| Your data | Recommended model | Why |
|---|---|---|
| Short series (< 100 obs) | `arima` | Robust on small samples, no GPU needed |
| General / mixed | `auto` or `chronos` | Chronos is zero-shot, works on any domain |
| Long series (> 500 obs) with seasonality | `lstm` | Benefits from deep patterns in long histories |
| Need maximum accuracy | `ensemble` | Combines models (costs 5 credits/call) |

Pass the model explicitly to avoid ambiguity:
```python
payload = {"series": [...], "horizon": 30, "frequency": "M", "model": "arima"}
```

---

## Next Steps

- **Tutorial 2** — Forecast 50 products simultaneously with `/v1/forecast/batch`
- **Tutorial 3** — Validate your model before deploying with `/v1/validate`
- Check `/v1/usage` to monitor your remaining credits:
  ```python
  resp = requests.get("https://tsfa.p.rapidapi.com/v1/usage", headers=headers)
  print(resp.json())  # credits_used, credits_remaining, period
  ```
