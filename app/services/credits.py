"""Credit calculation utilities.

Provides a static mapping from model name to credits per API call,
as specified in the project billing rules (section 3).
"""

# Static credits-per-call table (spec section 3)
_CREDITS_TABLE: dict[str, int] = {
    "arima": 1,
    "chronos": 1,
    "lstm": 2,
    "tide": 3,
    "ensemble": 5,
}

_DEFAULT_CREDITS: int = 1


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
