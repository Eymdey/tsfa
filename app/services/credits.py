"""Credit calculation utilities and Redis-backed CreditsService.

Provides:
- Static mapping from model name to credits per call.
- CreditsService: Redis-backed class for tracking and enforcing monthly credit limits.
"""

import time
from datetime import date
from typing import Any

from fastapi import HTTPException

from app.config import settings as _settings


# Static credits-per-call table (spec section 3)
_CREDITS_TABLE: dict[str, int] = {
    "arima": 1,
    "chronos": 1,
    "lstm": 2,
    "tide": 3,
    "ensemble": 5,
}

_DEFAULT_CREDITS: int = 1

# Rate limits per plan (requests per minute)
RATE_LIMITS: dict[str, int] = {
    "free": 10,
    "basic": 30,
    "pro": 100,
    "ultra": 300,
}

# Plan credit limits per month
PLAN_LIMITS: dict[str, int] = {
    "free": _settings.plan_free_credits,
    "basic": _settings.plan_basic_credits,
    "pro": _settings.plan_pro_credits,
    "ultra": _settings.plan_ultra_credits,
}


def get_credits_for_model(model: str) -> int:
    """Return the number of credits consumed by a single call to the given model.

    Args:
        model: Lowercase model name, e.g. 'arima', 'chronos', 'lstm'.

    Returns:
        Integer credit cost.  Unknown models default to 1 credit.
    """
    return _CREDITS_TABLE.get(model.lower(), _DEFAULT_CREDITS)


def get_credits_for_batch(model: str, n_series: int) -> int:
    """Return credits for a batch forecast (N × credits_per_model).

    Args:
        model: Model name.
        n_series: Number of series in the batch.

    Returns:
        Total credit cost.
    """
    return get_credits_for_model(model) * max(1, n_series)


def get_credits_for_validation(model: str, n_windows: int) -> int:
    """Return credits for a backtesting job (N windows × credits_per_model).

    Args:
        model: Model name.
        n_windows: Number of cross-validation windows.

    Returns:
        Total credit cost.
    """
    return get_credits_for_model(model) * max(1, n_windows)


class CreditsService:
    """Redis-backed service for tracking monthly credit consumption.

    Redis key schema:
        credits:{api_key}:{YYYY-MM}   — cumulative credits consumed
        requests:{api_key}:{YYYY-MM}  — cumulative request count

    When redis_client is None (test/dev environment), all operations are
    no-ops and usage is reported as zero.
    """

    _TTL_SECONDS: int = 35 * 24 * 3600  # 35-day expiry (covers full month + buffer)

    def __init__(self, redis_client: Any | None) -> None:
        """Initialise with an optional Redis client.

        Args:
            redis_client: An async Redis client (redis.asyncio), or None to
                          disable Redis persistence (test mode).
        """
        self._redis = redis_client

    def _plan_limit(self, plan: str) -> int:
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    @staticmethod
    def _period() -> str:
        return date.today().strftime("%Y-%m")

    async def consume(self, api_key: str, plan: str, credits: int) -> None:
        """Consume credits for a request, raising HTTP 429 if the limit is exceeded.

        This method is a no-op when no Redis client is configured.

        Args:
            api_key: Unique identifier for the caller (RapidAPI user or IP).
            plan: Subscription plan name ('free', 'basic', 'pro', 'ultra').
            credits: Number of credits to consume.

        Raises:
            HTTPException 429: When consuming *credits* would exceed the plan limit.
        """
        if self._redis is None:
            return

        period = self._period()
        credits_key = f"credits:{api_key}:{period}"
        requests_key = f"requests:{api_key}:{period}"
        limit = self._plan_limit(plan)

        # Check current usage before incrementing
        current_raw = await self._redis.get(credits_key)
        current_credits = int(current_raw) if current_raw else 0

        if current_credits + credits > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "status": "error",
                    "code": "CREDIT_LIMIT_EXCEEDED",
                    "message": (
                        f"Monthly credit limit of {limit} reached for plan '{plan}'. "
                        "Upgrade your plan or wait for the next billing period."
                    ),
                    "details": {
                        "credits_used": current_credits,
                        "credits_limit": limit,
                        "credits_remaining": max(0, limit - current_credits),
                        "period": period,
                    },
                },
            )

        # Atomically increment both keys
        pipe = self._redis.pipeline(transaction=True)
        pipe.incrby(credits_key, credits)
        pipe.incr(requests_key)
        pipe.expire(credits_key, self._TTL_SECONDS)
        pipe.expire(requests_key, self._TTL_SECONDS)
        await pipe.execute()

    async def get_usage(self, api_key: str, plan: str) -> dict[str, Any]:
        """Retrieve current credit and request usage for this billing period.

        Args:
            api_key: Unique identifier for the caller.
            plan: Subscription plan name.

        Returns:
            Dict with keys: credits_used, credits_limit, credits_remaining,
            requests_count, period.
        """
        period = self._period()
        limit = self._plan_limit(plan)

        if self._redis is None:
            return {
                "credits_used": 0,
                "credits_limit": limit,
                "credits_remaining": limit,
                "requests_count": 0,
                "period": period,
            }

        credits_key = f"credits:{api_key}:{period}"
        requests_key = f"requests:{api_key}:{period}"

        credits_raw, requests_raw = await self._redis.mget(credits_key, requests_key)
        credits_used = int(credits_raw) if credits_raw else 0
        requests_count = int(requests_raw) if requests_raw else 0

        return {
            "credits_used": credits_used,
            "credits_limit": limit,
            "credits_remaining": max(0, limit - credits_used),
            "requests_count": requests_count,
            "period": period,
        }
