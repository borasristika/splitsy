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


def total_spent(expenses: list) -> float:
    """Sum of every charge across the given expenses (what actually hit your cards),
    regardless of how it was split. Exact to the cent."""
    return to_dollars(sum(to_cents(e["amount"]) for e in expenses))


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


def _person_name(people: list, pid: str) -> str:
    for p in people:
        if p["id"] == pid:
            return p["name"]
    return str(pid)


def statements_included(expenses: list) -> list:
    """Distinct statement sources present, sorted — what the export covers."""
    return sorted({e.get("source", "") for e in expenses if e.get("source")})


def per_person_csv(expenses: list, person_id: str, people: list, generated_on=None) -> str:
    name = _person_name(people, person_id)
    out = io.StringIO()
    w = csvlib.writer(out)
    rows, total_cents = [], 0
    for e in expenses:
        shares = compute_shares(e)
        if person_id in shares:
            rows.append([e["date"], e["merchant"], e["category"], e.get("source", ""),
                         _fmt(e["amount"]), _fmt(shares[person_id])])
            total_cents += to_cents(shares[person_id])
    stmts = statements_included(expenses)
    w.writerow([f"Expense split summary for {name}"])
    w.writerow(["Statements included", "; ".join(stmts) or "(none)"])
    if generated_on:
        w.writerow(["Generated", generated_on])
    w.writerow([])
    w.writerow(["Date", "Merchant", "Category", "Statement", "Total", f"{name}'s share"])
    for r in rows:
        w.writerow(r)
    w.writerow([])
    w.writerow(["TOTAL", "", "", "", "", _fmt(to_dollars(total_cents))])
    return out.getvalue()


def combined_csv(expenses: list, people: list, generated_on=None) -> str:
    out = io.StringIO()
    w = csvlib.writer(out)
    names = [p["name"] for p in people]
    ids = [p["id"] for p in people]
    totals = {pid: 0 for pid in ids}
    stmts = statements_included(expenses)
    w.writerow(["Combined expense split summary"])
    w.writerow(["Statements included", "; ".join(stmts) or "(none)"])
    if generated_on:
        w.writerow(["Generated", generated_on])
    w.writerow([])
    w.writerow(["Date", "Merchant", "Category", "Statement", "Total"] + names)
    for e in expenses:
        shares = compute_shares(e)
        if not shares:
            continue
        row = [e["date"], e["merchant"], e["category"], e.get("source", ""), _fmt(e["amount"])]
        for pid in ids:
            amt = shares.get(pid, 0.0)
            totals[pid] += to_cents(amt)
            row.append(_fmt(amt))
        w.writerow(row)
    w.writerow([])
    w.writerow(["TOTAL", "", "", "", ""] + [_fmt(to_dollars(totals[pid])) for pid in ids])
    return out.getvalue()
