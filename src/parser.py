"""Parse Apple Card statement text into normalized transactions.

Pure text-in / dict-out so it is deterministic and easy to unit test.
PDF -> text extraction lives in src/pdf_text.py.

Real Apple Card layout notes (verified against a real statement):
- The transactions table starts at the first "Transactions" header. The header may
  repeat on later pages (page-break continuation) — those repeats are ignored.
- The table ends at the totals block ("Total Daily Cash this month") which is followed
  by the "Apple Card Monthly Installments" section — neither belongs to transactions.
- The reconciliation control figure is "Total charges, credits and returns" (it nets
  charges, credits and returns), with a fallback to "Total transactions for this period".
"""
import re
from src.merchant import extract_merchant, match_key
from src.money import to_cents

_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_MONEY = re.compile(r"^-?\$[\d,]+\.\d{2}$")
_PCT = re.compile(r"^\d+%$")

# Phrases whose following money line is the transactions control total.
_CONTROL_PHRASES = (
    "Total charges, credits and returns",
    "Total transactions for this period",
)
# Phrases that mark the end of the transactions table.
_STOP_PHRASES = (
    "Total Daily Cash this month",
    "Apple Card Monthly Installments",
    "Total charges, credits and returns",
    "Total transactions for this period",
)


def _money_to_float(s: str) -> float:
    neg = s.strip().startswith("-")
    digits = s.replace("-", "").replace("$", "").replace(",", "").strip()
    val = float(digits)
    return -val if neg else val


def _iso_date(mmddyyyy: str) -> str:
    mm, dd, yyyy = mmddyyyy.split("/")
    return f"{yyyy}-{mm}-{dd}"


def _starts_any(line: str, phrases) -> bool:
    return any(line.startswith(p) for p in phrases)


def parse_applecard(text: str, source: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Start scanning after the FIRST "Transactions" header (after the Payments section).
    start = None
    for i, ln in enumerate(lines):
        if ln == "Transactions":
            start = i + 1
            break
    body = lines[start:] if start is not None else lines

    # Reconciliation control total: money line following a control phrase (search full body).
    reported_total = None
    for i, ln in enumerate(body):
        if _starts_any(ln, _CONTROL_PHRASES):
            for nxt in body[i + 1:]:
                if _MONEY.match(nxt):
                    reported_total = round(_money_to_float(nxt), 2)
                    break
            break

    # Truncate the body at the first stop phrase (end of the transactions table).
    end = len(body)
    for i, ln in enumerate(body):
        if _starts_any(ln, _STOP_PHRASES):
            end = i
            break
    body = body[:end]

    # Group lines into records that begin on a date line.
    records = []
    current = None
    for ln in body:
        if _DATE.match(ln):
            current = [ln]
            records.append(current)
        elif current is not None:
            current.append(ln)

    transactions = []
    excluded = []
    for rec in records:
        date = _iso_date(rec[0])
        # A record may carry a promo sub-line ("3% Daily Cash at <merchant>") AFTER the
        # real amount. Only the lines before that marker belong to the transaction row.
        main_lines = []
        for x in rec[1:]:
            if "Daily Cash at" in x:
                break
            main_lines.append(x)
        moneys = [x for x in main_lines if _MONEY.match(x)]
        if not moneys:
            continue
        amount = round(_money_to_float(moneys[-1]), 2)  # rightmost money col = Amount
        # Description = lines after the date up to the first percentage/money column.
        desc_lines = []
        for x in main_lines:
            if _PCT.match(x) or _MONEY.match(x):
                break
            desc_lines.append(x)
        raw = " ".join(desc_lines).strip()
        merchant = extract_merchant(raw)
        tx = {
            "date": date,
            "rawDescription": raw,
            "merchant": merchant,
            "matchKey": match_key(merchant),
            "amount": amount,
            "source": source,
        }
        if amount <= 0:
            excluded.append(tx)
        else:
            transactions.append(tx)

    # Reconcile the NET of all rows (charges minus credits/returns) to the control total.
    net_cents = sum(to_cents(t["amount"]) for t in transactions) \
        + sum(to_cents(t["amount"]) for t in excluded)
    reconciles = (reported_total is not None
                  and net_cents == to_cents(reported_total))

    return {
        "transactions": transactions,
        "excluded": excluded,
        "reportedTotal": reported_total,
        "sumOfTransactions": round(sum(to_cents(t["amount"]) for t in transactions) / 100, 2),
        "netTotal": round(net_cents / 100, 2),
        "reconciles": reconciles,
    }
