"""Immutable HTML snapshots of the full review state, for the History view.

A snapshot captures EVERYONE's expenses + totals at a moment in time. Snapshots are
deduplicated by a content fingerprint: identical state -> same fingerprint -> reuse.
"""
import hashlib
import html as _html
import json

from src.splitter import compute_shares
from src.money import to_cents, to_dollars
from src.reports import per_person_totals, owner_total, total_spent, statements_included

_CAT_ORDER = ["Coffee", "Grocery", "Restaurants", "Beauty", "Shopping", "Transport", "Subscriptions"]


def _shares_key(e):
    sh = e["split"].get("shares")
    if isinstance(sh, str):
        return sh
    return tuple(sorted((k, f"{float(v):.2f}") for k, v in sh.items()))


def fingerprint(expenses, people) -> str:
    rows = sorted(
        (e["id"], e["status"], f"{e['amount']:.2f}", e["category"],
         tuple(sorted(e["split"].get("participants", []))),
         bool(e["split"].get("includeSelf")), _shares_key(e))
        for e in expenses)
    payload = json.dumps({"people": sorted((p["id"], p["name"]) for p in people), "rows": rows},
                         sort_keys=True, default=str)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def _cat_rank(name):
    if name == "Miscellaneous":
        return 999
    try:
        return _CAT_ORDER.index(name)
    except ValueError:
        return 500


def _esc(s):
    return _html.escape(str(s))


def render_html(expenses, people, generated_on) -> str:
    name_by = {p["id"]: p["name"] for p in people}
    totals = per_person_totals(expenses)
    you = owner_total(expenses)
    spent = total_spent(expenses)
    stmts = statements_included(expenses)

    def shares_str(e):
        if e["status"] == "personal":
            return "Just you"
        sh = compute_shares(e)
        your_cents = to_cents(e["amount"]) - sum(to_cents(v) for v in sh.values())
        parts = [f"You ${to_dollars(your_cents):.2f}"]
        for pid, v in sh.items():
            parts.append(f"{_esc(name_by.get(pid, pid))} ${v:.2f}")
        return "; ".join(parts)

    cats = sorted({e["category"] for e in expenses}, key=lambda c: (_cat_rank(c), c))
    groups = ""
    for c in cats:
        rows = [e for e in expenses if e["category"] == c]
        sub = sum(e["amount"] for e in rows)
        body = ""
        for e in rows:
            status = "Personal" if e["status"] == "personal" else "Split"
            body += (f"<tr><td>{_esc(e['date'])}</td><td>{_esc(e['merchant'])}</td>"
                     f"<td>{_esc(e.get('source', ''))}</td>"
                     f"<td class='r'>${e['amount']:.2f}</td><td>{status}</td>"
                     f"<td>{shares_str(e)}</td></tr>")
        groups += (f"<h3>{_esc(c)} <small>{len(rows)} item(s) · ${sub:.2f}</small></h3>"
                   f"<table><thead><tr><th>Date</th><th>Merchant</th><th>Statement</th>"
                   f"<th class='r'>Amount</th><th>Status</th><th>Shares</th></tr></thead>"
                   f"<tbody>{body}</tbody></table>")

    owed = "".join(f"<li>{_esc(name_by.get(pid, pid))} owes you <b>${amt:.2f}</b></li>"
                   for pid, amt in totals.items()) or "<li>No split expenses</li>"
    stmts_html = "; ".join(_esc(s) for s in stmts) or "(none)"

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Splitsy snapshot — {_esc(generated_on)}</title>
<style>
body{{font-family:-apple-system,system-ui,sans-serif;margin:24px;color:#241f22;}}
h1{{margin:0 0 2px;}} .meta{{color:#867c81;font-size:13px;margin-bottom:16px;}}
.summary{{background:#fff4f9;border:1px solid #ffd6e6;border-radius:12px;padding:14px 18px;margin-bottom:20px;}}
.summary b{{font-variant-numeric:tabular-nums;}} .summary ul{{margin:6px 0 0;}}
h3{{margin:18px 0 6px;}} h3 small{{color:#867c81;font-weight:400;}}
table{{border-collapse:collapse;width:100%;margin-bottom:8px;font-size:13px;}}
th,td{{border-bottom:1px solid #eee;padding:6px 8px;text-align:left;vertical-align:top;}}
td.r,th.r{{text-align:right;font-variant-numeric:tabular-nums;}}
</style></head><body>
<h1>Splitsy — expense snapshot</h1>
<div class="meta">Generated {_esc(generated_on)} · Statements: {stmts_html}</div>
<div class="summary">
  <div>Total spent: <b>${spent:.2f}</b></div>
  <div>You pay: <b>${you:.2f}</b></div>
  <ul>{owed}</ul>
</div>
{groups}
<p class="meta">Immutable snapshot of the full review state at the time of export.</p>
</body></html>"""
