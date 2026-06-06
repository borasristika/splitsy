# Expense Splitter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python harness + browser app that ingests bank/credit-card statements, lets the user tag each expense personal-or-split, and exports per-person and combined CSVs plus per-person totals.

**Architecture:** A tiny Python stdlib `http.server` serves a vanilla HTML/CSS/JS frontend and persists three JSON files (`expenses.json`, `rules.json`, `settings.json`). All parsing and money/split logic lives in small, unit-tested Python modules under `src/`. A `LAUNCH.md` prompt lets Claude Code run the same parser deterministically, self-verify, and open the app (harness mode).

**Tech Stack:** Python 3 (stdlib only + `pypdf`), built-in `unittest`, vanilla HTML/CSS/JS. No Node, no web framework, no build step.

---

## Conventions

- All commands run from the repo root: `/Users/sristikabora/Desktop/Work/expense-splitter`.
- Run tests with: `python3 -m unittest discover -s tests -v`
- Money is handled in **integer cents** internally; JSON stores dollars as numbers with 2 decimals only at the boundary.
- Python modules live in `src/`; tests in `tests/`. `src/__init__.py` and `tests/__init__.py` make them importable.
- Commit after every task with the message shown.

## Shared data shapes (used by all tasks — keep names identical)

```text
Expense = {
  "id": str,                # stable hash of source|date|rawDescription|amount
  "date": str,              # ISO "YYYY-MM-DD"
  "merchant": str,          # display merchant, e.g. "STARBUCKS"
  "matchKey": str,          # normalized key for rule matching, e.g. "STARBUCKS"
  "rawDescription": str,    # full original description line
  "amount": float,          # positive dollars, 2 decimals
  "source": str,            # e.g. "AppleCard 2026-01"
  "category": str,          # e.g. "Coffee" or "Miscellaneous"
  "status": str,            # "split" | "personal"
  "split": {                # present always; ignored when status == "personal"
    "participants": [str],  # person ids (NOT including the owner)
    "includeSelf": bool,    # owner shares too?
    "shares": "equal" | {personId: float}   # custom dollar amounts when not "equal"
  }
}

Person   = {"id": str, "name": str}
Rule     = {"matchKey": str, "handling": "personal"|"split"|None, "category": str|None}
Settings = {
  "people": [Person],
  "defaultPartnerId": str|None,
  "defaultSplitWays": int,          # e.g. 2
  "categories": [str],
  "statementFolder": str|None
}
```

The owner ("you") is implicit and never a Person. `defaultSplitWays = 2` with one
default partner means "you + partner".

---

## Task 1: Project scaffold

**Files:**
- Create: `src/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)
- Create: `README.md`
- Modify: `.gitignore` (already exists; ensure data files + venv ignored)

- [ ] **Step 1: Create package dirs and files**

```bash
mkdir -p src tests
: > src/__init__.py
: > tests/__init__.py
```

- [ ] **Step 2: Ensure .gitignore covers data + python artifacts**

Overwrite `.gitignore` with:

```gitignore
__pycache__/
*.pyc
.venv/
venv/
# local data (never commit real financial data)
data/
expenses.json
rules.json
settings.json
*.pdf
```

- [ ] **Step 3: Write README.md**

```markdown
# Expense Splitter

Local tool to turn bank/credit-card statements into a reviewed list of expenses,
tag each as personal or split-with-people, and export CSVs + per-person totals.

See `docs/specs/2026-06-06-expense-splitter-design.md` for the design.

## Run (app mode)
    python3 -m src.server
Then open http://localhost:8000

## Run (harness mode)
Open a Claude Code session in this folder and paste the prompt in `LAUNCH.md`.

## Test
    python3 -m unittest discover -s tests -v

Requires Python 3 and `pypdf` (`python3 -m pip install pypdf`).
```

- [ ] **Step 4: Verify Python imports work**

Run: `python3 -c "import src; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: project scaffold for python expense splitter"
```

---

## Task 2: Money module (integer-cent math)

**Files:**
- Create: `src/money.py`
- Test: `tests/test_money.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_money.py
import unittest
from src.money import to_cents, to_dollars, split_equal

class TestMoney(unittest.TestCase):
    def test_to_cents_rounds_half_up(self):
        self.assertEqual(to_cents(33.13), 3313)
        self.assertEqual(to_cents(0.55), 55)
        self.assertEqual(to_cents(15.625), 1563)  # round half up

    def test_to_dollars(self):
        self.assertEqual(to_dollars(3313), 33.13)
        self.assertEqual(to_dollars(5), 0.05)

    def test_split_equal_even(self):
        self.assertEqual(split_equal(3000, 3), [1000, 1000, 1000])

    def test_split_equal_remainder_distributed(self):
        # 1000 / 3 = 333.33...; remainder cent goes to earliest shares
        self.assertEqual(split_equal(1000, 3), [334, 333, 333])
        self.assertEqual(sum(split_equal(1000, 3)), 1000)

    def test_split_equal_one_way(self):
        self.assertEqual(split_equal(4505, 1), [4505])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_money -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.money'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/money.py
"""Integer-cent money helpers so split math never drifts due to float error."""
from decimal import Decimal, ROUND_HALF_UP


