"""Usage router — GET /v1/usage endpoint.

Returns credit consumption and plan limits for the current billing period.
"""

from datetime import date

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_plan, get_api_key
from app.schemas.common import UsageResponse
from app.services.credits import CreditsService

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get(
    "",
    response_model=UsageResponse,
    summary="Get current plan usage",
    description=(
        "Returns credit usage and limits for the current billing period."
    ),
)
async def get_usage(
    request: Request,
    plan: str = Depends(get_plan),
    api_key: str = Depends(get_api_key),
) -> UsageResponse:
    """Return current credit usage for the caller's plan."""
    redis_client = getattr(request.app.state, "redis", None)
    service = CreditsService(redis_client)
    usage = await service.get_usage(api_key, plan)

    today = date.today()
    if today.month == 12:
        reset_date = date(today.year + 1, 1, 1)
    else:
        reset_date = date(today.year, today.month + 1, 1)

    return UsageResponse(
        plan=plan,
        period=usage["period"],
        credits_used=usage["credits_used"],
        credits_limit=usage["credits_limit"],
        credits_remaining=usage["credits_remaining"],
        reset_date=str(reset_date),
        requests_count=usage["requests_count"],
    )
