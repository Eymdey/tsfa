"""Integration tests for POST /v1/validate."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"X-RapidAPI-Proxy-Secret": "test", "X-RapidAPI-Subscription": "pro"}

SERIES_20 = [float(i + 1) for i in range(20)]
SERIES_50 = [float(i + 1) for i in range(50)]


@pytest.fixture
def client():
    with TestClient(app) as c:
        app.state.redis = None
        yield c


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_validate_success(client):
    payload = {"series": SERIES_20, "horizon": 3}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"


def test_validate_returns_mae(client):
    payload = {"series": SERIES_50, "horizon": 5}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "mae" in body or "metrics" in body or "windows" in body or "results" in body


def test_validate_with_n_windows(client):
    payload = {"series": SERIES_50, "horizon": 3, "n_windows": 2}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200


def test_validate_default_model(client):
    payload = {"series": SERIES_20, "horizon": 3}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200


def test_validate_explicit_arima_model(client):
    payload = {"series": SERIES_50, "horizon": 3, "model": "arima"}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_validate_series_too_short_returns_422(client):
    """Series shorter than minimum must be rejected."""
    payload = {"series": [1.0, 2.0, 3.0], "horizon": 2}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 422


def test_validate_missing_series_returns_422(client):
    payload = {"horizon": 3}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 422


def test_validate_missing_horizon_returns_422(client):
    payload = {"series": SERIES_20}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 422


def test_validate_horizon_zero_returns_422(client):
    payload = {"series": SERIES_20, "horizon": 0}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 422


def test_validate_horizon_negative_returns_422(client):
    payload = {"series": SERIES_20, "horizon": -1}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 422


def test_validate_n_windows_zero_returns_422(client):
    payload = {"series": SERIES_20, "horizon": 3, "n_windows": 0}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------

def test_validate_response_has_status(client):
    payload = {"series": SERIES_20, "horizon": 3}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert "status" in r.json()


def test_validate_response_has_meta(client):
    payload = {"series": SERIES_20, "horizon": 3}
    r = client.post("/v1/validate", json=payload, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "meta" in body or "credits_used" in body or "model_used" in body
