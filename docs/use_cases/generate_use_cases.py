"""
Generate use case notebooks and PNG outputs for TSFA.
Run from the project root: python docs/use_cases/generate_use_cases.py
"""

import os
import sys
import json
import random
import math
import time
import requests

# ── Setup ──────────────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000/v1"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROXY_SECRET = ""
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
try:
    with open(env_path) as f:
        for line in f:
            if line.startswith("RAPIDAPI_PROXY_SECRET="):
                PROXY_SECRET = line.strip().split("=", 1)[1]
                break
except FileNotFoundError:
    pass

HEADERS = {
    "Content-Type": "application/json",
    "X-Plan": "pro",
    "X-RapidAPI-Proxy-Secret": PROXY_SECRET,
}


def call_api(series, horizon, model="auto", frequency="D"):
    """Call the TSFA API and return the response dict."""
    payload = {
        "series": series,
        "horizon": horizon,
        "frequency": frequency,
        "model": model,
        "confidence_levels": [0.8, 0.95],
    }
    resp = requests.post(
        f"{BASE_URL}/forecast/univariate",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ── Use Case 1: Retail Demand Forecasting ─────────────────────────────────────

def generate_retail_series(n=180, seed=42):
    """Simulate 6 months of daily retail sales with trend + weekly seasonality + noise."""
    rng = random.Random(seed)
    base = 100.0
    values = []
    for i in range(n):
        trend = base * (1 + 0.005 / 7) ** i          # +0.5%/week
        weekday = i % 7
        seasonal = 1.35 if weekday in (4, 5) else (0.85 if weekday == 6 else 1.0)
        noise = rng.gauss(0, base * 0.04)
        values.append(round(max(0, trend * seasonal + noise), 1))
    return values


def use_case_1():
    print("\n[Use Case 1] Retail Demand Forecasting...")
    series = generate_retail_series()
    data = call_api(series, horizon=14, model="auto", frequency="D")
    model_used = data["model_used"]
    mean = data["forecast"]["mean"]
    l80 = data["forecast"]["lower_80"]
    u80 = data["forecast"]["upper_80"]
    l95 = data["forecast"]["lower_95"]
    u95 = data["forecast"]["upper_95"]
    inference_ms = data["meta"]["inference_time_ms"]

    # Plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("white")

    hist_x = list(range(len(series)))
    fore_x = list(range(len(series) - 1, len(series) + len(mean)))
    fore_series = [series[-1]] + mean
    fore_l80 = [series[-1]] + l80
    fore_u80 = [series[-1]] + u80
    fore_l95 = [series[-1]] + l95
    fore_u95 = [series[-1]] + u95

    ax.fill_between(fore_x, fore_l95, fore_u95, alpha=0.15, color="gray", label="95% CI")
    ax.fill_between(fore_x, fore_l80, fore_u80, alpha=0.25, color="gray", label="80% CI")
    ax.plot(hist_x, series, color="#2196F3", linewidth=1.5, label="Historical")
    ax.plot(fore_x, fore_series, color="#FF9800", linewidth=2.5, linestyle="--", label="Forecast (14 days)")

    ax.set_title("Retail Demand Forecast — 14-Day Ahead\nModel: {} | Inference: {}ms".format(
        model_used.upper(), int(inference_ms)), fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Day")
    ax.set_ylabel("Units sold")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_facecolor("white")

    # Business insight annotation
    lower_plan = round(min(l95), 0)
    upper_plan = round(max(u95), 0)
    ax.annotate(
        f"Stock planning range:\n{int(lower_plan)}–{int(upper_plan)} units",
        xy=(len(series) + len(mean) - 1, mean[-1]),
        xytext=(len(series) + 2, max(u95) * 0.85),
        fontsize=9,
        color="#555",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF9C4", edgecolor="#FFC107"),
        arrowprops=dict(arrowstyle="->", color="#888"),
    )

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "01_retail_forecast.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Saved: {out_path}")
    print(f"  Model: {model_used} | Mean forecast: {[round(v,1) for v in mean[:3]]}...")
    print(f"  95% CI range: {int(lower_plan)}–{int(upper_plan)} units")
    return mean, l95, u95


# ── Use Case 2: Financial Trend Forecasting ────────────────────────────────────

def load_exchange_rate_series():
    """Load exchange rate series from benchmark cache, or generate synthetic fallback."""
    cache_path = os.path.join(os.path.dirname(__file__), "..", "..", "benchmarks", ".cache", "exchange_rate.txt.gz")
    try:
        import gzip
        import pandas as pd
        with gzip.open(cache_path, "rt") as f:
            df = pd.read_csv(f, header=None, sep=",")
        series = df.iloc[:, 0].values[-200:].tolist()
        print("  Loaded real Exchange Rate data from cache.")
        return [round(float(v), 5) for v in series]
    except Exception:
        print("  Exchange rate data not cached — generating synthetic EUR/USD series.")
        rng = random.Random(7)
        series = [1.0800]
        for _ in range(199):
            series.append(round(series[-1] * (1 + rng.gauss(0, 0.003)), 5))
        return series


def use_case_2():
    print("\n[Use Case 2] Financial Trend Forecasting (EUR/USD)...")
    series = load_exchange_rate_series()
    n = len(series)

    # Call with auto (should select Chronos; falls back to ARIMA here)
    data_auto = call_api(series, horizon=30, model="auto", frequency="D")
    # Also call with explicit arima for comparison
    data_arima = call_api(series, horizon=30, model="arima", frequency="D")

    model_used = data_auto["model_used"]
    mean_auto = data_auto["forecast"]["mean"]
    l95_auto = data_auto["forecast"]["lower_95"]
    u95_auto = data_auto["forecast"]["upper_95"]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("white")

    hist_x = list(range(n))
    fore_x = list(range(n - 1, n + 30))
    fore_mean = [series[-1]] + mean_auto
    fore_l95 = [series[-1]] + l95_auto
    fore_u95 = [series[-1]] + u95_auto

    # Show last 60 historical points only for readability
    trim = max(0, n - 60)
    ax.plot(hist_x[trim:], series[trim:], color="#2196F3", linewidth=1.5, label="Historical (last 60 days)")
    ax.fill_between(fore_x, fore_l95, fore_u95, alpha=0.2, color="gray", label="95% CI")
    ax.plot(fore_x, fore_mean, color="#FF9800", linewidth=2.5, linestyle="--", label=f"Forecast (30 days) — {model_used.upper()}")

    # 90% probability band annotation
    lo_band = round(min(l95_auto), 5)
    hi_band = round(max(u95_auto), 5)
    ax.axhline(lo_band, color="#E53935", linewidth=0.8, linestyle=":", alpha=0.7)
    ax.axhline(hi_band, color="#E53935", linewidth=0.8, linestyle=":", alpha=0.7)
    ax.annotate(
        f"95% probability band:\n{lo_band:.4f} – {hi_band:.4f}",
        xy=(n + 15, (lo_band + hi_band) / 2),
        fontsize=9, color="#E53935",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFEBEE", edgecolor="#E53935"),
    )

    inference_ms = data_auto["meta"]["inference_time_ms"]
    ax.set_title("EUR/USD Exchange Rate Forecast — 30-Day Ahead\nModel: {} | Inference: {}ms".format(
        model_used.upper(), int(inference_ms)), fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Trading Day")
    ax.set_ylabel("Exchange Rate")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_facecolor("white")

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "02_financial_forecast.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Saved: {out_path}")
    print(f"  Model: {model_used} | 95% CI: {lo_band:.4f}–{hi_band:.4f}")
    return mean_auto


# ── Use Case 3: Energy Consumption Forecasting ────────────────────────────────

def load_energy_series():
    """Load ETT-h1 OT column (oil temperature) or generate synthetic hourly energy series."""
    cache_path = os.path.join(os.path.dirname(__file__), "..", "..", "benchmarks", ".cache", "ETTh1.csv")
    try:
        import pandas as pd
        df = pd.read_csv(cache_path)
        # Use last 30 days = 720 hourly observations
        series = df["OT"].values[-720:].tolist()
        print("  Loaded real ETT-h1 data from cache.")
        return [round(float(v), 4) for v in series]
    except Exception:
        print("  ETT-h1 data not cached — generating synthetic hourly energy series.")
        rng = random.Random(13)
        series = []
        for i in range(720):
            hour = i % 24
            day = (i // 24) % 7
            base = 8.0
            daily = 2.5 * math.sin(2 * math.pi * hour / 24 - math.pi / 2)  # peak at noon
            weekly = 1.0 if day < 5 else -0.5  # weekday vs weekend
            noise = rng.gauss(0, 0.3)
            series.append(round(base + daily + weekly + noise, 4))
        return series


def use_case_3():
    print("\n[Use Case 3] Energy Consumption Forecasting (48h ahead)...")
    series = load_energy_series()
    horizon = 48

    data = call_api(series, horizon=horizon, model="arima", frequency="H")
    model_used = data["model_used"]
    mean = data["forecast"]["mean"]
    l80 = data["forecast"]["lower_80"]
    u80 = data["forecast"]["upper_80"]
    l95 = data["forecast"]["lower_95"]
    u95 = data["forecast"]["upper_95"]
    inference_ms = data["meta"]["inference_time_ms"]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("white")

    # Show last 72h historical
    hist_show = min(72, len(series))
    trim = len(series) - hist_show
    hist_x = list(range(trim, len(series)))
    fore_x = list(range(len(series) - 1, len(series) + horizon))
    fore_mean = [series[-1]] + mean
    fore_l80 = [series[-1]] + l80
    fore_u80 = [series[-1]] + u80
    fore_l95 = [series[-1]] + l95
    fore_u95 = [series[-1]] + u95

    ax.fill_between(fore_x, fore_l95, fore_u95, alpha=0.12, color="gray", label="95% CI")
    ax.fill_between(fore_x, fore_l80, fore_u80, alpha=0.22, color="gray", label="80% CI")
    ax.plot(hist_x, series[trim:], color="#2196F3", linewidth=1.5, label="Historical (last 72h)")
    ax.plot(fore_x, fore_mean, color="#FF9800", linewidth=2.5, linestyle="--", label="Forecast (48h)")

    ax.axvline(x=len(series) - 1, color="#888", linewidth=1, linestyle=":")

    ax.set_title("Energy Consumption Forecast — 48h Ahead\nModel: {} | Inference: {}ms".format(
        model_used.upper(), int(inference_ms)), fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Hour")
    ax.set_ylabel("Temperature / Load (°C or MW)")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_facecolor("white")

    # Metrics from backtest
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "03_energy_forecast.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Saved: {out_path}")
    print(f"  Model: {model_used} | 48h mean forecast range: {round(min(mean),2)}–{round(max(mean),2)}")
    return mean


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("TSFA Use Case Generator")
    print("=" * 65)

    try:
        r1 = use_case_1()
        r2 = use_case_2()
        r3 = use_case_3()

        print("\n" + "=" * 65)
        print("All use cases generated successfully.")
        print(f"PNG outputs saved to: {OUTPUT_DIR}/")
        print("  - 01_retail_forecast.png")
        print("  - 02_financial_forecast.png")
        print("  - 03_energy_forecast.png")

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API at http://localhost:8000")
        print("Make sure the API is running: docker compose up")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
