# TSFA Benchmark Results

Generated: 2026-05-08 22:37 UTC

Evaluation methodology: rolling-window backtesting (5 windows per dataset).

## Results

| Dataset | Model | Horizon | MAE | RMSE | MAPE | sMAPE | Windows |
| ------- | ----- | ------- | --- | ---- | ---- | ----- | ------- |
| ett_h1 | arima | 24 | 2.4524 | 2.9405 | 10.1167% | 10.7415% | 5 |
| exchange_rate | arima | 30 | 0.0085 | 0.01 | 1.1314% | 1.1348% | 5 |
| m5_sample | arima | 14 | 9.0427 | 10.5617 | 7.6337% | 7.4284% | 5 |

## Models

- **arima**: AutoARIMA via `statsforecast` (local, CPU)
- **chronos**: Chronos-T5-Small via Modal.com (GPU) — shown as ARIMA-fallback when `--local-only`
- **naive**: Repeat last observed value (baseline)

## Datasets

- **ETT-h1**: Electricity Transformer Temperature, hourly, [ETDataset](https://github.com/zhouhaoyi/ETDataset)
- **Exchange Rate**: 8 currency exchange rates, daily, [Time-Series-Library](https://github.com/thuml/Time-Series-Library)
- **M5-sample**: Synthetic retail demand (M5-style weekly seasonality)

## Metrics

- **MAE**: Mean Absolute Error
- **RMSE**: Root Mean Squared Error
- **MAPE**: Mean Absolute Percentage Error (%)
- **sMAPE**: Symmetric MAPE (%)
