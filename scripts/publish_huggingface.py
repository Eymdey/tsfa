"""
Publication sur HuggingFace Hub.

Usage:
    pip install huggingface_hub
    huggingface-cli login
    python scripts/publish_huggingface.py --repo Eymdeyy/tsfa-forecasting-api

Ce script publie :
- Un README.md (model card) avec benchmarks intégrés
- Le fichier benchmark_results.json
- Un lien vers l'API RapidAPI
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

try:
    from huggingface_hub import HfApi, create_repo, upload_file
except ImportError:
    raise SystemExit(
        "huggingface_hub not installed. Run: pip install huggingface_hub"
    )

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_PATH = PROJECT_ROOT / "benchmarks" / "results" / "benchmark_results.json"
RAPIDAPI_URL = "https://rapidapi.com/dorianmrt/api/tsfa"  # fill after publication


def load_benchmarks() -> list[dict]:
    if not BENCHMARK_PATH.exists():
        return []
    with open(BENCHMARK_PATH) as f:
        data = json.load(f)
    return data.get("results", [])


def format_benchmark_table(results: list[dict]) -> str:
    if not results:
        return "_No benchmark results found._\n"

    lines = [
        "| Dataset | Model | Horizon | MAE | RMSE | MAPE | sMAPE |",
        "|---------|-------|---------|-----|------|------|-------|",
    ]
    for r in results:
        lines.append(
            f"| {r['dataset']} | {r['model']} | {r['horizon']} "
            f"| {r['mae']:.4f} | {r['rmse']:.4f} "
            f"| {r['mape']:.2f}% | {r['smape']:.2f}% |"
        )
    return "\n".join(lines)


def generate_readme(results: list[dict]) -> str:
    benchmark_table = format_benchmark_table(results)
    return f"""---
language: en
license: mit
tags:
  - time-series
  - forecasting
  - arima
  - chronos
  - lstm
  - api
---

# TSFA — Time Series Forecasting API

**Predict future values with calibrated confidence intervals via a simple REST API.**

TSFA handles the full forecasting pipeline: automatic preprocessing, model selection,
uncertainty quantification, and diagnostics — no ML expertise required.

## Available on RapidAPI

🚀 **[Try the API on RapidAPI]({RAPIDAPI_URL})**

Free tier available. No credit card required to start.

## Quick Start

```python
import requests

resp = requests.post(
    "https://tsfa.p.rapidapi.com/v1/forecast/univariate",
    headers={{
        "X-RapidAPI-Key": "YOUR_KEY",
        "X-RapidAPI-Host": "tsfa.p.rapidapi.com",
    }},
    json={{
        "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168],
        "horizon": 7,
        "model": "auto",
    }},
)
print(resp.json()["forecast"]["mean"])
# [171.2, 174.5, 177.8, 181.0, 184.3, 187.6, 190.8]
```

## Models

| Model | Credits | Best For |
|-------|---------|----------|
| `auto` | 1 | Automatic selection — recommended |
| `arima` | 1 | Stationary series, interpretable |
| `chronos` | 1 | Pre-trained transformer (zero-shot) |
| `lstm` | 2 | Long sequences, complex patterns |

## Benchmarks

Evaluated via sliding-window backtesting (5 windows) on public datasets.

{benchmark_table}

Datasets: ETT-h1 (electricity transformer temperature), Exchange Rate (8 currencies),
M5 (retail sales). All results are out-of-sample.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/forecast/univariate` | Forecast a single series |
| POST | `/v1/forecast/batch` | Forecast 50–500 series in parallel |
| POST | `/v1/validate` | Backtest with sliding-window cross-validation |
| GET | `/v1/models` | List available models |
| GET | `/v1/usage` | Check credit consumption |
| GET | `/health` | API health status |

## Plans

| Plan | Monthly Credits | Rate Limit | Price |
|------|----------------|------------|-------|
| BASIC | 500 | 10 req/min | $0 |
| PRO | 10,000 | 30 req/min | $49 |
| ULTRA | 50,000 | 100 req/min | $199 |
| MEGA | 200,000 | 300 req/min | $499 |

## License

MIT — see [LICENSE](./LICENSE)
"""


def publish(repo_id: str, dry_run: bool = False) -> None:
    api = HfApi()

    print(f"Publishing to HuggingFace Hub: {repo_id}")

    if not dry_run:
        create_repo(repo_id, repo_type="model", exist_ok=True)
        print(f"  Repo ready: https://huggingface.co/{repo_id}")

    # Load benchmarks
    results = load_benchmarks()
    print(f"  Loaded {len(results)} benchmark result(s)")

    # Generate README
    readme_content = generate_readme(results)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write README
        readme_path = tmp / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")

        # Copy benchmark_results.json
        benchmark_dest = tmp / "benchmark_results.json"
        if BENCHMARK_PATH.exists():
            benchmark_dest.write_text(
                BENCHMARK_PATH.read_text(encoding="utf-8"), encoding="utf-8"
            )

        if dry_run:
            print("\n--- DRY RUN: README.md ---")
            print(readme_content)
            print("--- END DRY RUN ---")
            return

        # Upload README
        upload_file(
            path_or_fileobj=str(readme_path),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="model",
            commit_message="Update model card with benchmarks",
        )
        print("  Uploaded README.md")

        # Upload benchmark results
        if benchmark_dest.exists():
            upload_file(
                path_or_fileobj=str(benchmark_dest),
                path_in_repo="benchmark_results.json",
                repo_id=repo_id,
                repo_type="model",
                commit_message="Update benchmark results",
            )
            print("  Uploaded benchmark_results.json")

    print(f"\nDone! View at: https://huggingface.co/{repo_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish TSFA to HuggingFace Hub")
    parser.add_argument(
        "--repo",
        default="Eymdeyy/tsfa-forecasting-api",
        help="HuggingFace repo ID (default: Eymdeyy/tsfa-forecasting-api)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print README without uploading",
    )
    args = parser.parse_args()
    publish(args.repo, dry_run=args.dry_run)
