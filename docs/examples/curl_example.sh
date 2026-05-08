#!/usr/bin/env bash
# TSFA curl examples
# ==================
# Three commented curl examples for the TSFA API.
# Run with: bash docs/examples/curl_example.sh

BASE_URL="http://localhost:8000/v1"

echo "========================================"
echo "Example 1: Basic daily forecast (7 days)"
echo "========================================"

# POST /v1/forecast/univariate
# Forecast 7 days ahead from 12 daily observations.
# X-Plan: free — local development plan header
# In production, use X-RapidAPI-Key instead.
curl -s -X POST "${BASE_URL}/forecast/univariate" \
  -H "Content-Type: application/json" \
  -H "X-Plan: free" \
  -d '{
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,
    "frequency": "D",
    "model": "auto"
  }' | python3 -m json.tool

echo ""
echo "========================================"
echo "Example 2: Monthly forecast with custom confidence levels"
echo "========================================"

# Forecast 12 months of monthly revenue data.
# confidence_levels: [0.80, 0.95] produces 4 interval arrays in the response.
curl -s -X POST "${BASE_URL}/forecast/univariate" \
  -H "Content-Type: application/json" \
  -H "X-Plan: basic" \
  -d '{
    "series": [
      1200, 1150, 1320, 1180, 1400, 1350, 1500, 1450,
      1600, 1550, 1700, 1650, 1800, 1750, 1900, 1850,
      2000, 1950, 2100, 2050, 2200, 2150, 2300, 2250
    ],
    "horizon": 12,
    "frequency": "M",
    "model": "arima",
    "confidence_levels": [0.80, 0.95]
  }' | python3 -m json.tool

echo ""
echo "========================================"
echo "Example 3: Weekly data with explicit timestamps"
echo "========================================"

# Provide timestamps for proper date labelling in the forecast output.
# The response forecast.timestamps will continue from the last provided date.
curl -s -X POST "${BASE_URL}/forecast/univariate" \
  -H "Content-Type: application/json" \
  -H "X-Plan: free" \
  -d '{
    "series": [450, 480, 520, 490, 510, 540, 560, 530, 570, 590, 610, 580],
    "timestamps": [
      "2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22", "2024-01-29",
      "2024-02-05", "2024-02-12", "2024-02-19", "2024-02-26", "2024-03-04",
      "2024-03-11", "2024-03-18"
    ],
    "horizon": 4,
    "frequency": "W",
    "model": "auto"
  }' | python3 -m json.tool

echo ""
echo "Done."
