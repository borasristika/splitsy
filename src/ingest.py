"""Orchestrate parse -> build expenses -> dedup -> verification report."""
from src.parser import parse_applecard
from src.expense import make_expense


def ingest_text(text: str, source: str, existing: list, rules: dict, settings: dict) -> dict:
    parsed = parse_applecard(text, source=source)
    new_expenses = [make_expense(tx, rules, settings) for tx in parsed["transactions"]]

    existing_ids = {e["id"] for e in existing}
    merged = list(existing)
    added = 0
    for e in new_expenses:
        if e["id"] not in existing_ids:
            merged.append(e)
            existing_ids.add(e["id"])
            added += 1

    report = {
        "source": source,
        "count": len(new_expenses),
        "added": added,
        "reportedTotal": parsed["reportedTotal"],
        "sumOfTransactions": parsed["sumOfTransactions"],
        "reconciles": parsed["reconciles"],
        "excludedCount": len(parsed["excluded"]),
    }
    return {"expenses": merged, "report": report}