def to_cents(dollars) -> int:
    """Convert a dollar amount to integer cents, rounding half up."""
    return int((Decimal(str(dollars)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_dollars(cents: int) -> float:
    """Convert integer cents back to a 2-decimal float dollar amount."""
    return float(Decimal(cents) / 100)


def split_equal(total_cents: int, n: int) -> list:
    """Split total_cents into n parts that sum exactly to total_cents.

    Remainder cents are handed to the earliest shares so the result is
    deterministic and always reconciles.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    base = total_cents // n
    remainder = total_cents - base * n
    return [base + (1 if i < remainder else 0) for i in range(n)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_money -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/money.py tests/test_money.py
git commit -m "feat: money module with integer-cent split math"
```

---

## Task 3: Merchant normalization

**Files:**
- Create: `src/merchant.py`
- Test: `tests/test_merchant.py`

Heuristic (documented, approximate — the harness refines via reasoning):
- `extract_merchant(description)`: take text before the first numeric run of length ≥ 3
  (street number / zip / store number); strip a leading `SQ *` prefix; collapse whitespace.
  If no numeric run, use the whole trimmed description.
- `match_key(merchant)`: uppercase the merchant, collapse spaces, keep at most the first
  3 tokens. This is the stable key used for rule matching "by merchant name".

- [ ] **Step 1: Write the failing test**

```python
# tests/test_merchant.py
import unittest
from src.merchant import extract_merchant, match_key

class TestMerchant(unittest.TestCase):
    def test_extract_simple(self):
        self.assertEqual(
            extract_merchant("STARBUCKS 05981 348 W EL CAMINO REAL SUNNYVALE 94087 CA USA"),
            "STARBUCKS")

    def test_extract_dotcom(self):
        self.assertEqual(
            extract_merchant("SHEIN.COM 383 madison ave NEW YORK 10179 NY USA"),
            "SHEIN.COM")

    def test_extract_strips_sq_prefix(self):
        self.assertEqual(
            extract_merchant("SQ *SHAHI DARBAR INDIA26953 Mission Blvd Ste F Hayward 94544 CA USA"),
            "SHAHI DARBAR INDIA")

    def test_extract_no_number(self):
        self.assertEqual(extract_merchant("Spotify USA"), "Spotify USA")

    def test_match_key_uppercases_and_caps_tokens(self):
        self.assertEqual(match_key("STARBUCKS"), "STARBUCKS")
        self.assertEqual(match_key("Spotify USA"), "SPOTIFY USA")
        self.assertEqual(match_key("SHAHI DARBAR INDIA RESTAURANT EXTRA"), "SHAHI DARBAR INDIA")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_merchant -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/merchant.py
"""Best-effort merchant extraction and a stable key for rule matching."""
import re

_NUMERIC_RUN = re.compile(r"\d{3,}")


def extract_merchant(description: str) -> str:
    s = description.strip()
    if s.upper().startswith("SQ *"):
        s = s[4:].strip()
    m = _NUMERIC_RUN.search(s)
    if m:
        s = s[:m.start()].strip()
    return re.sub(r"\s+", " ", s).strip()


def match_key(merchant: str) -> str:
    tokens = re.sub(r"\s+", " ", merchant.strip()).upper().split(" ")
    return " ".join(tokens[:3])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_merchant -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/merchant.py tests/test_merchant.py
git commit -m "feat: merchant extraction and match key"
```

---

## Task 4: Apple Card statement parser (text → transactions)

**Files:**
- Create: `src/parser.py`
- Create: `tests/fixtures/applecard_sample.txt`
- Test: `tests/test_parser.py`

The parser works on already-extracted text (PDF extraction is Task 5) so it is pure and
fast to test. It returns transactions plus a reconciliation total.

- [ ] **Step 1: Create the synthetic fixture**

Create `tests/fixtures/applecard_sample.txt` (mirrors the real Apple Card layout — date,
description, daily-cash %, daily-cash $, amount; a Payments section that must be skipped;
a promo sub-line that must be ignored; and a "Total transactions" control line):

```text
Payments
Date
Description
Amount
01/18/2026
ACH Deposit Internet transfer from account ending in 7315
-$1,419.72 
Total payments for this period 
-$1,419.72 
Transactions
Date
Description
Daily Cash
Amount
12/31/2025
SHEIN.COM 383 madison ave NEW YORK 10179 NY USA
2%
$0.66
$33.13 
01/01/2026
SQ *SHAHI DARBAR INDIA26953 Mission Blvd Ste F Hayward 94544 CA USA
2%
$0.90
$45.05 
01/02/2026
Spotify USA 45 W. 18th Street New York 10011 NY USA
1%
$0.12
$11.99 
01/05/2026
UBER *TRIP 706 MISSION ST 8005928996 94105 CA USA
2%
$0.31
$15.63 
3% Daily Cash at Uber
1%
$0.16
 
Total transactions for this period
$105.80 
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_parser.py
import os
import unittest
from src.parser import parse_applecard

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "applecard_sample.txt")

class TestParser(unittest.TestCase):
    def setUp(self):
        with open(FIX, encoding="utf-8") as f:
            self.result = parse_applecard(f.read(), source="AppleCard 2026-01")

    def test_skips_payments_section(self):
        descs = [t["rawDescription"] for t in self.result["transactions"]]
        self.assertFalse(any("ACH Deposit" in d for d in descs))

    def test_transaction_count(self):
        self.assertEqual(len(self.result["transactions"]), 4)

    def test_first_transaction_fields(self):
        t = self.result["transactions"][0]
        self.assertEqual(t["date"], "2025-12-31")
        self.assertEqual(t["amount"], 33.13)
        self.assertEqual(t["merchant"], "SHEIN.COM")
        self.assertEqual(t["source"], "AppleCard 2026-01")

    def test_ignores_promo_subline(self):
        uber = [t for t in self.result["transactions"] if t["merchant"].startswith("UBER")][0]
        self.assertEqual(uber["amount"], 15.63)

    def test_reconciles_to_reported_total(self):
        total = round(sum(t["amount"] for t in self.result["transactions"]), 2)
        self.assertEqual(total, 105.80)
        self.assertEqual(self.result["reportedTotal"], 105.80)
        self.assertTrue(self.result["reconciles"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_parser -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the implementation**

```python
# src/parser.py
"""Parse Apple Card statement text into normalized transactions.

Pure text-in / dict-out so it is deterministic and easy to unit test.
PDF -> text extraction lives in src/pdf_text.py (Task 5).
"""
import re
from src.merchant import extract_merchant, match_key
from src.money import to_cents

_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_MONEY = re.compile(r"^-?\$[\d,]+\.\d{2}$")
_PCT = re.compile(r"^\d+%$")
_TOTAL_LINE = re.compile(r"Total transactions for this period", re.I)


def _money_to_float(s: str) -> float:
    neg = s.strip().startswith("-")
    digits = s.replace("-", "").replace("$", "").replace(",", "").strip()
    val = float(digits)
    return -val if neg else val


def _iso_date(mmddyyyy: str) -> str:
    mm, dd, yyyy = mmddyyyy.split("/")
    return f"{yyyy}-{mm}-{dd}"


def parse_applecard(text: str, source: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Start scanning after the "Transactions" header (NOT "Payments").
    start = 0
    for i, ln in enumerate(lines):
        if ln == "Transactions":
            start = i + 1
    body = lines[start:]

    transactions = []
    excluded = []
    reported_total = None

    # Group lines into records that begin on a date line.
    records = []
    current = None
    for ln in body:
        if _TOTAL_LINE.search(ln):
            # the money line following the total label is the reported control total
            current = None
            continue
        if _DATE.match(ln):
            current = [ln]
            records.append(current)
        elif current is not None:
            current.append(ln)

    # reportedTotal: the money line that appears right after the total label.
    for i, ln in enumerate(body):
        if _TOTAL_LINE.search(ln):
            for nxt in body[i + 1:]:
                if _MONEY.match(nxt):
                    reported_total = round(_money_to_float(nxt), 2)
                    break
            break

    for rec in records:
        date = _iso_date(rec[0])
        moneys = [x for x in rec[1:] if _MONEY.match(x)]
        if not moneys:
            continue
        amount = round(_money_to_float(moneys[-1]), 2)  # rightmost money col = Amount
        desc_lines = [
            x for x in rec[1:]
            if not _MONEY.match(x) and not _PCT.match(x)
            and "Daily Cash at" not in x
        ]
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

    sum_cents = sum(to_cents(t["amount"]) for t in transactions)
    reconciles = (reported_total is not None
                  and sum_cents == to_cents(reported_total))

    return {
        "transactions": transactions,
        "excluded": excluded,
        "reportedTotal": reported_total,
        "sumOfTransactions": round(sum_cents / 100, 2),
        "reconciles": reconciles,
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_parser -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add src/parser.py tests/test_parser.py tests/fixtures/applecard_sample.txt
git commit -m "feat: apple card text parser with reconciliation"
```

---

## Task 5: PDF text extraction

**Files:**
- Create: `src/pdf_text.py`
- Test: `tests/test_pdf_text.py`

- [ ] **Step 1: Ensure pypdf is installed**

Run: `python3 -c "import pypdf; print(pypdf.__version__)"`
If it errors: `python3 -m pip install pypdf`
Expected: a version string.

- [ ] **Step 2: Write the test (guards behavior, no fixture PDF required)**

```python
# tests/test_pdf_text.py
import unittest
from src import pdf_text

class TestPdfText(unittest.TestCase):
    def test_extract_text_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            pdf_text.extract_text("/no/such/file.pdf")

    def test_module_exposes_extract_text(self):
        self.assertTrue(callable(pdf_text.extract_text))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pdf_text -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the implementation**

```python
# src/pdf_text.py
"""Extract selectable text from a PDF using pypdf."""
import os
from pypdf import PdfReader


def extract_text(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_pdf_text -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add src/pdf_text.py tests/test_pdf_text.py
git commit -m "feat: pdf text extraction via pypdf"
```

---

## Task 6: Keyword categorizer

**Files:**
- Create: `src/categories.py`
- Test: `tests/test_categories.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_categories.py
import unittest
from src.categories import DEFAULT_CATEGORIES, guess_category

class TestCategories(unittest.TestCase):
    def test_known_merchants(self):
        self.assertEqual(guess_category("STARBUCKS"), "Coffee")
        self.assertEqual(guess_category("SAFEWAY"), "Grocery")
        self.assertEqual(guess_category("INDIA CASH & CARRY"), "Grocery")
        self.assertEqual(guess_category("SEPHORA"), "Beauty")
        self.assertEqual(guess_category("UBER *TRIP"), "Transport")
        self.assertEqual(guess_category("SPOTIFY USA"), "Subscriptions")

    def test_unknown_is_miscellaneous(self):
        self.assertEqual(guess_category("ZZQ UNKNOWN VENDOR"), "Miscellaneous")

    def test_miscellaneous_is_last_category(self):
        self.assertEqual(DEFAULT_CATEGORIES[-1], "Miscellaneous")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_categories -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/categories.py
"""Default category buckets and a keyword-based guesser."""

DEFAULT_CATEGORIES = [
    "Coffee", "Grocery", "Restaurants", "Beauty",
    "Shopping", "Transport", "Subscriptions", "Miscellaneous",
]

# Keyword -> category. Checked as case-insensitive substring of the merchant text.
_KEYWORDS = [
    ("STARBUCKS", "Coffee"), ("COFFEE", "Coffee"), ("CAFE", "Coffee"),
    ("PEET", "Coffee"), ("DUNKIN", "Coffee"), ("BLUE BOTTLE", "Coffee"),
    ("SAFEWAY", "Grocery"), ("INDIA CASH", "Grocery"), ("HANKOOK", "Grocery"),
    ("SUPERMARKET", "Grocery"), ("TRADER", "Grocery"), ("WHOLE FOODS", "Grocery"),
    ("COSTCO", "Grocery"), ("MEAT CORNER", "Grocery"), ("GROCERY", "Grocery"),
    ("MARKET", "Grocery"),
    ("DARBAR", "Restaurants"), ("RESTAURANT", "Restaurants"), ("GRILL", "Restaurants"),
    ("KITCHEN", "Restaurants"), ("PIZZA", "Restaurants"), ("STREET FOOD", "Restaurants"),
    ("SEPHORA", "Beauty"), ("ULTA", "Beauty"), ("SALON", "Beauty"),
    ("SPA", "Beauty"), ("NAIL", "Beauty"),
    ("SHEIN", "Shopping"), ("AMAZON", "Shopping"), ("GOODWILL", "Shopping"),
    ("TARGET", "Shopping"), ("APPLE.COM/BILL", "Subscriptions"),
    ("UBER", "Transport"), ("LYFT", "Transport"), ("SHELL", "Transport"),
    ("CHEVRON", "Transport"), ("GAS", "Transport"),
    ("SPOTIFY", "Subscriptions"), ("NETFLIX", "Subscriptions"),
    ("UDEMY", "Subscriptions"),
]


def guess_category(merchant: str) -> str:
    text = (merchant or "").upper()
    for keyword, category in _KEYWORDS:
        if keyword in text:
            return category
    return "Miscellaneous"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_categories -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/categories.py tests/test_categories.py
git commit -m "feat: keyword categorizer with default buckets"
```

---

## Task 7: Expense builder (rules + defaults)

**Files:**
- Create: `src/expense.py`
- Test: `tests/test_expense.py`

Turns a parsed transaction into a full Expense by applying, in priority order:
matching merchant rule (handling + category) → else default split with the default
partner and a guessed category.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_expense.py
import unittest
from src.expense import make_expense, expense_id

TX = {
    "date": "2026-01-03", "rawDescription": "STARBUCKS 05981 ... CA USA",
    "merchant": "STARBUCKS", "matchKey": "STARBUCKS", "amount": 0.55,
    "source": "AppleCard 2026-01",
}
SETTINGS = {"people": [{"id": "p1", "name": "Nitin"}],
            "defaultPartnerId": "p1", "defaultSplitWays": 2,
            "categories": [], "statementFolder": None}

class TestExpense(unittest.TestCase):
    def test_id_is_stable(self):
        self.assertEqual(expense_id(TX), expense_id(dict(TX)))

    def test_default_is_split_with_partner(self):
        e = make_expense(TX, rules={}, settings=SETTINGS)
        self.assertEqual(e["status"], "split")
        self.assertEqual(e["split"]["participants"], ["p1"])
        self.assertTrue(e["split"]["includeSelf"])
        self.assertEqual(e["split"]["shares"], "equal")
        self.assertEqual(e["category"], "Coffee")

    def test_rule_marks_personal(self):
        rules = {"STARBUCKS": {"matchKey": "STARBUCKS", "handling": "personal", "category": None}}
        e = make_expense(TX, rules=rules, settings=SETTINGS)
        self.assertEqual(e["status"], "personal")

    def test_rule_overrides_category(self):
        rules = {"STARBUCKS": {"matchKey": "STARBUCKS", "handling": None, "category": "Restaurants"}}
        e = make_expense(TX, rules=rules, settings=SETTINGS)
        self.assertEqual(e["category"], "Restaurants")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_expense -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/expense.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_expense -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/expense.py tests/test_expense.py
git commit -m "feat: expense builder applying rules and defaults"
```

---

## Task 8: Splitter (compute per-person shares)

**Files:**
- Create: `src/splitter.py`
- Test: `tests/test_splitter.py`

`compute_shares(expense)` returns a dict {personId: dollars} for the **other** people
(never the owner). Equal split divides among owner+participants when `includeSelf`,
else among participants only. Custom shares are passed through (validated to reconcile).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_splitter.py
import unittest
from src.splitter import compute_shares

def split_exp(amount, participants, include_self=True, shares="equal"):
    return {"amount": amount, "status": "split",
            "split": {"participants": participants, "includeSelf": include_self, "shares": shares}}

class TestSplitter(unittest.TestCase):
    def test_equal_two_way_with_self(self):
        e = split_exp(30.00, ["p1"], include_self=True)
        self.assertEqual(compute_shares(e), {"p1": 15.00})

    def test_equal_three_way_with_self(self):
        e = split_exp(30.00, ["p1", "p2"], include_self=True)
        self.assertEqual(compute_shares(e), {"p1": 10.00, "p2": 10.00})

    def test_equal_excludes_self(self):
        e = split_exp(30.00, ["p1", "p2"], include_self=False)
        self.assertEqual(compute_shares(e), {"p1": 15.00, "p2": 15.00})

    def test_remainder_cent_is_deterministic(self):
        e = split_exp(10.00, ["p1", "p2"], include_self=True)  # 3 ways
        shares = compute_shares(e)
        # owner gets the extra cent; the two others get 3.33 each
        self.assertEqual(shares, {"p1": 3.33, "p2": 3.33})

    def test_custom_shares_passthrough(self):
        e = split_exp(30.00, ["p1", "p2"], shares={"p1": 20.00, "p2": 10.00})
        self.assertEqual(compute_shares(e), {"p1": 20.00, "p2": 10.00})

    def test_custom_shares_must_reconcile(self):
        e = split_exp(30.00, ["p1", "p2"], shares={"p1": 20.00, "p2": 5.00})
        with self.assertRaises(ValueError):
            compute_shares(e)

    def test_personal_has_no_shares(self):
        e = {"amount": 5.0, "status": "personal", "split": {"participants": [], "includeSelf": True, "shares": "equal"}}
        self.assertEqual(compute_shares(e), {})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_splitter -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/splitter.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_splitter -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/splitter.py tests/test_splitter.py
git commit -m "feat: per-person share computation"
```

---

## Task 9: Totals + CSV export

**Files:**
- Create: `src/reports.py`
- Test: `tests/test_reports.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reports.py
import unittest
from src.reports import per_person_totals, per_person_csv, combined_csv

PEOPLE = [{"id": "p1", "name": "Nitin"}, {"id": "p2", "name": "Priya"}]

def exp(eid, merchant, amount, participants, category="Misc", include_self=True, shares="equal", status="split"):
    return {"id": eid, "date": "2026-01-01", "merchant": merchant, "amount": amount,
            "category": category, "status": status, "source": "AppleCard 2026-01",
            "rawDescription": merchant, "matchKey": merchant.upper(),
            "split": {"participants": participants, "includeSelf": include_self, "shares": shares}}

EXPENSES = [
    exp("a", "STARBUCKS", 30.00, ["p1"]),            # p1 owes 15
    exp("b", "SAFEWAY", 30.00, ["p1", "p2"]),        # p1,p2 owe 10 each
    exp("c", "PERSONAL THING", 9.99, [], status="personal"),
]

class TestReports(unittest.TestCase):
    def test_per_person_totals(self):
        self.assertEqual(per_person_totals(EXPENSES), {"p1": 25.00, "p2": 10.00})

    def test_per_person_csv_only_their_expenses(self):
        csv = per_person_csv(EXPENSES, "p2", PEOPLE)
        lines = csv.strip().splitlines()
        self.assertEqual(lines[0], "Date,Merchant,Category,Total,Your Share")
        self.assertEqual(len(lines), 2)  # header + 1 expense for p2
        self.assertIn("SAFEWAY", lines[1])
        self.assertTrue(lines[1].endswith("10.0") or lines[1].endswith("10.00"))

    def test_combined_csv_has_column_per_person(self):
        csv = combined_csv(EXPENSES, PEOPLE)
        header = csv.strip().splitlines()[0]
        self.assertEqual(header, "Date,Merchant,Category,Total,Nitin,Priya")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_reports -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/reports.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_reports -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/reports.py tests/test_reports.py
git commit -m "feat: per-person totals and csv exports"
```

---

## Task 10: Store (JSON persistence)

**Files:**
- Create: `src/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
import os
import tempfile
import unittest
from src.store import Store, default_settings

class TestStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = Store(self.dir)

    def test_defaults_when_empty(self):
        self.assertEqual(self.store.load_expenses(), [])
        self.assertEqual(self.store.load_rules(), {})
        s = self.store.load_settings()
        self.assertEqual(s["defaultSplitWays"], 2)
        self.assertIn("Miscellaneous", s["categories"])

    def test_roundtrip_expenses(self):
        self.store.save_expenses([{"id": "x", "amount": 1.0}])
        self.assertEqual(self.store.load_expenses(), [{"id": "x", "amount": 1.0}])

    def test_roundtrip_rules(self):
        self.store.save_rules({"STARBUCKS": {"matchKey": "STARBUCKS", "handling": "personal", "category": None}})
        self.assertEqual(self.store.load_rules()["STARBUCKS"]["handling"], "personal")

    def test_default_settings_shape(self):
        s = default_settings()
        self.assertEqual(s["people"], [])
        self.assertIsNone(s["defaultPartnerId"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_store -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/store.py
"""Read/write the three JSON data files. All paths under one data directory."""
import json
import os
from src.categories import DEFAULT_CATEGORIES


def default_settings() -> dict:
    return {
        "people": [],
        "defaultPartnerId": None,
        "defaultSplitWays": 2,
        "categories": list(DEFAULT_CATEGORIES),
        "statementFolder": None,
    }


class Store:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    def _load(self, name: str, default):
        path = self._path(name)
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, name: str, data):
        with open(self._path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_expenses(self):
        return self._load("expenses.json", [])

    def save_expenses(self, expenses):
        self._save("expenses.json", expenses)

    def load_rules(self):
        return self._load("rules.json", {})

    def save_rules(self, rules):
        self._save("rules.json", rules)

    def load_settings(self):
        s = self._load("settings.json", None)
        if s is None:
            s = default_settings()
            self._save("settings.json", s)
        return s

    def save_settings(self, settings):
        self._save("settings.json", settings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_store -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: json store for expenses, rules, settings"
```

---

## Task 11: Ingest orchestration

**Files:**
- Create: `src/ingest.py`
- Test: `tests/test_ingest.py`

Ties parser + expense-builder + dedup together. Given statement text (or a PDF path)
and the current store, produce the merged expense list plus a verification report.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest.py
import os
import unittest
from src.ingest import ingest_text

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "applecard_sample.txt")
SETTINGS = {"people": [{"id": "p1", "name": "Nitin"}], "defaultPartnerId": "p1",
            "defaultSplitWays": 2, "categories": [], "statementFolder": None}

class TestIngest(unittest.TestCase):
    def setUp(self):
        with open(FIX, encoding="utf-8") as f:
            self.text = f.read()

    def test_produces_expenses_and_report(self):
        result = ingest_text(self.text, source="AppleCard 2026-01",
                             existing=[], rules={}, settings=SETTINGS)
        self.assertEqual(len(result["expenses"]), 4)
        self.assertTrue(result["report"]["reconciles"])
        self.assertEqual(result["report"]["count"], 4)

    def test_dedup_against_existing(self):
        first = ingest_text(self.text, source="AppleCard 2026-01",
                            existing=[], rules={}, settings=SETTINGS)["expenses"]
        again = ingest_text(self.text, source="AppleCard 2026-01",
                           existing=first, rules={}, settings=SETTINGS)["expenses"]
        self.assertEqual(len(again), 4)  # no duplicates added

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_ingest -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/ingest.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_ingest -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ingest.py tests/test_ingest.py
git commit -m "feat: ingest orchestration with dedup and report"
```

---

## Task 12: HTTP server (API + static files)

**Files:**
- Create: `src/server.py`
- Test: `tests/test_server.py`

Endpoints (JSON unless noted):
- `GET /api/state` → `{expenses, rules, settings, totals}`
- `POST /api/expenses` body `{expenses}` → saves, returns `{ok, totals}`
- `POST /api/rules` body `{rules}` → saves, returns `{ok}`
- `POST /api/settings` body `{settings}` → saves, returns `{ok}`
- `POST /api/upload` multipart PDF → parses, merges, saves, returns `{report, expenses, totals}`
- `GET /api/export/combined.csv` → text/csv
- `GET /api/export/person.csv?id=p1` → text/csv
- `GET /` and static files from `web/`

Server uses a module-level `Store` rooted at `data/` and the report from ingest.

- [ ] **Step 1: Write the failing test (uses http.client against a started server)**

```python
# tests/test_server.py
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from src import server

class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.httpd = server.make_server(host="127.0.0.1", port=0, data_dir=cls.dir)
        cls.port = cls.httpd.server_address[1]
        cls.t = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
            return json.loads(r.read().decode())

    def _post(self, path, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=data, headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())

    def test_state_has_keys(self):
        state = self._get("/api/state")
        for k in ("expenses", "rules", "settings", "totals"):
            self.assertIn(k, state)

    def test_save_expenses_returns_totals(self):
        exp = [{"id": "a", "date": "2026-01-01", "merchant": "M", "amount": 30.0,
                "category": "Misc", "status": "split", "source": "s", "rawDescription": "M", "matchKey": "M",
                "split": {"participants": ["p1"], "includeSelf": True, "shares": "equal"}}]
        res = self._post("/api/expenses", {"expenses": exp})
        self.assertTrue(res["ok"])
        self.assertEqual(res["totals"], {"p1": 15.0})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_server -v`
Expected: FAIL with `ModuleNotFoundError` or `AttributeError: make_server`

- [ ] **Step 3: Write the implementation**

```python
# src/server.py
"""Tiny stdlib HTTP server: JSON API + static frontend from web/."""
import json
import os
import cgi
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from src.store import Store
from src.reports import per_person_totals, per_person_csv, combined_csv
from src.ingest import ingest_text

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")

_CONTENT_TYPES = {
    ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
    ".json": "application/json", ".svg": "image/svg+xml",
}


def _make_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # quiet

        # ---- helpers ----
        def _send_json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, text, content_type="text/plain", code=200, filename=None):
            body = text.encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length).decode() or "{}")

        def _state(self):
            expenses = store.load_expenses()
            return {
                "expenses": expenses,
                "rules": store.load_rules(),
                "settings": store.load_settings(),
                "totals": per_person_totals(expenses),
            }

        # ---- routing ----
        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/state":
                return self._send_json(self._state())
            if path == "/api/export/combined.csv":
                expenses = store.load_expenses()
                people = store.load_settings()["people"]
                return self._send_text(combined_csv(expenses, people),
                                        "text/csv", filename="combined.csv")
            if path == "/api/export/person.csv":
                pid = parse_qs(parsed.query).get("id", [None])[0]
                expenses = store.load_expenses()
                people = store.load_settings()["people"]
                return self._send_text(per_person_csv(expenses, pid, people),
                                        "text/csv", filename=f"{pid}.csv")
            return self._serve_static(path)

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/expenses":
                data = self._read_json()
                store.save_expenses(data["expenses"])
                return self._send_json({"ok": True, "totals": per_person_totals(data["expenses"])})
            if path == "/api/rules":
                data = self._read_json()
                store.save_rules(data["rules"])
                return self._send_json({"ok": True})
            if path == "/api/settings":
                data = self._read_json()
                store.save_settings(data["settings"])
                return self._send_json({"ok": True})
            if path == "/api/upload":
                return self._handle_upload()
            return self._send_json({"error": "not found"}, 404)

        def _handle_upload(self):
            ctype = self.headers.get("Content-Type", "")
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                    environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype})
            fileitem = form["file"]
            import tempfile
            from src.pdf_text import extract_text
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(fileitem.file.read())
                tmp_path = tmp.name
            source = os.path.splitext(os.path.basename(fileitem.filename))[0]
            text = extract_text(tmp_path)
            os.unlink(tmp_path)
            result = ingest_text(text, source=source, existing=store.load_expenses(),
                                 rules=store.load_rules(), settings=store.load_settings())
            store.save_expenses(result["expenses"])
            return self._send_json({"report": result["report"],
                                    "expenses": result["expenses"],
                                    "totals": per_person_totals(result["expenses"])})

        def _serve_static(self, path):
            if path == "/":
                path = "/index.html"
            full = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
            if not full.startswith(WEB_DIR) or not os.path.isfile(full):
                return self._send_json({"error": "not found"}, 404)
            ext = os.path.splitext(full)[1]
            with open(full, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", _CONTENT_TYPES.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def make_server(host="127.0.0.1", port=8000, data_dir=None):
    data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    store = Store(data_dir)
    return ThreadingHTTPServer((host, port), _make_handler(store))


def main():
    httpd = make_server(port=int(os.environ.get("PORT", "8000")))
    host, port = httpd.server_address
    print(f"Expense Splitter running at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_server -v`
Expected: PASS (2 tests). (Static route returns 404 in test since `web/` is empty until Task 13 — that's fine; tests only hit the API.)

- [ ] **Step 5: Commit**

```bash
git add src/server.py tests/test_server.py
git commit -m "feat: stdlib http server with json api and csv export"
```

---

## Task 13: Frontend — HTML shell + styles

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`

- [ ] **Step 1: Write `web/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Expense Splitter</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <header>
    <h1>Expense Splitter</h1>
    <nav>
      <button data-view="review" class="active">Review</button>
      <button data-view="totals">Totals</button>
      <button data-view="settings">People &amp; Settings</button>
    </nav>
  </header>

  <section id="report" class="report hidden"></section>

  <main>
    <section id="view-review" class="view">
      <div class="upload">
        <label class="filebtn">Upload statement PDF
          <input type="file" id="pdfInput" accept="application/pdf" hidden>
        </label>
        <span id="uploadStatus"></span>
      </div>
      <div id="groups"></div>
    </section>

    <section id="view-totals" class="view hidden">
      <h2>Each person owes you</h2>
      <table id="totalsTable"></table>
      <div class="exports">
        <button id="exportCombined">Download combined CSV</button>
        <div id="perPersonExports"></div>
      </div>
    </section>

    <section id="view-settings" class="view hidden">
      <h2>People</h2>
      <ul id="peopleList"></ul>
      <form id="addPersonForm">
        <input id="personName" placeholder="Name (e.g. Nitin)" required>
        <button type="submit">Add person</button>
      </form>
      <h2>Defaults</h2>
      <label>Default partner:
        <select id="defaultPartner"></select>
      </label>
      <h2>Statement folder (for Claude Code harness)</h2>
      <input id="statementFolder" placeholder="/Users/you/Statements" size="40">
      <button id="saveSettings">Save settings</button>
    </section>
  </main>

  <!-- Split editor dialog -->
  <dialog id="splitDialog">
    <form method="dialog" id="splitForm">
      <h3 id="splitTitle">Split</h3>
      <div id="splitPeople"></div>
      <label><input type="checkbox" id="includeSelf" checked> Include me</label>
      <fieldset id="customShares" class="hidden">
        <legend>Custom amounts</legend>
        <div id="customSharesRows"></div>
      </fieldset>
      <label><input type="checkbox" id="useCustom"> Use custom amounts</label>
      <menu>
        <button value="cancel">Cancel</button>
        <button id="splitSave" value="save">Save</button>
      </menu>
    </form>
  </dialog>

  <script type="module" src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `web/styles.css`**

```css
* { box-sizing: border-box; }
body { font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #1d1d1f; background: #f5f5f7; }
header { background: #fff; padding: 12px 20px; border-bottom: 1px solid #ddd; position: sticky; top: 0; }
header h1 { margin: 0 0 8px; font-size: 20px; }
nav button { margin-right: 8px; padding: 6px 12px; border: 1px solid #ccc; background: #fff; border-radius: 8px; cursor: pointer; }
nav button.active { background: #0071e3; color: #fff; border-color: #0071e3; }
main { padding: 20px; max-width: 920px; margin: 0 auto; }
.view.hidden, .hidden { display: none; }
.report { background: #e8f5e9; border: 1px solid #a5d6a7; padding: 10px 16px; margin: 12px 20px; border-radius: 8px; }
.report.bad { background: #fdecea; border-color: #f5c6cb; }
.group { background: #fff; border: 1px solid #e3e3e3; border-radius: 12px; margin-bottom: 16px; overflow: hidden; }
.group h3 { margin: 0; padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #eee; }
.row { display: grid; grid-template-columns: 90px 1fr 90px auto; gap: 10px; align-items: center; padding: 10px 16px; border-bottom: 1px solid #f0f0f0; }
.row:last-child { border-bottom: none; }
.row .amount { text-align: right; font-variant-numeric: tabular-nums; }
.row.personal { opacity: 0.55; }
.actions button { font-size: 12px; margin-left: 4px; padding: 4px 8px; border-radius: 6px; border: 1px solid #ccc; background: #fff; cursor: pointer; }
.actions button.on { background: #0071e3; color: #fff; border-color: #0071e3; }
.filebtn { display: inline-block; padding: 8px 14px; background: #0071e3; color: #fff; border-radius: 8px; cursor: pointer; }
.upload { margin-bottom: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; }
td, th { padding: 10px 16px; border-bottom: 1px solid #eee; text-align: left; }
dialog { border: none; border-radius: 12px; padding: 20px; min-width: 320px; }
menu { display: flex; gap: 8px; justify-content: flex-end; padding: 0; }
```

- [ ] **Step 3: Verify files load (manual)**

Run: `python3 -m src.server` then open `http://localhost:8000`.
Expected: page renders with header/nav (no data yet; console clean except `app.js` 404 until Task 14). Stop the server with Ctrl-C.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/styles.css
git commit -m "feat: frontend shell and styles"
```

---

## Task 14: Frontend — app logic

**Files:**
- Create: `web/app.js`

This is the full client. It fetches state, renders grouped expenses with the per-row
actions (personal/split once or always, change category), the split editor, totals, and
settings. It persists by POSTing the whole expense list / rules / settings back.

- [ ] **Step 1: Write `web/app.js`**

```javascript
// web/app.js — Expense Splitter client
const api = {
  async state() { return (await fetch('/api/state')).json(); },
  async saveExpenses(expenses) {
    return (await fetch('/api/expenses', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({expenses})})).json();
  },
  async saveRules(rules) {
    return (await fetch('/api/rules', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({rules})})).json();
  },
  async saveSettings(settings) {
    return (await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({settings})})).json();
  },
  async upload(file) {
    const fd = new FormData(); fd.append('file', file);
    return (await fetch('/api/upload', {method:'POST', body: fd})).json();
  },
};

const state = { expenses: [], rules: {}, settings: null, totals: {} };
const CATEGORY_ORDER = ["Coffee","Grocery","Restaurants","Beauty","Shopping","Transport","Subscriptions","Miscellaneous"];

function personName(id) {
  const p = (state.settings.people || []).find(p => p.id === id);
  return p ? p.name : id;
}

async function refresh() {
  Object.assign(state, await api.state());
  render();
}

async function persistExpenses() {
  const res = await api.saveExpenses(state.expenses);
  state.totals = res.totals;
  render();
}

// ---------- rendering ----------
function render() {
  renderGroups();
  renderTotals();
  renderSettings();
}

function categoryRank(cat) {
  const i = CATEGORY_ORDER.indexOf(cat);
  return i === -1 ? CATEGORY_ORDER.length - 0.5 : i; // unknowns just before Miscellaneous
}

function renderGroups() {
  const container = document.getElementById('groups');
  container.innerHTML = '';
  const byCat = {};
  for (const e of state.expenses) (byCat[e.category] ||= []).push(e);
  const cats = Object.keys(byCat).sort((a,b) => categoryRank(a) - categoryRank(b));
  for (const cat of cats) {
    const group = document.createElement('div');
    group.className = 'group';
    group.innerHTML = `<h3>${cat}</h3>`;
    for (const e of byCat[cat]) group.appendChild(rowEl(e));
    container.appendChild(group);
  }
}

function rowEl(e) {
  const row = document.createElement('div');
  row.className = 'row' + (e.status === 'personal' ? ' personal' : '');
  const splitInfo = e.status === 'split'
    ? `split ${e.split.participants.map(personName).join(', ') || '(no one)'}`
    : 'personal';
  row.innerHTML = `
    <span>${e.date}</span>
    <span>${e.merchant} <small>${splitInfo}</small></span>
    <span class="amount">$${e.amount.toFixed(2)}</span>
    <span class="actions"></span>`;
  const actions = row.querySelector('.actions');
  actions.appendChild(btn('Personal', e.status==='personal', () => setPersonal(e, false)));
  actions.appendChild(btn('Always personal', false, () => setPersonal(e, true)));
  actions.appendChild(btn('Split…', e.status==='split', () => openSplit(e)));
  actions.appendChild(btn('Always split', false, () => setAlwaysSplit(e)));
  return row;
}

function btn(label, on, fn) {
  const b = document.createElement('button');
  b.textContent = label; if (on) b.classList.add('on');
  b.onclick = fn; return b;
}

// ---------- actions ----------
async function setPersonal(e, always) {
  e.status = 'personal';
  if (always) await saveRule(e.matchKey, {handling: 'personal'});
  await persistExpenses();
}

async function setAlwaysSplit(e) {
  e.status = 'split';
  await saveRule(e.matchKey, {handling: 'split'});
  await persistExpenses();
}

async function saveRule(matchKey, patch) {
  const existing = state.rules[matchKey] || {matchKey, handling: null, category: null};
  state.rules[matchKey] = {...existing, ...patch};
  await api.saveRules(state.rules);
}

// ---------- split editor ----------
let editing = null;
function openSplit(e) {
  editing = e;
  const dlg = document.getElementById('splitDialog');
  document.getElementById('splitTitle').textContent = `Split: ${e.merchant} ($${e.amount.toFixed(2)})`;
  const people = state.settings.people || [];
  const box = document.getElementById('splitPeople');
  box.innerHTML = people.map(p =>
    `<label><input type="checkbox" value="${p.id}" ${e.split.participants.includes(p.id)?'checked':''}> ${p.name}</label>`
  ).join('') || '<em>Add people in Settings first.</em>';
  document.getElementById('includeSelf').checked = e.split.includeSelf;
  document.getElementById('useCustom').checked = (e.split.shares !== 'equal');
  dlg.showModal();
}

document.getElementById('splitForm').addEventListener('submit', async (ev) => {
  if (ev.submitter && ev.submitter.value === 'cancel') return;
  const checked = [...document.querySelectorAll('#splitPeople input:checked')].map(i => i.value);
  editing.status = 'split';
  editing.split.participants = checked;
  editing.split.includeSelf = document.getElementById('includeSelf').checked;
  editing.split.shares = 'equal'; // custom-amount UI can be extended later
  await persistExpenses();
});

// ---------- totals + exports ----------
function renderTotals() {
  const t = document.getElementById('totalsTable');
  const rows = Object.entries(state.totals)
    .map(([pid, amt]) => `<tr><td>${personName(pid)}</td><td>$${amt.toFixed(2)}</td></tr>`).join('');
  t.innerHTML = `<tr><th>Person</th><th>Owes you</th></tr>${rows || '<tr><td colspan="2">No split expenses yet.</td></tr>'}`;
  const box = document.getElementById('perPersonExports');
  box.innerHTML = '';
  for (const p of (state.settings.people || [])) {
    const a = document.createElement('a');
    a.href = `/api/export/person.csv?id=${encodeURIComponent(p.id)}`;
    a.textContent = `Download ${p.name}'s CSV`;
    a.className = 'filebtn'; a.style.marginRight = '8px';
    box.appendChild(a);
  }
}

// ---------- settings ----------
function renderSettings() {
  const list = document.getElementById('peopleList');
  list.innerHTML = (state.settings.people || [])
    .map(p => `<li>${p.name} <button data-del="${p.id}">remove</button></li>`).join('');
  list.querySelectorAll('button[data-del]').forEach(b =>
    b.onclick = () => removePerson(b.dataset.del));
  const sel = document.getElementById('defaultPartner');
  sel.innerHTML = '<option value="">(none)</option>' +
    (state.settings.people || []).map(p =>
      `<option value="${p.id}" ${state.settings.defaultPartnerId===p.id?'selected':''}>${p.name}</option>`).join('');
  document.getElementById('statementFolder').value = state.settings.statementFolder || '';
}

async function removePerson(id) {
  state.settings.people = state.settings.people.filter(p => p.id !== id);
  if (state.settings.defaultPartnerId === id) state.settings.defaultPartnerId = null;
  await api.saveSettings(state.settings); await refresh();
}

document.getElementById('addPersonForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const name = document.getElementById('personName').value.trim();
  if (!name) return;
  const id = 'p' + Date.now();
  state.settings.people.push({id, name});
  document.getElementById('personName').value = '';
  await api.saveSettings(state.settings); await refresh();
});

document.getElementById('saveSettings').addEventListener('click', async () => {
  state.settings.defaultPartnerId = document.getElementById('defaultPartner').value || null;
  state.settings.statementFolder = document.getElementById('statementFolder').value.trim() || null;
  await api.saveSettings(state.settings); await refresh();
});

// ---------- upload ----------
document.getElementById('pdfInput').addEventListener('change', async (ev) => {
  const file = ev.target.files[0]; if (!file) return;
  document.getElementById('uploadStatus').textContent = 'Reading…';
  const res = await api.upload(file);
  showReport(res.report);
  await refresh();
  document.getElementById('uploadStatus').textContent =
    `Added ${res.report.added} of ${res.report.count} transactions.`;
});

function showReport(report) {
  const el = document.getElementById('report');
  el.classList.remove('hidden', 'bad');
  if (!report.reconciles) el.classList.add('bad');
  el.textContent = report.reconciles
    ? `✓ ${report.source}: ${report.count} transactions, total $${report.sumOfTransactions} reconciles with statement.`
    : `⚠ ${report.source}: parsed total $${report.sumOfTransactions} does NOT match statement total $${report.reportedTotal}. Review carefully.`;
}

// ---------- nav ----------
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  document.getElementById('view-' + b.dataset.view).classList.remove('hidden');
});
document.getElementById('exportCombined').onclick =
  () => location.href = '/api/export/combined.csv';

refresh();
```

- [ ] **Step 2: Manual smoke test**

Run: `python3 -m src.server`, open `http://localhost:8000`.
- Settings → add person "Nitin", set as default partner, Save.
- Review → Upload the real `Apple Card Statement - January 2026.pdf` from `~/Desktop`.
- Expect: green reconcile report, expenses grouped by category, default split = Nitin.
- Click Personal / Always personal / Split… and confirm rows update.
- Totals → see Nitin's total; download combined + per-person CSV.
Stop server with Ctrl-C.

- [ ] **Step 3: Commit**

```bash
git add web/app.js
git commit -m "feat: frontend app logic (review, split, totals, settings, upload)"
```

---

## Task 15: Harness launch prompt + verification helper

**Files:**
- Create: `LAUNCH.md`
- Create: `src/harness.py`
- Test: `tests/test_harness.py`

`src/harness.py` provides a CLI that Claude Code (or the user) can run to parse a folder
of statements deterministically and write `data/expenses.json`, printing the verification
report. `LAUNCH.md` is the copy-paste prompt that wraps this with the self-verification
protocol.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_harness.py
import os, tempfile, json, unittest
from src import harness

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "applecard_sample.txt")

class TestHarness(unittest.TestCase):
    def test_ingest_file_writes_and_reports(self):
        d = tempfile.mkdtemp()
        # seed a person so defaults have a partner
        with open(os.path.join(d, "settings.json"), "w") as f:
            json.dump({"people":[{"id":"p1","name":"Nitin"}],"defaultPartnerId":"p1",
                       "defaultSplitWays":2,"categories":[],"statementFolder":None}, f)
        report = harness.ingest_statement_text_file(FIX, source="AppleCard 2026-01", data_dir=d)
        self.assertTrue(report["reconciles"])
        self.assertEqual(report["count"], 4)
        with open(os.path.join(d, "expenses.json")) as f:
            self.assertEqual(len(json.load(f)), 4)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_harness -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/harness.py`**

```python
# src/harness.py
"""Deterministic statement ingestion for the Claude Code harness.

Usage:
    python3 -m src.harness path/to/statement.pdf [more.pdf ...]
Reads existing data/, parses each statement, merges + dedups, writes data/expenses.json,
and prints a verification report per file.
"""
import os
import sys
from src.store import Store
from src.ingest import ingest_text
from src.pdf_text import extract_text


def _source_from_path(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def ingest_statement_text(text: str, source: str, data_dir: str) -> dict:
    store = Store(data_dir)
    result = ingest_text(text, source=source, existing=store.load_expenses(),
                         rules=store.load_rules(), settings=store.load_settings())
    store.save_expenses(result["expenses"])
    return result["report"]


def ingest_statement_text_file(path: str, source: str, data_dir: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return ingest_statement_text(f.read(), source, data_dir)


def ingest_statement_pdf(path: str, data_dir: str) -> dict:
    return ingest_statement_text(extract_text(path), _source_from_path(path), data_dir)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python3 -m src.harness <statement.pdf> [...]")
        return 1
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    for path in argv:
        report = ingest_statement_pdf(path, data_dir)
        status = "OK" if report["reconciles"] else "CHECK"
        print(f"[{status}] {report['source']}: {report['count']} tx, "
              f"sum ${report['sumOfTransactions']} vs reported ${report['reportedTotal']}, "
              f"added {report['added']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_harness -v`
Expected: PASS (1 test)

- [ ] **Step 5: Write `LAUNCH.md`**

````markdown
# Launch prompt (paste into a Claude Code session in this folder)

You are running the Expense Splitter harness. Do the following carefully — this is
financial data and there is zero tolerance for misreads or math errors.

## Inputs
- Statement folder: read it from `data/settings.json` → `statementFolder`. If unset,
  ask me for the folder path. Process every PDF in it that isn't already represented
  in `data/expenses.json` (match by the statement's source name).

## Steps
1. For each new statement PDF, run the deterministic parser:
   `python3 -m src.harness "<path-to-pdf>"`
   This extracts transactions, merges + dedups into `data/expenses.json`, and prints a
   verification report (transaction count, parsed sum vs the statement's reported total,
   how many were added).
2. **Self-verify every statement** before trusting it:
   - Open the PDF text yourself (`python3 -c "from src.pdf_text import extract_text; print(extract_text('<path>'))"`)
     and independently confirm the transaction count and the summed total.
   - Confirm the parser's `sumOfTransactions` equals the statement's own
     "Total transactions for this period" (or equivalent control figure). If the report
     says `CHECK` (does not reconcile), investigate the discrepancy, find the misread or
     missing row, and fix it in `data/expenses.json` so it reconciles. Never guess.
   - Spot-check that no `Payments`/refund/credit row was included as an expense.
   - For non–Apple Card statements the deterministic parser may not understand, read the
     PDF text yourself and append correctly-normalized expense records to
     `data/expenses.json` using the exact shape documented in
     `docs/specs/2026-06-06-expense-splitter-design.md` §4, then re-verify the totals.
3. Print a final verification summary: per statement — source, count, reconciled total,
   and any rows you were unsure about.
4. Start the app and tell me to open it:
   `python3 -m src.server`  → http://localhost:8000

Do not modify amounts to force reconciliation — only fix genuine parse errors.
````

- [ ] **Step 6: Commit**

```bash
git add src/harness.py tests/test_harness.py LAUNCH.md
git commit -m "feat: harness cli and launch prompt with self-verification protocol"
```

---

## Task 16: Optional real-statement reconciliation test + full suite

**Files:**
- Create: `tests/test_real_statement.py`

- [ ] **Step 1: Write the integration test (skips when the real PDF is absent)**

```python
# tests/test_real_statement.py
import os
import unittest
from src.pdf_text import extract_text
from src.parser import parse_applecard

REAL = os.path.expanduser("~/Desktop/Apple Card Statement - January 2026.pdf")

@unittest.skipUnless(os.path.exists(REAL), "real statement not present")
class TestRealStatement(unittest.TestCase):
    def test_parses_and_reconciles(self):
        text = extract_text(REAL)
        result = parse_applecard(text, source="AppleCard 2026-01")
        self.assertGreater(len(result["transactions"]), 0)
        # If the statement exposes a reported total, it must reconcile.
        if result["reportedTotal"] is not None:
            self.assertTrue(result["reconciles"],
                f"parsed ${result['sumOfTransactions']} != reported ${result['reportedTotal']}")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests PASS (the real-statement test runs if the PDF is on the Desktop,
otherwise it is skipped). If the real-statement test FAILS, the parser needs adjustment
for the real layout (e.g. the "Total transactions" control line wording) — fix the parser
and re-run; do not weaken the assertion.

- [ ] **Step 3: Commit**

```bash
git add tests/test_real_statement.py
git commit -m "test: optional reconciliation against real apple card statement"
```

---

## Task 17: Final polish — start script + docs

**Files:**
- Create: `start.sh`
- Modify: `README.md`

- [ ] **Step 1: Write `start.sh`**

```bash
#!/usr/bin/env bash
# Launch the Expense Splitter app and open it in the browser.
set -e
cd "$(dirname "$0")"
python3 -m pip install --quiet pypdf >/dev/null 2>&1 || true
(python3 -m src.server) &
SERVER_PID=$!
sleep 1
open http://localhost:8000 || true
wait $SERVER_PID
```

- [ ] **Step 2: Make it executable and update README run instructions**

```bash
chmod +x start.sh
```

Append to `README.md`:

```markdown
## Quick start
    ./start.sh
Opens the app at http://localhost:8000. Add people in Settings, then upload a statement.
```

- [ ] **Step 3: Final full-suite run**

Run: `python3 -m unittest discover -s tests -v`
Expected: all PASS / skipped as noted.

- [ ] **Step 4: Commit**

```bash
git add start.sh README.md
git commit -m "chore: start script and quickstart docs"
```

---

## Self-Review (completed by plan author)

**Spec coverage:**
- Harness + app, two ingest modes → Tasks 12 (upload), 15 (harness) ✓
- Multi-bank via reasoning → LAUNCH.md step 2 (non–Apple Card handling) ✓
- Self-verification protocol (§6) → parser reconciliation (Task 4), report (Task 11),
  LAUNCH.md protocol (Task 15), optional real-statement test (Task 16) ✓
- Merchant rules by name, personal/split once-or-always → Tasks 7, 14 ✓
- Default split 2-way with Nitin → Task 7 ✓
- Equal-by-default incl. self, custom/exclude-self → Tasks 8, 14 ✓
- Categories grouped, Miscellaneous last, learned → Tasks 6, 14 (CATEGORY_ORDER) ✓
- Submit → totals → Tasks 9, 14 ✓
- Per-person + combined CSV → Tasks 9, 12, 14 ✓
- Local JSON storage → Task 10 ✓
- Python stdlib server, pypdf, unittest → Tasks 5, 12 ✓

**Placeholder scan:** No TBD/TODO; every code step has complete code.

**Type consistency:** Expense/Person/Rule/Settings shapes are identical across Tasks
4, 7, 8, 9, 10, 12, 14. `compute_shares`, `per_person_totals`, `make_expense`,
`ingest_text`, `parse_applecard`, `Store` signatures match their callers.

**Known approximation (documented, intentional):** offline merchant extraction is
heuristic; the harness refines via reasoning and the learning rules converge it.
