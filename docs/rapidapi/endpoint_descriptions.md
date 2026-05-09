# TSFA — Endpoint Descriptions

Short descriptions for each endpoint, ready to paste into the RapidAPI interface.

---

## POST /v1/forecast/univariate
Forecast a single time series. Accepts 10–50,000 historical observations and returns point forecasts with 80% and 95% calibrated prediction intervals. Supports AutoARIMA, Chronos-T5 (pre-trained transformer), and LSTM models. Includes automatic frequency detection, trend/seasonality diagnostics, and stationarity test. Available on all plans.

## POST /v1/forecast/batch
Forecast 50–500 independent time series in a single parallel request. Each series is processed independently — one failure does not block the others. Returns per-series forecasts with confidence intervals and error isolation. **Pro plan:** up to 50 series. **Ultra plan:** up to 500 series.

## POST /v1/validate
Evaluate forecast accuracy on your own data using sliding-window backtesting. Splits the series into training and test windows, trains the selected model on each window, and computes MAE, RMSE, MAPE, and sMAPE. Use this before going to production to validate model fit and tune the horizon.

## GET /v1/models
List all available forecasting models with their descriptions, credit costs, and recommended use cases. No authentication required beyond the RapidAPI key.

## GET /v1/usage
Check your current billing period's credit consumption, remaining quota, and reset date. Returns per-model breakdown of credits used.

## GET /health
API health status endpoint. Returns `status`, `version`, `redis_connected`, and `uptime_seconds`. Used for monitoring and uptime checks. No credit consumed.
