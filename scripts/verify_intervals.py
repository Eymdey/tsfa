"""
Vérifie que les intervalles de confiance sont mathématiquement corrects
sur les réponses réelles de l'API.

Usage:
    python3 scripts/verify_intervals.py
"""
import os
import requests
import json
import math
import sys

BASE_URL = "http://localhost:8000"
PROXY_SECRET = os.environ.get("RAPIDAPI_PROXY_SECRET", "")

if not PROXY_SECRET:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env_path) as f:
        for line in f:
            if line.startswith("RAPIDAPI_PROXY_SECRET="):
                PROXY_SECRET = line.strip().split("=", 1)[1]
                break

HEADERS = {
    "Content-Type": "application/json",
    "X-RapidAPI-Proxy-Secret": PROXY_SECRET,
    "X-Plan": "pro",
}

TEST_SERIES = [
    # 1. Trending upward
    {"name": "trend_up", "series": list(range(10, 60, 2)), "horizon": 5},
    # 2. Oscillating seasonal pattern
    {"name": "seasonal", "series": [100,110,120,115,105] * 8, "horizon": 7},
    # 3. Stationary random walk
    {"name": "stationary", "series": [50,52,49,54,53,55,51,56,54,57,53,58,55,59,56,60], "horizon": 5},
    # 4. Trending downward
    {"name": "trend_down", "series": list(range(100, 50, -2)), "horizon": 6},
    # 5. High variance series
    {"name": "high_var", "series": [10,50,5,80,2,60,15,45,8,70,3,90,12,40,7,65,20,55,9,75], "horizon": 5},
    # 6. Long series for Chronos auto-selection
    {"name": "long_series", "series": list(range(1, 61)), "horizon": 10},
    # 7. Near-constant series
    {"name": "near_const", "series": [100]*18 + [101, 99, 100, 98, 102, 100, 100, 101, 99, 100], "horizon": 4},
    # 8. Mixed frequency daily
    {"name": "mixed_daily", "series": [200,210,195,215,205,220,210,225,215,230,220,235,225,240,230,245], "horizon": 7},
    # 9. Exponential growth
    {"name": "exp_growth", "series": [round(1.05**i * 100) for i in range(20)], "horizon": 5},
    # 10. Series with a structural break
    {"name": "struct_break", "series": list(range(10, 20)) + list(range(50, 65)), "horizon": 5},
]


def verify_response(name: str, response: dict, horizon: int) -> list[str]:
    """
    Returns a list of anomalies. Empty list = all correct.
    Checks:
    - lower_95 <= lower_80 <= mean <= upper_80 <= upper_95 for each step
    - No NaN or Infinity
    - Forecast length == requested horizon
    - mean is within [lower_95, upper_95] for each step
    """
    errors = []
    forecast = response.get("forecast", {})
    mean = forecast.get("mean", [])
    l80 = forecast.get("lower_80", [])
    u80 = forecast.get("upper_80", [])
    l95 = forecast.get("lower_95", [])
    u95 = forecast.get("upper_95", [])

    if len(mean) != horizon:
        errors.append(f"Length mismatch: expected {horizon}, got {len(mean)}")

    if not (l80 and u80 and l95 and u95):
        errors.append("Missing interval fields")
        return errors

    for i, (m, lb, ub, l9, u9) in enumerate(zip(mean, l80, u80, l95, u95)):
        # NaN / Inf check
        if any(math.isnan(v) or math.isinf(v) for v in [m, lb, ub, l9, u9]):
            errors.append(f"Step {i}: NaN or Inf detected")
            continue

        # Ordering check (with small tolerance for floating point)
        eps = 1e-6
        if not (l9 - eps <= lb + eps and lb - eps <= m + eps and
                m - eps <= ub + eps and ub - eps <= u9 + eps):
            errors.append(
                f"Step {i}: ordering violated: "
                f"{l9:.4f} <= {lb:.4f} <= {m:.4f} <= {ub:.4f} <= {u9:.4f}"
            )

    return errors


def run_all_tests():
    results = []
    total_violations = 0
    total_errors = 0

    print("=" * 70)
    print("TSFA Interval Coherence Verification")
    print("=" * 70)
    print(f"Testing {len(TEST_SERIES)} series against {BASE_URL}")
    print()

    for test in TEST_SERIES:
        payload = {
            "series": test["series"],
            "horizon": test["horizon"],
            "frequency": "D",
            "model": "arima",
            "confidence_levels": [0.8, 0.95],
        }

        try:
            resp = requests.post(
                f"{BASE_URL}/v1/forecast/univariate",
                headers=HEADERS,
                json=payload,
                timeout=30,
            )

            if resp.status_code != 200:
                print(f"[ERROR] {test['name']}: HTTP {resp.status_code}")
                total_errors += 1
                results.append({
                    "name": test["name"],
                    "model": "?",
                    "violations": 0,
                    "status": "HTTP_ERROR",
                })
                continue

            data = resp.json()
            model_used = data.get("model_used", "?")
            errors = verify_response(test["name"], data, test["horizon"])

            if errors:
                total_violations += len(errors)
                print(f"[FAIL] {test['name']} (model={model_used}): {len(errors)} violation(s)")
                for e in errors:
                    print(f"       ↳ {e}")
            else:
                print(f"[ OK ] {test['name']} (model={model_used}, horizon={test['horizon']}) — all intervals valid")

            results.append({
                "name": test["name"],
                "model": model_used,
                "violations": len(errors),
                "status": "FAIL" if errors else "OK",
            })

        except Exception as exc:
            print(f"[ERROR] {test['name']}: {exc}")
            total_errors += 1
            results.append({
                "name": test["name"],
                "model": "?",
                "violations": 0,
                "status": "EXCEPTION",
            })

    print()
    print("=" * 70)
    ok_count = sum(1 for r in results if r["status"] == "OK")
    print(f"Results: {ok_count}/{len(TEST_SERIES)} series passed")
    print(f"Total interval violations: {total_violations}")
    print(f"HTTP/exception errors: {total_errors}")

    if total_violations == 0 and total_errors == 0:
        print("\n✅ ALL INTERVALS MATHEMATICALLY CORRECT")
        return 0
    else:
        print("\n❌ VIOLATIONS DETECTED — review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
