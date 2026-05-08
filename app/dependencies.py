"""FastAPI dependency functions.

Provides plan resolution from request headers, supporting both
RapidAPI production headers and local development fallback headers.
"""

from fastapi import Request


VALID_PLANS: set[str] = {"free", "basic", "pro", "ultra"}


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
    # Production: RapidAPI forwards plan info via X-RapidAPI-User
    rapidapi_user: str | None = request.headers.get("X-RapidAPI-User")
    if rapidapi_user:
        # RapidAPI encodes subscription as part of the user header in some
        # gateway configurations.  Here we parse the plan from a dedicated
        # header forwarded by our RapidAPI transformer.
        plan_header: str | None = request.headers.get("X-RapidAPI-Subscription")
        if plan_header and plan_header.lower() in VALID_PLANS:
            return plan_header.lower()

    # Development / testing fallback
    dev_plan: str | None = request.headers.get("X-Plan")
    if dev_plan and dev_plan.lower() in VALID_PLANS:
        return dev_plan.lower()

    return "free"
