"""Minimal Splitwise API client (stdlib only) + pure payload builder.

Auth: a personal API key (bearer token) from https://secure.splitwise.com/apps.
Only the payload builder is unit-tested; the network calls are thin wrappers the
user exercises live with their own token.
"""
import json
import urllib.parse
import urllib.request

from src.money import to_cents, to_dollars
from src.splitter import compute_shares

BASE = "https://secure.splitwise.com/api/v3.0"


class SplitwiseError(Exception):
    pass


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get(token: str, path: str) -> dict:
    req = urllib.request.Request(f"{BASE}/{path}", headers=_auth_headers(token))
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SplitwiseError(f"{path} failed: HTTP {e.code} {e.read().decode()[:200]}")


def get_current_user(token: str) -> dict:
    return _get(token, "get_current_user")["user"]


def get_friends(token: str) -> list:
    return _get(token, "get_friends")["friends"]


def get_groups(token: str) -> list:
    return _get(token, "get_groups")["groups"]


def build_expense_payload(expense: dict, my_user_id, person_to_splitwise: dict,
                          group_id=0, currency_code: str = "USD") -> dict:
    """Build form params for create_expense.

    You are the payer (paid_share = full cost); each participant owes their computed
    share. owed_shares sum exactly to the cost by construction (your share absorbs the
    rounding remainder, matching the in-app totals).
    """
    shares = compute_shares(expense)  # {personId: dollars} for participants
    amount_cents = to_cents(expense["amount"])
    part_cents = {pid: to_cents(v) for pid, v in shares.items()}
    my_cents = amount_cents - sum(part_cents.values())
    if my_cents < 0:
        raise SplitwiseError("participant shares exceed the expense amount")

    cost = f"{expense['amount']:.2f}"
    params = {
        "cost": cost,
        "description": expense.get("merchant") or expense.get("rawDescription") or "Expense",
        "date": expense["date"],
        "group_id": int(group_id or 0),
        "currency_code": currency_code,
        "users__0__user_id": my_user_id,
        "users__0__paid_share": cost,
        "users__0__owed_share": f"{to_dollars(my_cents):.2f}",
    }
    i = 1
    for pid, cents in part_cents.items():
        sw_id = person_to_splitwise.get(pid)
        if not sw_id:
            raise SplitwiseError(f"no Splitwise user mapped for person '{pid}'")
        params[f"users__{i}__user_id"] = sw_id
        params[f"users__{i}__paid_share"] = "0.00"
        params[f"users__{i}__owed_share"] = f"{to_dollars(cents):.2f}"
        i += 1
    return params


def create_expense(token: str, params: dict):
    """POST create_expense; return the new Splitwise expense id."""
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{BASE}/create_expense", data=data,
                                 headers=_auth_headers(token))
    try:
        with urllib.request.urlopen(req) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SplitwiseError(f"create_expense HTTP {e.code}: {e.read().decode()[:200]}")
    errors = body.get("errors")
    if errors:
        raise SplitwiseError(f"create_expense rejected: {errors}")
    return body["expenses"][0]["id"]
