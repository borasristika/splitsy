"""Per-person totals and CSV exports built from computed shares."""
import csv as csvlib
import io
from src.money import to_cents, to_dollars
from src.splitter import compute_shares


def per_person_totals(expenses: list) -> dict:
    totals_cents = {}
    for e in expenses:
        for pid, amount in compute_shares(e).items():
            totals_cents[pid] = totals_cents.get(pid, 0) + to_cents(amount)
    return {pid: to_dollars(c) for pid, c in totals_cents.items()}


def owner_total(expenses: list) -> float:
    """The owner's ('You') own share across all expenses, in exact cents.

    Personal expenses are fully the owner's; for split expenses the owner's share is
    the amount minus everyone else's shares. By construction owner_total plus the sum
    of per_person_totals always equals the sum of all expense amounts.
    """
    cents = 0
    for e in expenses:
        amount_cents = to_cents(e["amount"])
        if e.get("status") == "personal":
            cents += amount_cents
        elif e.get("status") == "split":
            others = sum(to_cents(v) for v in compute_shares(e).values())
            cents += amount_cents - others
    return to_dollars(cents)


def _fmt(amount: float) -> str:
    return f"{amount:.2f}"


def per_person_csv(expenses: list, person_id: str, people: list) -> str:
    out = io.StringIO()
    w = csvlib.writer(out)
    w.writerow(["Date", "Merchant", "Category", "Total", "Your Share"])
    for e in expenses:
        shares = compute_shares(e)
        if person_id in shares:
            w.writerow([e["date"], e["merchant"], e["category"],
                        _fmt(e["amount"]), _fmt(shares[person_id])])
    return out.getvalue()


def combined_csv(expenses: list, people: list) -> str:
    out = io.StringIO()
    w = csvlib.writer(out)
    names = [p["name"] for p in people]
    ids = [p["id"] for p in people]
    w.writerow(["Date", "Merchant", "Category", "Total"] + names)
    for e in expenses:
        shares = compute_shares(e)
        if not shares:
            continue
        row = [e["date"], e["merchant"], e["category"], _fmt(e["amount"])]
        row += [_fmt(shares.get(pid, 0.0)) for pid in ids]
        w.writerow(row)
    return out.getvalue()
