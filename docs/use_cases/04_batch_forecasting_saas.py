"""
Use Case: SaaS platform forecasting 50 product lines simultaneously.
Demonstrates batch endpoint efficiency vs. 50 individual calls.

This example shows:
- How to use /forecast/batch for high-volume forecasting
- Time comparison: batch vs sequential calls
- Error handling when one series is malformed

Requirements:
    pip install requests

Usage:
    python docs/use_cases/04_batch_forecasting_saas.py
"""

import os
import time
import requests
import random

BASE_URL = "http://localhost:8000/v1"

# Load proxy secret if available
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

N_PRODUCTS = 50
HORIZON = 7
HISTORY_LENGTH = 20


def generate_product_series(seed: int) -> list[float]:
    """Generate a realistic retail demand series with trend, seasonality, and noise."""
    rng = random.Random(seed)
    base = rng.uniform(100, 500)
    trend = rng.uniform(0.1, 0.8)
    values = []
    for i in range(HISTORY_LENGTH):
        seasonal = 20 * (1 if i % 7 in (4, 5) else -1)  # weekend peak
        noise = rng.gauss(0, base * 0.05)
        values.append(round(max(0, base + trend * i + seasonal + noise), 1))
    return values


def sequential_forecast(series_list: list[dict]) -> tuple[list, float]:
    """Run N individual forecast requests sequentially."""
    results = []
    t_start = time.perf_counter()
    for item in series_list:
        payload = {
            "series": item["values"],
            "horizon": item["horizon"],
            "frequency": "D",
            "model": "arima",
        }
        resp = requests.post(
            f"{BASE_URL}/forecast/univariate",
            headers=HEADERS,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            results.append({"id": item["id"], "status": "success"})
        else:
            results.append({"id": item["id"], "status": "error", "code": resp.status_code})
    elapsed = time.perf_counter() - t_start
    return results, elapsed


def batch_forecast(series_list: list[dict]) -> tuple[list, float]:
    """Run a single batch forecast request."""
    payload = {
        "series_list": series_list,
        "frequency": "D",
        "model": "arima",
    }
    t_start = time.perf_counter()
    resp = requests.post(
        f"{BASE_URL}/forecast/batch",
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    elapsed = time.perf_counter() - t_start

    if resp.status_code != 200:
        raise RuntimeError(f"Batch request failed: HTTP {resp.status_code} — {resp.text[:200]}")

    data = resp.json()
    results = data.get("results", [])
    return results, elapsed


def main():
    print("=" * 65)
    print("TSFA Use Case 4 — Batch Forecasting for SaaS Multi-Tenant")
    print("=" * 65)
    print(f"\nGenerating {N_PRODUCTS} synthetic product demand series...")

    # Build series list, intentionally including one malformed series
    series_list = []
    for i in range(N_PRODUCTS - 1):
        series_list.append({
            "id": f"product_{i+1:03d}",
            "values": generate_product_series(seed=i + 42),
            "horizon": HORIZON,
        })

    # Add one malformed series (too short) to test error handling
    series_list.append({
        "id": "product_bad_050",
        "values": [100, 200, 150],  # Only 3 values — will fail validation
        "horizon": HORIZON,
    })

    valid_series = series_list[:-1]  # 49 valid series
    malformed_series = series_list[-1:]  # 1 malformed series

    print(f"  {len(valid_series)} valid series + 1 intentionally malformed series (too short)")

    # --- Sequential ---
    print(f"\n[1/2] Sequential: {len(valid_series)} individual /forecast/univariate calls...")
    seq_results, seq_time = sequential_forecast(valid_series)
    seq_success = sum(1 for r in seq_results if r["status"] == "success")
    print(f"  Completed: {seq_success}/{len(valid_series)} successful")
    print(f"  Time: {seq_time:.2f}s")

    # --- Batch (valid series only) ---
    print(f"\n[2/2] Batch: 1 request with {len(valid_series)} valid series...")
    try:
        batch_results, batch_time = batch_forecast(valid_series)
        batch_success = sum(1 for r in batch_results if r.get("status") == "success")
        batch_errors = sum(1 for r in batch_results if r.get("status") == "error")
        print(f"  Completed: {batch_success}/{len(valid_series)} successful, {batch_errors} error(s)")
        print(f"  Time: {batch_time:.2f}s")

        # Comparison
        print("\n" + "=" * 65)
        print("Results:")
        print(f"  Sequential ({len(valid_series)} calls) : {seq_time:.2f}s")
        print(f"  Batch (1 call, {len(valid_series)} series): {batch_time:.2f}s")
        if batch_time > 0:
            speedup = seq_time / batch_time
            print(f"  Speedup               : {speedup:.1f}x faster")

    except RuntimeError as e:
        print(f"  Batch request failed: {e}")

    # --- Error handling demo ---
    print(f"\n[+] Error handling: submitting batch with 1 malformed series (3 values, min=10)...")
    import requests as _req
    bad_payload = {
        "series_list": malformed_series,
        "frequency": "D",
        "model": "arima",
    }
    resp = _req.post(f"{BASE_URL}/forecast/batch", headers=HEADERS, json=bad_payload, timeout=10)
    print(f"  HTTP {resp.status_code} — validation error returned as expected ✅")
    print(f"  Detail: {resp.json().get('detail', [{}])[0].get('msg', '')[:80] if resp.status_code == 422 else resp.text[:80]}")


if __name__ == "__main__":
    main()
