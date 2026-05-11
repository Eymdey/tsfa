"""Create Jupyter notebooks for the TSFA use cases."""
import nbformat as nbf
import os

OUTPUT_DIR = os.path.dirname(__file__)


def make_notebook(title, cells):
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.0"},
    }
    nb["cells"] = cells
    return nb


# ── Notebook 1: Retail Demand Forecasting ─────────────────────────────────────

nb1_cells = [
    nbf.v4.new_markdown_cell("""# Forecast Product Demand with 3 Lines of Code

**Use Case:** E-commerce demand forecasting for inventory optimization
**Dataset:** 6 months of synthetic daily sales with weekly seasonality
**API Plan:** Free tier (works with 500 credits/month)

This notebook shows how to use TSFA to predict the next 14 days of retail demand and compute a stock planning range from the 95% confidence interval.
"""),

    nbf.v4.new_code_cell("""# Install dependencies (if needed)
# !pip install requests matplotlib

import requests
import matplotlib.pyplot as plt
import random

BASE_URL = "http://localhost:8000/v1"
HEADERS = {"Content-Type": "application/json", "X-Plan": "free"}
"""),

    nbf.v4.new_markdown_cell("## Step 1 — Generate Realistic Sales Data\n\nIn production, replace this with: `pd.read_csv('your_sales_data.csv')['sales'].tolist()`"),

    nbf.v4.new_code_cell("""def generate_retail_series(n=180, seed=42):
    \"\"\"6 months of daily sales: trend + weekly seasonality + noise.\"\"\"
    rng = random.Random(seed)
    base = 100.0
    values = []
    for i in range(n):
        trend = base * (1 + 0.005 / 7) ** i        # +0.5%/week growth
        weekday = i % 7
        seasonal = 1.35 if weekday in (4, 5) else (0.85 if weekday == 6 else 1.0)
        noise = rng.gauss(0, base * 0.04)
        values.append(round(max(0, trend * seasonal + noise), 1))
    return values

series = generate_retail_series()
print(f"Series: {len(series)} days of data")
print(f"Range: {min(series):.0f} – {max(series):.0f} units/day")
print(f"Last 7 days: {series[-7:]}")
"""),

    nbf.v4.new_markdown_cell("## Step 2 — Call TSFA API (3 lines of code)"),

    nbf.v4.new_code_cell("""# ── 3 lines of code ──────────────────────────────────────────────
response = requests.post(f"{BASE_URL}/forecast/univariate", headers=HEADERS,
    json={"series": series, "horizon": 14, "frequency": "D", "model": "auto",
          "confidence_levels": [0.8, 0.95]})
data = response.json()
# ─────────────────────────────────────────────────────────────────

print(f"Model used   : {data['model_used']}")
print(f"Inference    : {data['meta']['inference_time_ms']}ms")
print(f"Trend        : {data['diagnostics']['trend']}")
print(f"Forecast mean (first 7 days): {[round(v,1) for v in data['forecast']['mean'][:7]]}")
"""),

    nbf.v4.new_markdown_cell("## Step 3 — Visualize Historical Data + Forecast"),

    nbf.v4.new_code_cell("""mean  = data["forecast"]["mean"]
l80   = data["forecast"]["lower_80"]
u80   = data["forecast"]["upper_80"]
l95   = data["forecast"]["lower_95"]
u95   = data["forecast"]["upper_95"]

fig, ax = plt.subplots(figsize=(12, 5))
fig.patch.set_facecolor("white")

hist_x  = list(range(len(series)))
fore_x  = list(range(len(series) - 1, len(series) + len(mean)))
fore_mean = [series[-1]] + mean
fore_l80 = [series[-1]] + l80;  fore_u80 = [series[-1]] + u80
fore_l95 = [series[-1]] + l95;  fore_u95 = [series[-1]] + u95

ax.fill_between(fore_x, fore_l95, fore_u95, alpha=0.15, color="gray", label="95% CI")
ax.fill_between(fore_x, fore_l80, fore_u80, alpha=0.25, color="gray", label="80% CI")
ax.plot(hist_x, series, color="#2196F3", linewidth=1.5, label="Historical")
ax.plot(fore_x, fore_mean, color="#FF9800", linewidth=2.5, linestyle="--", label="Forecast (14 days)")

ax.set_title("Retail Demand Forecast — 14-Day Ahead", fontsize=13, fontweight="bold")
ax.set_xlabel("Day"); ax.set_ylabel("Units sold")
ax.legend(loc="upper left"); ax.grid(True, alpha=0.3)
ax.set_facecolor("white")
plt.tight_layout()
plt.savefig("outputs/01_retail_forecast.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
"""),

    nbf.v4.new_markdown_cell("## Step 4 — Business Insight: Stock Planning Range"),

    nbf.v4.new_code_cell("""lower_plan = round(min(l95))
upper_plan = round(max(u95))
peak_day   = mean.index(max(mean)) + 1
avg_demand = round(sum(mean) / len(mean), 1)

print("=" * 55)
print("Stock Planning Recommendation (next 14 days)")
print("=" * 55)
print(f"Expected average demand : {avg_demand} units/day")
print(f"Peak demand day         : Day {peak_day} ({round(max(mean), 1)} units)")
print()
print(f"With 95% confidence interval:")
print(f"  Plan stock between {lower_plan} and {upper_plan} units total")
print(f"  (covering the full 14-day forecast horizon)")
print()
print(f"Recommended safety stock: {upper_plan - round(sum(mean))} units")
"""),
]

