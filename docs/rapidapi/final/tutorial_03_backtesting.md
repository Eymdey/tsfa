# Tutorial 3: Backtesting — Validate Before You Commit

---

## Why Backtest?

Choosing a forecasting model without validating it on your own data is a gamble. The `/v1/validate`
endpoint runs sliding-window cross-validation on your historical data and returns accuracy metrics
and calibration scores. Use this before committing to a model in production.

---

## The Sliding Window Method

The validator splits your series into multiple train/test windows and measures forecast error on each:

```
Full series: [===========================]

Window 1:  [train=====][test=horizon]
Window 2:     [train=====][test=horizon]
Window 3:        [train=====][test=horizon]
```

Each window produces MAE, RMSE, MAPE, and prediction interval coverage. The aggregate metrics
are the average across all windows.

---

## Full Example

```python
import requests

RAPIDAPI_KEY = "your-rapidapi-key-here"
url = "https://tsfa.p.rapidapi.com/v1/validate"
headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "Content-Type": "application/json",
}

# 52 weeks of weekly sales data
weekly_sales = [
    450, 480, 520, 490, 510, 540, 560, 530, 570, 590, 610, 580,
    620, 600, 650, 630, 670, 645, 690, 660, 700, 720, 710, 695,
    730, 750, 740, 760, 780, 770, 800, 810, 795, 820, 840, 830,
    860, 850, 870, 890, 880, 910, 900, 920, 940, 930, 950, 960,
    970, 980, 990, 1000,
]

payload = {
    "series": weekly_sales,
    "horizon": 4,        # Validate 4-week-ahead forecast accuracy
    "frequency": "W",
    "model": "arima",    # Test ARIMA specifically
    "n_windows": 5,      # Use 5 rolling windows
}

response = requests.post(url, json=payload, headers=headers)
response.raise_for_status()
data = response.json()

# --- Aggregate metrics ---
metrics = data["backtest_metrics"]
print(f"MAE:         {metrics['mae']:.4f}")
print(f"RMSE:        {metrics['rmse']:.4f}")
print(f"MAPE:        {metrics['mape']:.2f}%")
print(f"sMAPE:       {metrics['smape']:.2f}%")
print(f"Coverage 80%: {metrics['coverage_80']:.2%}")
print(f"Coverage 95%: {metrics['coverage_95']:.2%}")

# --- Decision rule ---
MAE_THRESHOLD = 50.0
if metrics["mae"] < MAE_THRESHOLD:
    print(f"\nModel accepted: MAE={metrics['mae']:.2f} < threshold={MAE_THRESHOLD}")
else:
    print(f"\nModel rejected: MAE={metrics['mae']:.2f} >= threshold={MAE_THRESHOLD}")
    print("Consider trying model='chronos' or increasing your training history.")
```

---

## Interpreting the Metrics

| Metric | What it measures | Good value (relative) |
|---|---|---|
| **MAE** | Average absolute error in your series' units | < 10% of mean series value |
| **RMSE** | Same as MAE but penalizes large errors more | Should be close to MAE (no large outliers) |
| **MAPE** | Percentage error — scale-independent | < 10% is generally good; < 5% is excellent |
| **coverage_80** | Fraction of actuals that fell inside the 80% interval | Should be close to 0.80 (calibrated intervals) |
| **coverage_95** | Fraction of actuals inside the 95% interval | Should be close to 0.95 |

**Coverage interpretation:** If `coverage_95` = 0.60, the model's confidence intervals are too
narrow — it is overconfident. If `coverage_95` = 0.99, intervals are too wide (conservative).
Well-calibrated intervals are a sign you can trust the uncertainty estimates.

**Credit cost for validation:** `n_windows × credits_per_model`. For 5 windows with ARIMA = 5 credits.
