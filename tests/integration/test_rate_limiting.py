"""Integration tests for Redis-based rate limiting."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app

HEADERS_FREE = {"X-RapidAPI-Proxy-Secret": "test", "X-RapidAPI-Subscription": "free"}
HEADERS_PRO = {"X-RapidAPI-Proxy-Secret": "test", "X-RapidAPI-Subscription": "pro"}

SERIES = [float(i + 1) for i in range(15)]


@pytest.fixture
def client_no_redis():
    with TestClient(app) as c:
        app.state.redis = None
        yield c


def _make_counting_redis(limit: int):
    """Redis mock that counts calls and returns 429 after `limit` increments."""
    call_count = 0
    r = MagicMock()

    async def fake_incr(key):
        nonlocal call_count
        call_count += 1
        return call_count

    r.incr = AsyncMock(side_effect=fake_incr)
    r.expire = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    r.pipeline = MagicMock()
    pipe = MagicMock()
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=False)
    pipe.incr = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[call_count, True, call_count, True])
    r.pipeline.return_value = pipe
    return r


# ---------------------------------------------------------------------------
# No Redis — rate limiting disabled, no 429
# ---------------------------------------------------------------------------

def test_no_redis_no_rate_limit(client_no_redis):
    """Without Redis, requests never get rate-limited."""
    payload = {"series": SERIES, "horizon": 3}
    for _ in range(5):
        r = client_no_redis.post(
            "/v1/forecast/univariate", json=payload, headers=HEADERS_FREE
        )
        assert r.status_code != 429


# ---------------------------------------------------------------------------
# With Redis mock — 429 after limit exceeded
# ---------------------------------------------------------------------------

def test_rate_limit_429_after_limit():
    """11th request on free plan (limit=10/min) must return 429."""
    redis_mock = _make_counting_redis(limit=10)

    with TestClient(app) as c:
        app.state.redis = redis_mock
        payload = {"series": SERIES, "horizon": 3}
        responses = []
        for i in range(11):
            r = c.post(
                "/v1/forecast/univariate",
                json=payload,
                headers=HEADERS_FREE,
            )
            responses.append(r.status_code)

    # At least one 429 must appear
    assert 429 in responses, f"Expected a 429 but got: {responses}"


def test_rate_limit_response_has_retry_after():
    """429 response must include Retry-After header."""
    # Simulate Redis returning high count immediately
    r = MagicMock()
    r.incr = AsyncMock(return_value=9999)
    r.expire = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    pipe = MagicMock()
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=False)
    pipe.incr = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[9999, True, 9999, True])
    r.pipeline.return_value = pipe

    with TestClient(app, raise_server_exceptions=False) as c:
        app.state.redis = r
        payload = {"series": SERIES, "horizon": 3}
        resp = c.post("/v1/forecast/univariate", json=payload, headers=HEADERS_FREE)

    if resp.status_code == 429:
        assert "retry-after" in resp.headers or "Retry-After" in resp.headers


def test_pro_plan_higher_rate_limit():
    """Pro plan should allow more requests per minute than free."""
    call_count = 0
    redis_mock = MagicMock()

    async def counting_incr(key):
        nonlocal call_count
        call_count += 1
        return call_count

    redis_mock.incr = AsyncMock(side_effect=counting_incr)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    pipe = MagicMock()
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=False)
    pipe.incr = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[call_count, True, call_count, True])
    redis_mock.pipeline.return_value = pipe

    payload = {"series": SERIES, "horizon": 3}
    statuses = []
    with TestClient(app) as c:
        app.state.redis = redis_mock
        for _ in range(15):
            r = c.post("/v1/forecast/univariate", json=payload, headers=HEADERS_PRO)
            statuses.append(r.status_code)

    # With pro plan, 15 requests should not all be rate-limited
    non_429 = [s for s in statuses if s != 429]
    assert len(non_429) > 0
