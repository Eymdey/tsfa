"""
TSFA Python Example
===================

Complete example demonstrating how to use the TSFA API from Python.
Covers: basic forecast, custom frequency, confidence intervals, and
reading diagnostic information.

Requirements:
    pip install requests

Usage:
    python docs/examples/python_example.py
"""

import json
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000/v1"

# In production, replace with your RapidAPI key header:
# HEADERS = {"X-RapidAPI-Key": "your-key-here", "Content-Type": "application/json"}
HEADERS = {
    "Content-Type": "application/json",
    "X-Plan": "free",  # local dev header
}


# ---------------------------------------------------------------------------
# Example 1: Basic daily forecast
# ---------------------------------------------------------------------------

def example_basic_forecast():
    """Forecast 7 days ahead from 12 historical daily observations."""
    print("=" * 60)
    print("Example 1: Basic daily forecast")
    print("=" * 60)

    payload = {
        "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
        "horizon": 7,
        "frequency": "D",
        "model": "auto",
    }

    response = requests.post(f"{BASE_URL}/forecast/univariate", json=payload, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    print(f"Status       : {data['status']}")
    print(f"Model used   : {data['model_used']}")
    print(f"Forecast mean: {data['forecast']['mean']}")
    print(f"95% lower    : {data['forecast']['lower_95']}")
    print(f"95% upper    : {data['forecast']['upper_95']}")
    print()
    print(f"Trend        : {data['diagnostics']['trend']}")
    print(f"Stationarity : {data['diagnostics']['stationarity']}")
    print(f"Series length: {data['diagnostics']['series_length']}")
    print()
    print(f"Inference time: {data['meta']['inference_time_ms']} ms")
    print(f"Request ID   : {data['meta']['request_id']}")
    print(f"Credits used : {data['meta']['credits_used']}")
    print()

    return data


# ---------------------------------------------------------------------------
# Example 2: Monthly sales forecast with custom confidence levels
# ---------------------------------------------------------------------------

def example_monthly_forecast():
    """Forecast 12 months of monthly sales data with 90% and 99% intervals."""
    print("=" * 60)
    print("Example 2: Monthly sales forecast")
    print("=" * 60)

    # 24 months of synthetic sales data with upward trend and noise
    monthly_sales = [
        1200, 1150, 1320, 1180, 1400, 1350, 1500, 1450, 1600, 1550, 1700, 1650,
        1800, 1750, 1900, 1850, 2000, 1950, 2100, 2050, 2200, 2150, 2300, 2250,
    ]

    payload = {
        "series": monthly_sales,
        "horizon": 12,
        "frequency": "M",
        "model": "auto",
        "confidence_levels": [0.90, 0.99],
    }

    response = requests.post(f"{BASE_URL}/forecast/univariate", json=payload, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    print(f"Model used   : {data['model_used']}")
    print(f"Forecast mean: {[round(v, 1) for v in data['forecast']['mean']]}")
    print()
    diag = data["diagnostics"]
    print(f"Trend         : {diag['trend']}")
    print(f"Seasonality   : detected={diag['seasonality_detected']}, "
          f"period={diag['seasonality_period']}")
    print(f"Stationarity  : {diag['stationarity']}")
    print()

    return data


# ---------------------------------------------------------------------------
# Example 3: Weekly e-commerce transactions with timestamps
# ---------------------------------------------------------------------------

def example_with_timestamps():
    """Forecast using explicit timestamps for proper date labelling."""
    print("=" * 60)
    print("Example 3: Weekly transactions with timestamps")
    print("=" * 60)

    timestamps = [
        "2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22", "2024-01-29",
        "2024-02-05", "2024-02-12", "2024-02-19", "2024-02-26", "2024-03-04",
        "2024-03-11", "2024-03-18",
    ]
    values = [450, 480, 520, 490, 510, 540, 560, 530, 570, 590, 610, 580]

    payload = {
        "series": values,
        "timestamps": timestamps,
        "horizon": 4,
        "frequency": "W",
        "model": "auto",
    }

    response = requests.post(f"{BASE_URL}/forecast/univariate", json=payload, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    print("Forecast:")
    for ts, mean, lo, hi in zip(
        data["forecast"]["timestamps"],
        data["forecast"]["mean"],
        data["forecast"]["lower_95"],
        data["forecast"]["upper_95"],
    ):
        print(f"  {ts}: {mean:.1f}  [{lo:.1f}, {hi:.1f}]")
    print()

    return data


# ---------------------------------------------------------------------------
# Example 4: List available models
# ---------------------------------------------------------------------------

def example_list_models():
    """List all models and their availability status."""
    print("=" * 60)
    print("Example 4: Available models")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/models", headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    for model in data["models"]:
        status = "AVAILABLE" if model["available"] else "Phase 2"
        print(f"  [{status:9s}] {model['id']:10s} | {model['name']}")
    print()

    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\nTSFA Python Client Examples\n")

    try:
        example_basic_forecast()
        example_monthly_forecast()
        example_with_timestamps()
        example_list_models()
        print("All examples completed successfully.")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API.")
        print("Make sure the API is running: docker compose up")
    except requests.exceptions.HTTPError as exc:
        print(f"HTTP error: {exc}")
        print(exc.response.text)
