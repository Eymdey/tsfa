"""Backtesting / validation service stub.

Provides the interface for cross-validation of forecasting models.
Full implementation is planned for Phase 1 Week 3.
"""

from app.schemas.validate import ValidateRequest, ValidateResponse


async def run_backtest(request: ValidateRequest) -> ValidateResponse:
    """Execute a cross-validated backtesting run on the provided series.

    Args:
        request: Validated ValidateRequest.

    Returns:
        ValidateResponse with per-window and aggregate metrics.

    Raises:
        NotImplementedError: Always — backtesting is not yet implemented.
    """
    raise NotImplementedError(
        "Backtesting (/v1/validate) is not yet implemented. Coming in Phase 1 Week 3."
    )
