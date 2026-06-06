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
   - Open the PDF text yourself
     (`python3 -c "from src.pdf_text import extract_text; print(extract_text('<path>'))"`)
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
