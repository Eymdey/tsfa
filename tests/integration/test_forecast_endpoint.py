"""Integration tests for POST /v1/forecast/univariate.

Uses FastAPI's TestClient (via httpx) with a mocked Redis state so tests
run without a real Redis instance.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Create a test client with no Redis (app.state.redis = None)."""
    app.state.redis = None
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


VALID_PAYLOAD = {
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,
    "frequency": "D",
    "model": "auto",
}

HEADERS = {"X-Plan": "free", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------


def test_valid_forecast_returns_200(client: TestClient):
    """A well-formed request with 12 data points and horizon 7 must return 200."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    assert response.status_code == 200


def test_response_has_status_success(client: TestClient):
    """Response body must contain status='success'."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    data = response.json()
    assert data["status"] == "success"


def test_response_has_forecast_mean(client: TestClient):
    """Response must include forecast.mean as a list of 7 values."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    data = response.json()
    assert "forecast" in data
    assert "mean" in data["forecast"]
    assert isinstance(data["forecast"]["mean"], list)
    assert len(data["forecast"]["mean"]) == 7


def test_response_has_confidence_intervals(client: TestClient):
    """Response must include lower_95 and upper_95 arrays."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    data = response.json()
    forecast = data["forecast"]
    assert "lower_95" in forecast
    assert "upper_95" in forecast
    assert isinstance(forecast["lower_95"], list)
    assert isinstance(forecast["upper_95"], list)
    assert len(forecast["lower_95"]) == 7
    assert len(forecast["upper_95"]) == 7


def test_response_has_diagnostics(client: TestClient):
    """Response must include a complete diagnostics block."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    data = response.json()
    assert "diagnostics" in data
    diag = data["diagnostics"]
    assert "trend" in diag
    assert "seasonality_detected" in diag
    assert "series_length" in diag
    assert "missing_values" in diag
    assert "stationarity" in diag
    assert diag["series_length"] == 12


def test_response_has_meta_with_inference_time(client: TestClient):
    """Response meta must include inference_time_ms."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    data = response.json()
    assert "meta" in data
    meta = data["meta"]
    assert "inference_time_ms" in meta
    assert isinstance(meta["inference_time_ms"], (int, float))
    assert meta["inference_time_ms"] >= 0


def test_response_meta_has_request_id(client: TestClient):
    """Response meta must include a request_id."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    data = response.json()
    assert "request_id" in data["meta"]
    assert data["meta"]["request_id"].startswith("req_")


def test_model_used_is_arima(client: TestClient):
    """Phase 1 must always report model_used='arima'."""
    response = client.post("/v1/forecast/univariate", json=VALID_PAYLOAD, headers=HEADERS)
    data = response.json()
    assert data["model_used"] == "arima"


# ---------------------------------------------------------------------------
# Error cases — 422 Unprocessable Entity
# ---------------------------------------------------------------------------


def test_series_too_short_returns_422(client: TestClient):
    """A series with fewer than 10 points must return 422."""
    payload = {**VALID_PAYLOAD, "series": [1.0, 2.0, 3.0, 4.0, 5.0]}
    response = client.post("/v1/forecast/univariate", json=payload, headers=HEADERS)
    assert response.status_code == 422


def test_horizon_too_large_returns_422(client: TestClient):
    """horizon=366 must return 422."""
    payload = {**VALID_PAYLOAD, "horizon": 366}
    response = client.post("/v1/forecast/univariate", json=payload, headers=HEADERS)
    assert response.status_code == 422


def test_horizon_zero_returns_422(client: TestClient):
    """horizon=0 must return 422."""
    payload = {**VALID_PAYLOAD, "horizon": 0}
    response = client.post("/v1/forecast/univariate", json=payload, headers=HEADERS)
    assert response.status_code == 422


def test_invalid_frequency_returns_422(client: TestClient):
    """An unrecognised frequency string must return 422."""
    payload = {**VALID_PAYLOAD, "frequency": "X"}
    response = client.post("/v1/forecast/univariate", json=payload, headers=HEADERS)
    assert response.status_code == 422


def test_invalid_model_returns_422(client: TestClient):
    """An unrecognised model name must return 422."""
    payload = {**VALID_PAYLOAD, "model": "gpt4"}
    response = client.post("/v1/forecast/univariate", json=payload, headers=HEADERS)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Other endpoints
# ---------------------------------------------------------------------------


def test_health_check(client: TestClient):
    """GET /health must return 200 with status='ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_models_returns_200(client: TestClient):
    """GET /v1/models must return 200 with a models list."""
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)
    assert len(data["models"]) > 0


def test_arima_is_available_in_models(client: TestClient):
    """GET /v1/models must list arima as available=true."""
    response = client.get("/v1/models")
    models = response.json()["models"]
    arima_models = [m for m in models if m["id"] == "arima"]
    assert len(arima_models) == 1
    assert arima_models[0]["available"] is True


def test_multivariate_returns_501(client: TestClient):
    """POST /v1/forecast/multivariate must return 501."""
    payload = {
        "target": {
            "name": "sales",
            "values": [float(i) for i in range(10)],
        },
        "covariates": [
            {"name": "temp", "values": [float(i) for i in range(10)], "is_future_known": False}
        ],
        "horizon": 3,
    }
    response = client.post("/v1/forecast/multivariate", json=payload, headers=HEADERS)
    assert response.status_code == 501


def test_batch_returns_501(client: TestClient):
    """POST /v1/forecast/batch must return 501."""
    payload = {
        "series_list": [
            {"id": "s1", "values": [float(i) for i in range(10)], "horizon": 3}
        ]
    }
    response = client.post("/v1/forecast/batch", json=payload, headers=HEADERS)
    assert response.status_code == 501
