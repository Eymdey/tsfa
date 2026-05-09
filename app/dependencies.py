"""FastAPI dependency functions.

Provides plan resolution from request headers, supporting both
RapidAPI production headers and local development fallback headers.
Also provides API key extraction and Redis-based rate limiting.
"""

import time
from typing import Any

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.credits import RATE_LIMITS


VALID_PLANS: set[str] = {"free", "basic", "pro", "ultra"}


async def verify_rapidapi_proxy(
    request: Request,
    x_rapidapi_proxy_secret: str | None = Header(default=None),
) -> None:
    """Validate the RapidAPI proxy secret header.

    In production (ENVIRONMENT=production):
      - Requires X-RapidAPI-Proxy-Secret == RAPIDAPI_PROXY_SECRET from .env
      - Missing or incorrect secret → HTTP 403
    In development (ENVIRONMENT=development):
      - Skips the check (local/test mode)

    Args:
        request: The incoming FastAPI Request object.
        x_rapidapi_proxy_secret: Value of the X-RapidAPI-Proxy-Secret header.

    Raises:
        HTTPException 403: When in production and the secret is missing or wrong.
    """
    if settings.environment != "production":
        return

    expected = settings.rapidapi_proxy_secret
    if not expected or x_rapidapi_proxy_secret != expected:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "code": "FORBIDDEN",
                "message": "Direct API access is not allowed. Use RapidAPI.",
            },
        )


def get_plan(request: Request) -> str:
    """Resolve the caller's subscription plan from request headers.

    In production (RapidAPI), the plan is encoded in the X-RapidAPI-User
    header or inferred from X-RapidAPI-Proxy-Secret.  For local development
    and testing, the X-Plan header is used as a fallback.

    Args:
        request: The incoming FastAPI Request object.

    Returns:
        One of "free", "basic", "pro", "ultra".  Defaults to "free" when no
        recognizable plan header is present.
    """
    # Production: RapidAPI forwards subscription tier via X-RapidAPI-Subscription
    plan_header: str | None = request.headers.get("X-RapidAPI-Subscription")
    if plan_header and plan_header.lower() in VALID_PLANS:
        return plan_header.lower()

    # Development / testing fallback
    dev_plan: str | None = request.headers.get("X-Plan")
    if dev_plan and dev_plan.lower() in VALID_PLANS:
        return dev_plan.lower()

    return "free"


def get_api_key(request: Request) -> str:
    """Extract a unique caller identifier from the request.

    Resolution order:
    1. X-RapidAPI-User header (production, set by RapidAPI gateway)
    2. X-Forwarded-For header (first IP in chain, behind a proxy)
    3. Direct client host from the TCP connection
    4. "anonymous" as a final fallback

    Args:
        request: The incoming FastAPI Request object.

    Returns:
        A string identifier for the caller.
    """
    rapidapi_user: str | None = request.headers.get("X-RapidAPI-User")
    if rapidapi_user:
        return rapidapi_user

    forwarded_for: str | None = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "anonymous"


async def check_rate_limit(
    request: Request,
    plan: str = Depends(get_plan),
) -> None:
    """Redis-backed per-minute rate limiter.

    Uses a counter key that resets every calendar minute:
        rate:{api_key}:{minute}   where minute = int(time.time() / 60)

    When no Redis client is configured (test/dev), this is a no-op.

    Args:
        request: The incoming FastAPI Request object.
        plan: Resolved subscription plan (injected by get_plan dependency).

    Raises:
        HTTPException 429: When the request count for the current minute
            exceeds the plan's rate limit.  Includes a ``Retry-After: 60``
            header.
    """
    redis_client: Any | None = getattr(request.app.state, "redis", None)
    if redis_client is None:
        return

    api_key = get_api_key(request)
    limit = RATE_LIMITS.get(plan, RATE_LIMITS["free"])
    minute = int(time.time() / 60)
    rate_key = f"rate:{api_key}:{minute}"

    count_raw = await redis_client.incr(rate_key)
    # Set expiry only on first increment to avoid resetting TTL on every request
    if count_raw == 1:
        await redis_client.expire(rate_key, 60)

    if count_raw > limit:
        raise HTTPException(
            status_code=429,
            detail={
                "status": "error",
                "code": "RATE_LIMIT_EXCEEDED",
                "message": (
                    f"Rate limit of {limit} requests/minute exceeded for plan '{plan}'. "
                    "Please slow down your requests."
                ),
                "details": {
                    "limit": limit,
                    "plan": plan,
                    "retry_after": 60,
                },
            },
            headers={"Retry-After": "60"},
        )
