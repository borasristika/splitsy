# Splitsy — local statement expense splitter

Splitsy turns your credit-card / bank statements into a reviewed list of expenses,
lets you mark each one as **personal** or **split with other people**, and produces a
clear, shareable breakdown of **who owes you what** — as CSV, as a PDF, or pushed
straight into [Splitwise](https://splitwise.com).

It's **local-first and private**: it runs entirely on your own machine, stores
everything in plain JSON files on disk, and never uploads your financial data
anywhere (the only network calls are the optional Splitwise push, which you trigger).

> Built for one user (you). No accounts, no cloud database, no tracking.

## What it does

- **Reads statements.** Drop in a PDF (Apple Card is supported out of the box) and it
  extracts every transaction — date, merchant, amount — and **reconciles the total
  against the statement's own control figure** so nothing is misread or missed.
- **Groups by category.** Coffee, Grocery, Restaurants, Beauty, Shopping, Transport,
  Subscriptions, … (anything unknown lands in Miscellaneous). It learns: re-categorize
  a merchant once and it remembers.
- **Personal vs. split, with memory.** Tag each expense as just yours or split with
  one or more people. "Always personal / Always split" creates a per-merchant rule that
  applies to every matching expense, now and on future uploads.
- **Accurate splitting.** Equal by default (you included), or custom shares / exclude
  yourself. All money math is done in **integer cents**, so every split reconciles to
  the penny.
- **Running totals.** A live bar shows your **total spent across all statements** and
  **how much each person owes you**, updating as you tag.
- **Provenance-stamped exports.** Per-person and combined **CSV** and **PDF** summaries,
  each stamped with which statements (and bank) are included, the generated date, and a
  TOTAL — so an "Apple Card Jan–Apr" export is never confused with a future "Chase" one.
- **Statement history.** Upload many statements over time and filter the view to any one
  of them; tagging persists on disk across reloads and restarts.
- **Optional Splitwise integration.** Connect with your Splitwise API key (stored
  locally), map each person to a Splitwise friend, and push a summary expense — with the
  PDF breakdown attached and a comment — in one click.

## Two ways to get expenses in

1. **App upload** — start the app and drag a statement PDF into the browser.
2. **Claude Code harness** — open a [Claude Code](https://claude.com/claude-code)
   session in this folder and paste the prompt in [`LAUNCH.md`](./LAUNCH.md). It runs the
   same deterministic parser, **self-verifies** the numbers, can read statements from
   banks beyond Apple Card by reasoning over them, and opens the app already populated.

## Quick start

```bash
./start.sh
```

Opens the app at <http://localhost:8000>. Then:

1. **People & Settings** → add the people you split with, pick a default partner.
2. **Review** → upload a statement PDF; tag expenses personal / split.
3. **Totals** → see who owes you, pick a scope (all statements or one), and export
   CSV / PDF, or push to Splitwise.

### Run manually

```bash
python3 -m src.server      # serves the app at http://localhost:8000
```

### Run the test suite

```bash
python3 -m unittest discover -s tests -v
```

## Privacy & data

- All data lives in `data/` on your machine (`expenses.json`, `rules.json`,
  `settings.json`) — **gitignored and never committed**.
- Your statement PDFs and any Splitwise API key stay local. The key is stored in
  `settings.json` (treat that file like a password).
- The only outbound network calls are the Splitwise API requests you explicitly trigger.

## How it's built

- **Python 3**, standard library only for the server (`http.server`) — no web framework,
  no build step.
- Dependencies (see [`requirements.txt`](./requirements.txt)): `pypdf` (read statement
  PDFs) and `fpdf2` (generate PDF summaries). `start.sh` installs them automatically.
- **Frontend:** vanilla HTML/CSS/JS (the "Sorbet" theme), talking to the local server
  over `fetch`.
- Core logic is small, focused, and unit-tested: parsing, merchant normalization,
  integer-cent money math, categorization, splitting, totals, CSV/PDF export, and the
  Splitwise client.

| Module | Responsibility |
|---|---|
| `src/parser.py` | Apple Card statement text → transactions + reconciliation |
| `src/pdf_text.py` | Extract text from a PDF (`pypdf`) |
| `src/merchant.py` | Merchant extraction + stable match key for rules |
| `src/money.py` | Integer-cent math (exact 2-decimal splits) |
| `src/categories.py` | Default categories + keyword guesser |
| `src/expense.py` | Build expenses from transactions, applying rules + defaults |
| `src/splitter.py` | Per-person share computation |
| `src/reports.py` | Totals, "total spent", CSV exports |
| `src/pdf_export.py` | Branded per-person / combined PDF summaries |
| `src/store.py` | JSON persistence |
| `src/ingest.py` | Parse → build → dedup → verification report |
| `src/harness.py` | CLI used by the Claude Code harness |
| `src/splitwise.py` | Splitwise API client (connect, push, comment) |
| `src/server.py` | Local HTTP server: JSON API + static frontend + exports |

## Design docs

- Spec: [`docs/specs/2026-06-06-expense-splitter-design.md`](./docs/specs/2026-06-06-expense-splitter-design.md)
- Build plan: [`docs/plans/2026-06-06-expense-splitter.md`](./docs/plans/2026-06-06-expense-splitter.md)

## Status & scope

Personal project. Apple Card PDFs are supported by the built-in parser; other banks are
handled via the Claude Code harness. Scanned/image-only statements (which would need OCR)
are out of scope.
