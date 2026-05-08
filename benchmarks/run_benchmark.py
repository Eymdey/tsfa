"""Benchmark runner — Phase 1 placeholder.

This script will run reproducible benchmarks of TSFA models against
standard time series datasets (M5, ETT, Traffic) and generate the
public benchmark_results.json file.

Phase 2 implementation will include:
- M5 dataset (retail demand forecasting)
- ETT-H1 dataset (electricity transformer temperature)
- Traffic dataset (road occupancy rates)

Each model will be evaluated on MAE, RMSE, MAPE, and SMAPE metrics
across multiple forecasting horizons.
"""

# TODO (Phase 2): Implement full benchmark pipeline
#
# import pandas as pd
# import numpy as np
# from pathlib import Path
# from statsforecast import StatsForecast
# from statsforecast.models import AutoARIMA
#
# DATASETS = {
#     "m5_sample": "benchmarks/datasets/m5_sample.csv",
#     "ett_h1_sample": "benchmarks/datasets/ett_h1_sample.csv",
#     "traffic_sample": "benchmarks/datasets/traffic_sample.csv",
# }
#
# def run_all_benchmarks() -> dict:
#     results = {}
#     for name, path in DATASETS.items():
#         results[name] = run_dataset_benchmark(path)
#     return results
#
# if __name__ == "__main__":
#     results = run_all_benchmarks()
#     import json
#     with open("benchmarks/results/benchmark_results.json", "w") as f:
#         json.dump(results, f, indent=2)
#     print("Benchmarks complete. Results saved.")

if __name__ == "__main__":
    print("Benchmark runner — Phase 2 placeholder. Not yet implemented.")
