"""Compute per-person shares for an expense. Owner is never in the output."""
from src.money import to_cents, to_dollars, split_equal


def compute_shares(expense: dict) -> dict:
    if expense.get("status") != "split":
        return {}
    split = expense["split"]
    participants = list(split.get("participants", []))
    shares = split.get("shares", "equal")
    amount_cents = to_cents(expense["amount"])

    if shares != "equal":
        # custom dollar amounts per participant; must sum to the expense amount
        custom_cents = {pid: to_cents(v) for pid, v in shares.items()}
        if sum(custom_cents.values()) != amount_cents:
            raise ValueError("custom shares do not reconcile to the expense amount")
        return {pid: to_dollars(c) for pid, c in custom_cents.items()}

    n = len(participants) + (1 if split.get("includeSelf") else 0)
    if n == 0:
        return {}
    parts = split_equal(amount_cents, n)
    # Owner (if included) takes the first share (and thus any remainder cent);
    # participants take the rest in order.
    offset = 1 if split.get("includeSelf") else 0
    return {pid: to_dollars(parts[offset + i]) for i, pid in enumerate(participants)}
