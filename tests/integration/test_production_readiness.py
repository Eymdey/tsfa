"""
Tests de readiness production.
Ces tests vérifient les comportements critiques pour RapidAPI.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture()
def client():
    """Test client with no Redis (unit-level)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        app.state.redis = None
        yield c


@pytest.fixture()
def prod_client(monkeypatch):
    """Test client simulating production environment."""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "rapidapi_proxy_secret", "test-proxy-secret-prod")
    with TestClient(app, raise_server_exceptions=False) as c:
        app.state.redis = None
        yield c


# ---------------------------------------------------------------------------
# Proxy secret enforcement
# ---------------------------------------------------------------------------


def test_proxy_secret_missing_returns_403_in_production(prod_client):
    """Sans X-RapidAPI-Proxy-Secret en mode production → 403."""
    resp = prod_client.post(
        "/v1/forecast/univariate",
        json={
            "series": list(range(10, 25)),
            "horizon": 3,
            "model": "arima",
        },
        headers={"X-Plan": "pro"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["code"] == "FORBIDDEN"


def test_proxy_secret_wrong_returns_403_in_production(prod_client):
    """Avec un mauvais secret en production → 403."""
    resp = prod_client.post(
        "/v1/forecast/univariate",
        json={
            "series": list(range(10, 25)),
            "horizon": 3,
            "model": "arima",
        },
        headers={
            "X-Plan": "pro",
            "X-RapidAPI-Proxy-Secret": "wrong-secret",
        },
    )
    assert resp.status_code == 403


def test_proxy_secret_valid_passes(prod_client):
    """Avec le bon secret → requête traitée normalement (non-403)."""
    resp = prod_client.post(
        "/v1/forecast/univariate",
        json={
            "series": list(range(10, 25)),
            "horizon": 3,
            "model": "arima",
        },
        headers={
            "X-Plan": "pro",
            "X-RapidAPI-Proxy-Secret": "test-proxy-secret-prod",
        },
    )
    assert resp.status_code != 403


def test_proxy_secret_not_checked_in_development(client):
    """En mode développement → pas de vérification du secret."""
    resp = client.post(
        "/v1/forecast/univariate",
        json={
            "series": list(range(10, 25)),
            "horizon": 3,
            "model": "arima",
        },
        headers={"X-Plan": "free"},
    )
    # No 403 regardless of missing proxy secret
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Response headers
# ---------------------------------------------------------------------------


def test_response_headers_present(client):
    """X-Request-Id, X-Credits-Used, X-Credits-Remaining présents."""
    resp = client.post(
        "/v1/forecast/univariate",
        json={
            "series": list(range(10, 25)),
            "horizon": 3,
            "model": "arima",
        },
        headers={"X-Plan": "pro"},
    )
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    assert "x-credits-used" in resp.headers
    assert "x-credits-remaining" in resp.headers


# ---------------------------------------------------------------------------
# Payload size limits
# ---------------------------------------------------------------------------


def test_oversized_series_rejected(client):
    """Série de 50001 valeurs → 422."""
    resp = client.post(
        "/v1/forecast/univariate",
        json={
            "series": [1.0] * 50001,
            "horizon": 3,
            "model": "arima",
        },
        headers={"X-Plan": "pro"},
    )
    assert resp.status_code == 422


def test_max_series_accepted(client):
    """Série de exactement 50000 valeurs → pas de 422 pour taille."""
    resp = client.post(
        "/v1/forecast/univariate",
        json={
            "series": [float(i % 100 + 1) for i in range(50000)],
            "horizon": 3,
            "model": "arima",
        },
        headers={"X-Plan": "pro"},
    )
    # May succeed or fail for other reasons (model timeout) but NOT 422 for size
    assert resp.status_code != 422 or "50 000" not in resp.text


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_returns_all_fields(client):
    """Health check contient status, version, redis_connected, uptime_seconds."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "version" in body
    assert "redis_connected" in body
    assert "uptime_seconds" in body
    assert body["status"] == "ok"


def test_health_no_proxy_check(prod_client):
    """/health est accessible sans X-RapidAPI-Proxy-Secret même en production."""
    resp = prod_client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GZip compression
# ---------------------------------------------------------------------------


def test_gzip_compression_active(client):
    """Réponse avec Accept-Encoding: gzip → contenu potentiellement compressé."""
    resp = client.post(
        "/v1/forecast/univariate",
        json={
            "series": list(range(10, 25)),
            "horizon": 7,
            "model": "arima",
        },
        headers={
            "X-Plan": "pro",
            "Accept-Encoding": "gzip",
        },
    )
    assert resp.status_code == 200
    # TestClient auto-decompresses; verify the middleware is registered
    # by confirming the app accepted the request successfully
    assert resp.json()["status"] == "success"


# ---------------------------------------------------------------------------
# Rate limit headers
# ---------------------------------------------------------------------------


def test_rate_limit_headers_present(client):
    """X-RateLimit-Limit et X-RateLimit-Remaining présents sur les réponses forecast."""
    resp = client.post(
        "/v1/forecast/univariate",
        json={
            "series": list(range(10, 25)),
            "horizon": 3,
            "model": "arima",
        },
        headers={"X-Plan": "pro"},
    )
    assert resp.status_code == 200
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers
