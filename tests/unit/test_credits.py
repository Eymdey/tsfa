"""Unit tests for CreditsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.credits import CreditsService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_redis(get_value=None, mget_values=None):
    """Return a mock async Redis client."""
    r = MagicMock()
    r.get = AsyncMock(return_value=get_value)
    r.mget = AsyncMock(return_value=mget_values if mget_values is not None else [None, None])
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock(return_value=True)
    r.pipeline = MagicMock()
    pipe = MagicMock()
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=False)
    pipe.incr = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[1, True, 1, True])
    r.pipeline.return_value = pipe
    return r


# ---------------------------------------------------------------------------
# get_usage — no Redis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_usage_no_redis_returns_zeros():
    """Without Redis, get_usage returns zeroed counters."""
    service = CreditsService(None)
    usage = await service.get_usage("test_key", "free")
    assert usage["credits_used"] == 0
    assert usage["requests_count"] == 0
    assert usage["credits_remaining"] == usage["credits_limit"]


@pytest.mark.asyncio
async def test_get_usage_no_redis_free_limit():
    service = CreditsService(None)
    usage = await service.get_usage("k", "free")
    assert usage["credits_limit"] > 0
    assert "period" in usage


@pytest.mark.asyncio
async def test_get_usage_pro_limit_higher_than_free():
    service = CreditsService(None)
    free = await service.get_usage("k", "free")
    pro = await service.get_usage("k", "pro")
    assert pro["credits_limit"] > free["credits_limit"]


# ---------------------------------------------------------------------------
# get_usage — with Redis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_usage_with_redis_reads_values():
    r = make_redis(mget_values=["42", "7"])
    service = CreditsService(r)
    usage = await service.get_usage("api_key_1", "pro")
    assert usage["credits_used"] == 42
    assert usage["requests_count"] == 7


@pytest.mark.asyncio
async def test_get_usage_redis_returns_none_defaults_zero():
    r = make_redis(mget_values=[None, None])
    service = CreditsService(r)
    usage = await service.get_usage("api_key_1", "basic")
    assert usage["credits_used"] == 0
    assert usage["requests_count"] == 0


# ---------------------------------------------------------------------------
# consume — no Redis (no-op)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consume_no_redis_is_noop():
    """consume() must not raise when Redis is None."""
    service = CreditsService(None)
    await service.consume("key", "free", 1)  # should not raise


# ---------------------------------------------------------------------------
# consume — with Redis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consume_increments_credits():
    r = make_redis()
    service = CreditsService(r)
    await service.consume("key", "pro", 2)
    # pipeline.execute should have been called
    pipe = r.pipeline.return_value
    pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_consume_calls_incr_with_credits_key():
    r = make_redis()
    service = CreditsService(r)
    await service.consume("mykey", "ultra", 5)
    pipe = r.pipeline.return_value
    # At least one incr call should have been made on the pipe
    assert pipe.incr.called


# ---------------------------------------------------------------------------
# period key format
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_usage_period_format():
    service = CreditsService(None)
    usage = await service.get_usage("k", "free")
    import re
    assert re.match(r"^\d{4}-\d{2}$", usage["period"]), f"Bad period: {usage['period']}"
