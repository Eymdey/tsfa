# TSFA Benchmark Results

Generated: 2026-05-11 15:08 UTC

Evaluation methodology: rolling-window backtesting (5 windows per dataset).

## Results on M5 Sample Dataset (horizon=14, frequency=D)

*Lower is better. Benchmarks run on public datasets with fixed random seed 42.*

| Model | MAE | RMSE | MAPE | sMAPE |
|---|---|---|---|---|
| Naive | 14.3541 | 16.7054 | 11.45% | 11.74% |
| Seasonal Naive | 5.0372 | 6.2019 | 4.24% | 4.18% |
| **AutoARIMA** | **9.0427** | **10.5617** | **7.63%** | **7.43%** |

## Full Results (All Datasets)

| Dataset | Model | Horizon | MAE | RMSE | MAPE | sMAPE | Windows |
| ------- | ----- | ------- | --- | ---- | ---- | ----- | ------- |
| ett_h1 | arima | 24 | 2.4524 | 2.9405 | 10.1167% | 10.7415% | 5 |
| ett_h1 | naive | 24 | 2.4524 | 2.9405 | 10.1167% | 10.7415% | 5 |
| ett_h1 | seasonal_naive | 24 | 1.9263 | 2.2837 | 8.2541% | 8.7383% | 5 |
| ett_h1 | chronos* | 24 | 2.4524 | 2.9405 | 10.1167% | 10.7415% | 5 |
| exchange_rate | arima | 30 | 0.0085 | 0.0100 | 1.1314% | 1.1348% | 5 |
| exchange_rate | naive | 30 | 0.0085 | 0.0100 | 1.1314% | 1.1348% | 5 |
| exchange_rate | seasonal_naive | 30 | 0.0103 | 0.0117 | 1.3734% | 1.3749% | 5 |
| exchange_rate | chronos* | 30 | 0.0085 | 0.0100 | 1.1314% | 1.1348% | 5 |
| m5_sample | arima | 14 | 9.0427 | 10.5617 | 7.6337% | 7.4284% | 5 |
| m5_sample | naive | 14 | 14.3541 | 16.7054 | 11.4515% | 11.7407% | 5 |
| m5_sample | seasonal_naive | 14 | 5.0372 | 6.2019 | 4.2397% | 4.1772% | 5 |
| m5_sample | chronos* | 14 | 9.0427 | 10.5617 | 7.6337% | 7.4284% | 5 |

*\* Chronos shown as AutoARIMA fallback (local-only mode). GPU results available when USE_MODAL=true with Modal credentials.*

## Models

- **arima**: AutoARIMA via `statsforecast` (local, CPU)
- **chronos**: Chronos-T5-Small via Modal.com (GPU) — shown as ARIMA-fallback when `--local-only`
- **naive**: Repeat last observed value (baseline)
- **seasonal_naive**: Predict same-day last season value (7-day period for daily data)

## Datasets

- **ETT-h1**: Electricity Transformer Temperature, hourly, [ETDataset](https://github.com/zhouhaoyi/ETDataset)
- **Exchange Rate**: 8 currency exchange rates, daily, [Time-Series-Library](https://github.com/thuml/Time-Series-Library)
- **M5-sample**: Synthetic retail demand (M5-style weekly seasonality)

## Metrics

- **MAE**: Mean Absolute Error
- **RMSE**: Root Mean Squared Error
- **MAPE**: Mean Absolute Percentage Error (%)
- **sMAPE**: Symmetric MAPE (%)
