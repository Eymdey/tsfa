"""Usage router — GET /v1/usage endpoint.

Returns credit consumption and plan limits for the current billing period.
Phase 1: returns mocked data. Phase 2: connected to persistent storage.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.dependencies import get_plan
from app.schemas.common import UsageResponse

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get(
    "",
    response_model=UsageResponse,
    summary="Get current plan usage",
    description=(
        "Returns credit usage and limits for the current billing period. "
        "Phase 1: returns mocked data with credits_used=0."
    ),
)
async def get_usage(
    request: Request,
    plan: str = Depends(get_plan),
) -> UsageResponse:
    """Return current credit usage for the caller's plan.

    Args:
        request: FastAPI Request.
        plan: Resolved subscription plan.

    Returns:
        UsageResponse with current period credits and limits.
    """
    # Resolve credits limit from config
    credits_limit_map: dict[str, int] = {
        "free": settings.plan_free_credits,
        "basic": settings.plan_basic_credits,
        "pro": settings.plan_pro_credits,
        "ultra": settings.plan_ultra_credits,
    }
    credits_limit = credits_limit_map.get(plan, settings.plan_free_credits)

    # Phase 1: mocked usage data
    today = date.today()
    period = today.strftime("%Y-%m")

    # Compute next month's first day as reset date
    if today.month == 12:
        reset_date = date(today.year + 1, 1, 1)
    else:
        reset_date = date(today.year, today.month + 1, 1)

    return UsageResponse(
        plan=plan,
        period=period,
        credits_used=0,
        credits_limit=credits_limit,
        credits_remaining=credits_limit,
        reset_date=str(reset_date),
        requests_count=0,
    )
