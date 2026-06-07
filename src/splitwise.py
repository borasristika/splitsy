"""Minimal Splitwise API client (stdlib only) + pure payload builder.

Auth: a personal API key (bearer token) from https://secure.splitwise.com/apps.
Only the payload builder is unit-tested; the network calls are thin wrappers the
user exercises live with their own token.
"""
import json
import os
import urllib.parse
import urllib.request

from src.money import to_cents, to_dollars
from src.splitter import compute_shares

BASE = "https://secure.splitwise.com/api/v3.0"


class SplitwiseError(Exception):
    pass


def _auth_headers(token: str) -> dict:
    # Splitwise (behind a CDN) returns 403 / error 1010 for the default
    # "Python-urllib" User-Agent, so we must send a normal one.
    return {"Authorization": f"Bearer {token}", "User-Agent": "ExpenseSplitter/1.0"}


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
    """POST create_expense (urlencoded); return the new Splitwise expense id."""
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


def build_summary_payload(cost_dollars, my_user_id, friend_user_id, description,
                          group_id=0, details="", currency_code="USD") -> dict:
    """A single 'IOU' expense: you paid the full cost, the friend owes all of it."""
    cost = f"{cost_dollars:.2f}"
    return {
        "cost": cost,
        "description": description,
        "details": details,
        "group_id": int(group_id or 0),
        "currency_code": currency_code,
        "users__0__user_id": my_user_id,
        "users__0__paid_share": cost,
        "users__0__owed_share": "0.00",
        "users__1__user_id": friend_user_id,
        "users__1__paid_share": "0.00",
        "users__1__owed_share": cost,
    }


def _multipart(fields: dict, file_field=None, file_name=None, file_bytes=None,
               file_type="application/pdf"):
    boundary = "----expensesplitter" + os.urandom(8).hex()
    crlf = "\r\n"
    parts = []
    for k, v in fields.items():
        parts.append((f'--{boundary}{crlf}'
                      f'Content-Disposition: form-data; name="{k}"{crlf}{crlf}{v}{crlf}').encode())
    if file_bytes is not None:
        parts.append((f'--{boundary}{crlf}'
                      f'Content-Disposition: form-data; name="{file_field}"; filename="{file_name}"{crlf}'
                      f'Content-Type: {file_type}{crlf}{crlf}').encode())
        parts.append(file_bytes)
        parts.append(crlf.encode())
    parts.append(f'--{boundary}--{crlf}'.encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


def create_expense_with_receipt(token: str, params: dict, receipt_bytes=None,
                                receipt_filename="summary.pdf"):
    """create_expense with an optional file attachment (multipart). Returns expense id."""
    if not receipt_bytes:
        return create_expense(token, params)
    str_fields = {k: str(v) for k, v in params.items()}
    ctype, body = _multipart(str_fields, "receipt", receipt_filename, receipt_bytes)
    headers = dict(_auth_headers(token))
    headers["Content-Type"] = ctype
    req = urllib.request.Request(f"{BASE}/create_expense", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SplitwiseError(f"create_expense HTTP {e.code}: {e.read().decode()[:200]}")
    if resp.get("errors"):
        raise SplitwiseError(f"create_expense rejected: {resp['errors']}")
    return resp["expenses"][0]["id"]


def create_comment(token: str, expense_id, content: str):
    """Add a comment to an expense."""
    data = urllib.parse.urlencode({"expense_id": expense_id, "content": content}).encode()
    req = urllib.request.Request(f"{BASE}/create_comment", data=data, headers=_auth_headers(token))
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SplitwiseError(f"create_comment HTTP {e.code}: {e.read().decode()[:200]}")
    if resp.get("errors"):
        raise SplitwiseError(f"create_comment rejected: {resp['errors']}")
    return resp.get("comment", {}).get("id")
