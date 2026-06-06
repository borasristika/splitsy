"""Build full Expense records from parsed transactions, applying rules + defaults."""
import hashlib
from src.categories import guess_category


def expense_id(tx: dict) -> str:
    key = f"{tx['source']}|{tx['date']}|{tx['rawDescription']}|{tx['amount']}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def make_expense(tx: dict, rules: dict, settings: dict) -> dict:
    rule = rules.get(tx["matchKey"])

    # status
    if rule and rule.get("handling") == "personal":
        status = "personal"
    else:
        status = "split"  # default, including when rule says "split"

    # category: rule wins, else keyword guess
    if rule and rule.get("category"):
        category = rule["category"]
    else:
        category = guess_category(tx["merchant"])

    partner = settings.get("defaultPartnerId")
    participants = [partner] if partner else []

    return {
        "id": expense_id(tx),
        "date": tx["date"],
        "merchant": tx["merchant"],
        "matchKey": tx["matchKey"],
        "rawDescription": tx["rawDescription"],
        "amount": tx["amount"],
        "source": tx["source"],
        "category": category,
        "status": status,
        "split": {
            "participants": participants,
            "includeSelf": True,
            "shares": "equal",
        },
    }