nb1 = make_notebook("Retail Demand Forecasting", nb1_cells)
path1 = os.path.join(OUTPUT_DIR, "01_retail_demand_forecasting.ipynb")
nbf.write(nb1, path1)
print(f"Created: {path1}")


# ── Notebook 2: Financial Trend Forecasting ────────────────────────────────────

nb2_cells = [
    nbf.v4.new_markdown_cell("""# Forecast Currency Exchange Rates for Risk Management

**Use Case:** EUR/USD exchange rate forecasting for risk management
**Dataset:** Real exchange rate data from benchmark cache (or synthetic fallback)
**API Plan:** Pro (uses auto model selection)

This notebook forecasts EUR/USD 30 days ahead and computes a risk probability band.
"""),

    nbf.v4.new_code_cell("""import os, gzip, requests, random
import matplotlib.pyplot as plt

BASE_URL = "http://localhost:8000/v1"
HEADERS = {"Content-Type": "application/json", "X-Plan": "pro"}

def load_or_generate_exchange_rate():
    cache = os.path.join("..", "..", "benchmarks", ".cache", "exchange_rate.txt.gz")
    try:
        import pandas as pd
        with gzip.open(cache, "rt") as f:
            df = pd.read_csv(f, header=None, sep=",")
        series = df.iloc[:, 0].values[-200:].tolist()
        print("Loaded real Exchange Rate data.")
        return [round(float(v), 5) for v in series]
    except Exception:
        print("Generating synthetic EUR/USD series.")
        rng = random.Random(7)
        s = [1.0800]
        for _ in range(199):
            s.append(round(s[-1] * (1 + rng.gauss(0, 0.003)), 5))
        return s

series = load_or_generate_exchange_rate()
print(f"Series length: {len(series)} trading days")
print(f"Current rate: {series[-1]:.5f}")
"""),

    nbf.v4.new_markdown_cell("## Step 1 — Forecast with Auto Model Selection"),

    nbf.v4.new_code_cell("""response = requests.post(f"{BASE_URL}/forecast/univariate", headers=HEADERS,
    json={"series": series, "horizon": 30, "frequency": "D", "model": "auto",
          "confidence_levels": [0.8, 0.95]})
data = response.json()

print(f"Model selected : {data['model_used']}")
print(f"Fallback used  : {data['meta']['fallback_used']} ({data['meta']['fallback_reason']})")
print(f"Inference      : {data['meta']['inference_time_ms']}ms")
mean = data["forecast"]["mean"]
l95  = data["forecast"]["lower_95"]
u95  = data["forecast"]["upper_95"]
print(f"30-day forecast range: {min(mean):.5f} – {max(mean):.5f}")
"""),

    nbf.v4.new_markdown_cell("## Step 2 — Visualize with 95% Confidence Band"),

    nbf.v4.new_code_cell("""n = len(series)
fig, ax = plt.subplots(figsize=(12, 5))
fig.patch.set_facecolor("white")

trim = max(0, n - 60)
hist_x = list(range(trim, n))
fore_x = list(range(n - 1, n + 30))
fore_mean = [series[-1]] + mean
fore_l95 = [series[-1]] + l95
fore_u95 = [series[-1]] + u95

ax.fill_between(fore_x, fore_l95, fore_u95, alpha=0.2, color="gray", label="95% CI")
ax.plot(hist_x, series[trim:], color="#2196F3", linewidth=1.5, label="Historical (last 60 days)")
ax.plot(fore_x, fore_mean, color="#FF9800", linewidth=2.5, linestyle="--",
        label=f"Forecast (30 days) — {data['model_used'].upper()}")

ax.set_title("EUR/USD Exchange Rate — 30-Day Forecast", fontsize=13, fontweight="bold")
ax.set_xlabel("Trading Day"); ax.set_ylabel("Exchange Rate")
ax.legend(loc="upper left"); ax.grid(True, alpha=0.3)
ax.set_facecolor("white")
plt.tight_layout()
plt.savefig("outputs/02_financial_forecast.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
"""),

    nbf.v4.new_markdown_cell("## Step 3 — Risk Management Insight"),

    nbf.v4.new_code_cell("""lo = round(min(l95), 5)
hi = round(max(u95), 5)
current = series[-1]
worst_loss = round((current - lo) / current * 100, 2)
best_gain  = round((hi - current) / current * 100, 2)

print("=" * 50)
print("Risk Management Summary (next 30 trading days)")
print("=" * 50)
print(f"Current rate     : {current:.5f}")
print(f"Forecast range   : {min(mean):.5f} – {max(mean):.5f}")
print()
print(f"95% probability: rate stays between {lo:.5f} and {hi:.5f}")
print(f"  Downside risk  : -{worst_loss}% vs. current")
print(f"  Upside chance  : +{best_gain}% vs. current")
print()
print("Recommendation: hedge positions with max {:.0f}% downside buffer.".format(worst_loss * 1.2))
"""),
]

