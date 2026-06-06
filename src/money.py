"""Integer-cent money helpers so split math never drifts due to float error."""
from decimal import Decimal, ROUND_HALF_UP


def to_cents(dollars) -> int:
    """Convert a dollar amount to integer cents, rounding half up."""
    return int((Decimal(str(dollars)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_dollars(cents: int) -> float:
    """Convert integer cents back to a 2-decimal float dollar amount."""
    return float(Decimal(cents) / 100)


def split_equal(total_cents: int, n: int) -> list:
    """Split total_cents into n parts that sum exactly to total_cents.

    Remainder cents are handed to the earliest shares so the result is
    deterministic and always reconciles.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    base = total_cents // n
    remainder = total_cents - base * n
    return [base + (1 if i < remainder else 0) for i in range(n)]
