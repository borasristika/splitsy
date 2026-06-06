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
