"""Benchmark TSFA models vs baseline on 3 public datasets.

Datasets:
- ETT-h1 (electricity transformer temperature) — Autoformer paper
- Exchange Rate (8 currencies, Autoformer paper)
- M5-sample (synthetic retail demand approximation)

Metrics: MAE, RMSE, MAPE, sMAPE
Models: arima, naive (seasonal), chronos (if --local-only skipped and available)

Usage:
    python benchmarks/run_benchmark.py --model all --output benchmarks/results/
    python benchmarks/run_benchmark.py --model arima --local-only
    python benchmarks/run_benchmark.py --model chronos --local-only
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# ─── Constants ────────────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent / ".cache"
RESULTS_DIR = Path(__file__).parent / "results"

DATASET_URLS = {
    "ett_h1": "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv",
    "exchange_rate": (
        "https://raw.githubusercontent.com/laiguokun/"
        "multivariate-time-series-data/master/exchange_rate/exchange_rate.txt.gz"
    ),
}

EVAL_HORIZONS = {
    "ett_h1": 24,        # 24 hours ahead
    "exchange_rate": 30,  # 30 trading days
    "m5_sample": 14,     # 2-week retail horizon
}

FREQUENCIES = {
    "ett_h1": "h",
    "exchange_rate": "B",   # business days
    "m5_sample": "D",
}

N_EVAL_WINDOWS = 5   # rolling windows per dataset


# ─── Metric functions ─────────────────────────────────────────────────────────

def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = np.abs(y_true) > 1e-8
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def _smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    mask = denom > 1e-8
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask]) / denom[mask]) * 100)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": round(_mae(y_true, y_pred), 4),
        "rmse": round(_rmse(y_true, y_pred), 4),
        "mape": round(_mape(y_true, y_pred), 4),
        "smape": round(_smape(y_true, y_pred), 4),
    }


# ─── Data loaders ─────────────────────────────────────────────────────────────

def _download(url: str, dest: Path) -> bool:
    """Download url to dest.  Returns True on success."""
    try:
        print(f"  Downloading {dest.name} …", end=" ", flush=True)
        urllib.request.urlretrieve(url, dest)
        print("OK")
        return True
    except Exception as exc:
        print(f"FAILED ({exc})")
        return False


def load_ett_h1() -> np.ndarray | None:
    """Return OT (oil temperature) column from ETT-h1, first 2 000 rows."""
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / "ETTh1.csv"
    if not path.exists():
        ok = _download(DATASET_URLS["ett_h1"], path)
        if not ok:
            return None
    try:
        df = pd.read_csv(path)
        return df["OT"].values[:2000].astype(float)
    except Exception as exc:
        print(f"  Could not parse ETTh1.csv: {exc}")
        return None


def load_exchange_rate() -> np.ndarray | None:
    """Return first exchange-rate column, first 1 500 rows.

    Source: laiguokun/multivariate-time-series-data (space-separated .txt.gz).
    Falls back gracefully if unavailable.
    """
    import gzip

    CACHE_DIR.mkdir(exist_ok=True)
    gz_path = CACHE_DIR / "exchange_rate.txt.gz"
    if not gz_path.exists():
        ok = _download(DATASET_URLS["exchange_rate"], gz_path)
        if not ok:
            return None
    try:
        with gzip.open(gz_path, "rt") as f:
            df = pd.read_csv(f, header=None, sep=",")
        return df.iloc[:1500, 0].values.astype(float)
    except Exception as exc:
        print(f"  Could not parse exchange_rate.txt.gz: {exc}")
        return None


def load_m5_sample() -> np.ndarray:
    """Generate a synthetic M5-like weekly retail demand series (deterministic)."""
    rng = np.random.default_rng(42)
    n = 600
    trend = np.linspace(80.0, 130.0, n)
    weekly = 20.0 * np.sin(2 * np.pi * np.arange(n) / 7)
    annual = 10.0 * np.sin(2 * np.pi * np.arange(n) / 365)
    noise = rng.normal(0.0, 4.0, n)
    return np.clip(trend + weekly + annual + noise, 0.0, None)


# ─── Model runners ────────────────────────────────────────────────────────────

def run_arima(train: np.ndarray, horizon: int, freq: str) -> np.ndarray:
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA

    # statsforecast requires uppercase legacy freq aliases on older versions
    freq_map = {"h": "H", "B": "B", "D": "D", "W": "W", "M": "M"}
    sf_freq = freq_map.get(freq, freq)

    df = pd.DataFrame(
        {
            "unique_id": ["s1"] * len(train),
            "ds": pd.date_range("2020-01-01", periods=len(train), freq=sf_freq),
            "y": train,
        }
    )
    sf = StatsForecast(models=[AutoARIMA()], freq=sf_freq, n_jobs=1)
    sf.fit(df)
    forecast_df = sf.predict(h=horizon)
    col = "AutoARIMA" if "AutoARIMA" in forecast_df.columns else forecast_df.columns[-1]
    return forecast_df[col].values


def run_naive(train: np.ndarray, horizon: int) -> np.ndarray:
    """Repeat the last observed value (simple naive baseline)."""
    return np.full(horizon, float(train[-1]))


def run_seasonal_naive(train: np.ndarray, horizon: int, freq: str) -> np.ndarray:
    """Predict the value from the same period one season ago (seasonal naive).

    Season length: 7 for daily/business-day, 24 for hourly, 12 for monthly.
    """
    season_map = {"D": 7, "B": 5, "h": 24, "H": 24, "W": 4, "M": 12}
    m = season_map.get(freq, 7)
    if len(train) < m:
        # Fallback to simple naive if not enough history
        return run_naive(train, horizon)
    preds = []
    for i in range(horizon):
        idx = len(train) - m + (i % m)
        preds.append(float(train[idx]))
    return np.array(preds)


def run_chronos(train: np.ndarray, horizon: int) -> np.ndarray:
    """Run ChronosModel locally (requires chronos + torch installed)."""
    from ml.models.chronos_model import ChronosModel

    model = ChronosModel()
    model.fit(list(train.astype(float)), "D")
    result = model.predict(horizon=horizon)
    return np.array(result["mean"], dtype=float)


# ─── Evaluation loop ──────────────────────────────────────────────────────────

def rolling_evaluate(
    series: np.ndarray,
    horizon: int,
    model_name: str,
    freq: str,
    local_only: bool,
) -> dict | None:
    """Run N_EVAL_WINDOWS rolling windows and average metrics."""
    n = len(series)
    min_train = max(12, horizon * 2)

    # Windows end at test_start + horizon; we evaluate from the right
    windows = []
    for i in range(N_EVAL_WINDOWS, 0, -1):
        test_start = n - i * horizon
        if test_start < min_train:
            continue
        windows.append((test_start, test_start + horizon))

    if not windows:
        print(f"    Not enough data for evaluation (n={n}, horizon={horizon})")
        return None

    all_metrics: list[dict] = []

    for test_start, test_end in windows:
        train = series[:test_start]
        y_true = series[test_start:test_end]
        if len(y_true) < horizon:
            continue

        try:
            if model_name == "arima":
                y_pred = run_arima(train, horizon, freq)
            elif model_name == "naive":
                y_pred = run_naive(train, horizon)
            elif model_name == "seasonal_naive":
                y_pred = run_seasonal_naive(train, horizon, freq)
            elif model_name == "chronos":
                if local_only:
                    # Fallback to ARIMA when chronos/torch unavailable
                    y_pred = run_arima(train, horizon, freq)
                else:
                    y_pred = run_chronos(train, horizon)
            else:
                print(f"    Unknown model: {model_name}")
                return None

            y_pred = y_pred[: len(y_true)]
            all_metrics.append(compute_metrics(y_true, y_pred))

        except Exception as exc:
            print(f"    Window {test_start}–{test_end}: {model_name} error: {exc}")
            continue

    if not all_metrics:
        return None

    keys = ["mae", "rmse", "mape", "smape"]
    averaged = {
        k: round(float(np.nanmean([m[k] for m in all_metrics])), 4) for k in keys
    }
    averaged["n_windows"] = len(all_metrics)
    return averaged


# ─── Report generator ─────────────────────────────────────────────────────────

def build_readme(results: list[dict]) -> str:
    lines = [
        "# TSFA Benchmark Results",
        "",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Evaluation methodology: rolling-window backtesting "
        f"({N_EVAL_WINDOWS} windows per dataset).",
        "",
        "## Results",
        "",
        "| Dataset | Model | Horizon | MAE | RMSE | MAPE | sMAPE | Windows |",
        "| ------- | ----- | ------- | --- | ---- | ---- | ----- | ------- |",
    ]

    for r in results:
        if "error" in r:
            lines.append(
                f"| {r['dataset']} | {r['model']} | — | *{r['error']}* | | | | |"
            )
        else:
            lines.append(
                f"| {r['dataset']} | {r['model']} | {r['horizon']} "
                f"| {r['mae']} | {r['rmse']} "
                f"| {r['mape']}% | {r['smape']}% | {r['n_windows']} |"
            )

    lines += [
        "",
        "## Models",
        "",
        "- **arima**: AutoARIMA via `statsforecast` (local, CPU)",
        "- **chronos**: Chronos-T5-Small via Modal.com (GPU) — "
        "shown as ARIMA-fallback when `--local-only`",
        "- **naive**: Repeat last observed value (baseline)",
        "- **seasonal_naive**: Predict same-day last season value (7-day period for daily data)",
        "",
        "## Datasets",
        "",
        "- **ETT-h1**: Electricity Transformer Temperature, hourly, "
        "[ETDataset](https://github.com/zhouhaoyi/ETDataset)",
        "- **Exchange Rate**: 8 currency exchange rates, daily, "
        "[Time-Series-Library](https://github.com/thuml/Time-Series-Library)",
        "- **M5-sample**: Synthetic retail demand (M5-style weekly seasonality)",
        "",
        "## Metrics",
        "",
        "- **MAE**: Mean Absolute Error",
        "- **RMSE**: Root Mean Squared Error",
        "- **MAPE**: Mean Absolute Percentage Error (%)",
        "- **sMAPE**: Symmetric MAPE (%)",
    ]

    return "\n".join(lines) + "\n"


# ─── Main ─────────────────────────────────────────────────────────────────────

DATASETS = {
    "ett_h1": load_ett_h1,
    "exchange_rate": load_exchange_rate,
    "m5_sample": load_m5_sample,
}

ALL_MODELS = ["arima", "naive", "seasonal_naive", "chronos"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run TSFA benchmarks against public time-series datasets."
    )
    parser.add_argument(
        "--model",
        default="all",
        choices=ALL_MODELS + ["all", "baselines"],
        help="Model(s) to benchmark (default: all).",
    )
    parser.add_argument(
        "--output",
        default=str(RESULTS_DIR),
        help="Output directory for results (default: benchmarks/results/).",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Skip Modal calls — chronos uses ARIMA fallback locally.",
    )
    parser.add_argument(
        "--dataset",
        default="all",
        choices=list(DATASETS.keys()) + ["all"],
        help="Dataset to benchmark (default: all).",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.model == "all":
        models = ALL_MODELS
    elif args.model == "baselines":
        models = ["naive", "seasonal_naive"]
    else:
        models = [args.model]
    dataset_names = list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]

    print(f"TSFA Benchmark — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Models : {models}")
    print(f"Datasets: {dataset_names}")
    print(f"Local-only: {args.local_only}")
    print()

    all_results: list[dict] = []

    for ds_name in dataset_names:
        print(f"── Dataset: {ds_name} ──────────────────────────────")
        loader = DATASETS[ds_name]
        series = loader()

        if series is None:
            print(f"  Skipping {ds_name} (data unavailable).")
            all_results.append(
                {
                    "dataset": ds_name,
                    "model": "all",
                    "error": "data unavailable",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            continue

        print(f"  Series length: {len(series)}")
        horizon = EVAL_HORIZONS[ds_name]
        freq = FREQUENCIES[ds_name]

        for model_name in models:
            print(f"  [{model_name}] horizon={horizon} …", end=" ", flush=True)
            metrics = rolling_evaluate(series, horizon, model_name, freq, args.local_only)

            if metrics is None:
                print("SKIPPED")
                all_results.append(
                    {
                        "dataset": ds_name,
                        "model": model_name,
                        "horizon": horizon,
                        "error": "evaluation failed",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            else:
                print(
                    f"MAE={metrics['mae']:.4f}  RMSE={metrics['rmse']:.4f}  "
                    f"MAPE={metrics['mape']:.2f}%  sMAPE={metrics['smape']:.2f}%"
                )
                all_results.append(
                    {
                        "dataset": ds_name,
                        "model": model_name,
                        "horizon": horizon,
                        "freq": freq,
                        "local_only": args.local_only,
                        **metrics,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

    # ── Write outputs ──────────────────────────────────────────────────────────
    results_path = output_dir / "benchmark_results.json"
    results_path.write_text(
        json.dumps({"generated": datetime.utcnow().isoformat(), "results": all_results}, indent=2)
    )
    print(f"\nResults written to {results_path}")

    readme_path = output_dir / "README.md"
    readme_path.write_text(build_readme(all_results))
    print(f"README written to {readme_path}")

    # Summary table to stdout
    print("\n── Summary ──────────────────────────────────────────")
    for r in all_results:
        if "error" not in r:
            print(
                f"  {r['dataset']:15s} {r['model']:8s} "
                f"MAE={r['mae']:.4f}  RMSE={r['rmse']:.4f}  "
                f"sMAPE={r['smape']:.2f}%"
            )


if __name__ == "__main__":
    main()