nb2 = make_notebook("Financial Trend Forecasting", nb2_cells)
path2 = os.path.join(OUTPUT_DIR, "02_financial_trend_forecasting.ipynb")
nbf.write(nb2, path2)
print(f"Created: {path2}")


# ── Notebook 3: Energy Consumption Forecasting ────────────────────────────────

nb3_cells = [
    nbf.v4.new_markdown_cell("""# Predict Energy Consumption for Smart Grid Optimization

**Use Case:** 48-hour-ahead energy consumption forecasting
**Dataset:** ETT-h1 (Electricity Transformer Temperature) — real hourly data
**API Plan:** Pro

This notebook forecasts 48 hours of energy load and validates accuracy with backtest.
"""),

    nbf.v4.new_code_cell("""import os, math, random, requests
import matplotlib.pyplot as plt

BASE_URL = "http://localhost:8000/v1"
HEADERS = {"Content-Type": "application/json", "X-Plan": "pro"}

def load_energy_series():
    cache = os.path.join("..", "..", "benchmarks", ".cache", "ETTh1.csv")
    try:
        import pandas as pd
        df = pd.read_csv(cache)
        series = df["OT"].values[-720:].tolist()
        print("Loaded real ETT-h1 data (last 720 hours = 30 days).")
        return [round(float(v), 4) for v in series]
    except Exception:
        print("Generating synthetic hourly energy series (720 points).")
        rng = random.Random(13)
        series = []
        for i in range(720):
            hour = i % 24
            day = (i // 24) % 7
            base = 8.0
            daily = 2.5 * math.sin(2 * math.pi * hour / 24 - math.pi / 2)
            weekly = 1.0 if day < 5 else -0.5
            noise = rng.gauss(0, 0.3)
            series.append(round(base + daily + weekly + noise, 4))
        return series

series = load_energy_series()
print(f"Series: {len(series)} hourly observations")
print(f"Range: {min(series):.2f} – {max(series):.2f}")
"""),

    nbf.v4.new_markdown_cell("## Step 1 — Forecast 48 Hours Ahead"),

    nbf.v4.new_code_cell("""response = requests.post(f"{BASE_URL}/forecast/univariate", headers=HEADERS,
    json={"series": series, "horizon": 48, "frequency": "H", "model": "arima",
          "confidence_levels": [0.8, 0.95]})
data = response.json()

mean = data["forecast"]["mean"]
l80  = data["forecast"]["lower_80"]
u80  = data["forecast"]["upper_80"]
l95  = data["forecast"]["lower_95"]
u95  = data["forecast"]["upper_95"]

print(f"Model    : {data['model_used']}")
print(f"Inference: {data['meta']['inference_time_ms']}ms")
print(f"48h forecast: min={min(mean):.2f}, max={max(mean):.2f}, avg={sum(mean)/len(mean):.2f}")
"""),

    nbf.v4.new_markdown_cell("## Step 2 — Hourly Visualization"),

    nbf.v4.new_code_cell("""n = len(series)
hist_show = min(72, n)
trim = n - hist_show

fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor("white")

hist_x = list(range(trim, n))
fore_x = list(range(n - 1, n + 48))
fore_mean = [series[-1]] + mean
fore_l80 = [series[-1]] + l80;  fore_u80 = [series[-1]] + u80
fore_l95 = [series[-1]] + l95;  fore_u95 = [series[-1]] + u95

ax.fill_between(fore_x, fore_l95, fore_u95, alpha=0.12, color="gray", label="95% CI")
ax.fill_between(fore_x, fore_l80, fore_u80, alpha=0.22, color="gray", label="80% CI")
ax.plot(hist_x, series[trim:], color="#2196F3", linewidth=1.5, label="Historical (last 72h)")
ax.plot(fore_x, fore_mean, color="#FF9800", linewidth=2.5, linestyle="--", label="Forecast (48h)")
ax.axvline(x=n - 1, color="#888", linewidth=1, linestyle=":", label="Forecast start")

ax.set_title("Energy Consumption — 48h Ahead Forecast", fontsize=13, fontweight="bold")
ax.set_xlabel("Hour Index"); ax.set_ylabel("Temperature / Load (°C or MW)")
ax.legend(loc="upper right"); ax.grid(True, alpha=0.3)
ax.set_facecolor("white")
plt.tight_layout()
plt.savefig("outputs/03_energy_forecast.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
"""),

    nbf.v4.new_markdown_cell("## Step 3 — Validate with Backtesting"),

    nbf.v4.new_code_cell("""val_response = requests.post(f"{BASE_URL}/validate", headers=HEADERS,
    json={"series": series[:500], "horizon": 24, "frequency": "H",
          "model": "arima", "n_windows": 3})
val = val_response.json()

metrics = val["backtest_metrics"]
print("=" * 50)
print("Backtest Results (3-window cross-validation)")
print("=" * 50)
print(f"MAE           : {metrics['mae']:.4f}")
print(f"RMSE          : {metrics['rmse']:.4f}")
print(f"MAPE          : {metrics['mape'] * 100:.2f}%")
print(f"Coverage 80%  : {metrics['coverage_80'] * 100:.1f}% (target ≥ 80%)")
print(f"Coverage 95%  : {metrics['coverage_95'] * 100:.1f}% (target ≥ 95%)")
print()
print(f"TSFA achieves {metrics['mape'] * 100:.1f}% MAPE on energy data ✅")
"""),
]

nb3 = make_notebook("Energy Consumption Forecasting", nb3_cells)
path3 = os.path.join(OUTPUT_DIR, "03_energy_consumption_forecasting.ipynb")
nbf.write(nb3, path3)
print(f"Created: {path3}")

print("\nAll notebooks created successfully.")
