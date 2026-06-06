# Expense Splitter — Design Spec

**Date:** 2026-06-06
**Status:** Approved design, pending implementation plan

## 1. Purpose

A personal **harness + app** for turning credit-card / bank statements into a
reviewed list of expenses, deciding which are **personal** vs **split with other
people**, and exporting CSVs to send those people for review — ending with a clear
total of how much each person owes.

- The **app** is a local browser UI for reviewing, tagging, and exporting.
- The **harness** is a Claude Code workflow: point it at a folder of downloaded
  statements (Apple Card, Chase, Amex, anything with selectable text), and it reads,
  normalizes, and **self-verifies** them into the app's common format.

Single user (the owner). No cloud database, no accounts. All data is local files.

## 2. Key decisions (settled during brainstorming)

| Topic | Decision |
|---|---|
| Statement sources | **Any bank** via the harness (Apple Card, Chase, Amex, …) as long as the PDF has selectable text. The built-in **offline** parser handles **Apple Card** to start. |
| Ingest paths | (a) **Upload in the app** for one-offs; (b) **harness scans a configured statement folder** via Claude Code. |
| Accuracy | Harness must **self-verify**: re-read, reconcile to the statement's own totals, and produce a verification report. No tolerance for misreads or math errors. |
| Platform | Local **browser app** served by a tiny local **Python** server (stdlib `http.server`, zero extra runtime). No cloud, no external database. |
| Intelligence | **Hybrid.** Offline keyword categorizer + Apple Card parser (Python); or launch via **Claude Code**, which can call the same parser deterministically and add multi-bank reading + smart categorization. |
| Storage | JSON files on disk: `expenses.json`, `rules.json`, settings. |
| Merchant rules | Matched by **merchant name only** (tagging "Starbucks" covers all Starbucks). |
| People | Named **contacts** (e.g. "Nitin"). Default partner + default split configurable in Settings. |
| Default per expense | Apply saved rule → else **Split 2 ways with default partner (Nitin)**. Category guessed; unsure → **Miscellaneous**. |
| Split math | **Equal by default, you included**; override per expense for more people, custom shares, or excluding yourself. |
| Personal / Split actions | Each has **"once"** (this instance) and **"always this merchant"** (a remembered rule). |
| Remove button | Equivalent to **Personal (once)**. No separate hard-delete. |
| Categories | Built-in buckets + new ones over time. Re-categorizing a merchant is remembered. Miscellaneous shown last. |
| Submit → Totals | After review, **Submit** computes how much **each person owes**. |
| Export | **Review and publish** CSVs: **per-person** and **combined**. |
| Launch prompt | A `LAUNCH.md` file with an exact copy-paste prompt that includes the parse + **self-verification** protocol. |

## 3. Two ways to use the app

One codebase, one set of data files, two ingest paths:

| | App-upload mode | Harness mode (Claude Code) |
|---|---|---|
| Launch | One-line start command | Paste the `LAUNCH.md` prompt into a Claude Code session |
| Statement source | Files you pick in the browser | A **configured folder** Claude Code scans |
| Banks supported | Built-in parsers (Apple Card to start) | **Any** text-based statement, via reasoning |
| Categorize | Keyword dictionary (learns from corrections) | Claude reasons over merchants, may add categories |
| Accuracy | Deterministic parser + unit tests | **Self-verification protocol** (see §6) |
| Result | Upload in browser, then tag & export | App opens already grouped + verified, then tag & export |

Both modes read/write the **same files**, so corrections in one are respected by the
other. The harness always applies saved `rules.json` first, then reasons only about
merchants with no rule yet.

### Privacy note

App-upload mode with the offline parser keeps everything on the machine. Harness mode
sends statement text through Anthropic's cloud during reading/categorization — same
exposure as the Anthropic API, but on the existing Claude Code session (no separate
key or per-call billing). To limit exposure, categorization sends only merchant names.

## 4. Core concepts (data model)

- **Expense** — one transaction:
  `{ id, date, merchant, rawDescription, amount, source, category, status, split }`
  - `source`: which statement/bank it came from (e.g. `"AppleCard 2026-01"`).
  - `status`: `"split"` | `"personal"`
  - `split` (when split): `{ participants: [personIds...], includeSelf: bool, shares: "equal" | { personId: amount } }`
  - `id` is derived from `source + date + rawDescription + amount` (stable across re-ingests; enables dedup).
- **Person** — `{ id, name }`. The owner ("you") is implicit, not a Person record.
- **Merchant rule** — keyed by normalized merchant name:
  `{ merchantName, handling: "personal" | "split" | null, category: string | null, defaultSplit?: {...} }`
- **Settings** — `{ defaultPartnerId, defaultSplitWays, categories: [...], statementFolder }`

### Files on disk

- `expenses.json` — current working set of expenses with their tags.
- `rules.json` — remembered merchant handling + category mappings.
- `settings.json` — people, defaults, and the configured statement folder path.

Plain JSON; backup = copy the files.

## 5. Ingest flow

### App-upload mode
1. User picks one or more PDFs in the browser.
2. Built-in parser (Apple Card) extracts transactions.
3. Rules applied → defaults filled → dedup → written to `expenses.json`.

### Harness mode
1. User pastes the `LAUNCH.md` prompt; Claude Code reads the **configured statement folder**.
2. For each statement file, regardless of bank:
   - Extract every transaction: **date, merchant, amount** (+ raw description, source).
   - Skip payments/refunds/credits by default (negative amounts), but surface them in the report.
   - Normalize into the common **Expense** format.
3. **Self-verify** (see §6) before anything is written.
4. Apply saved rules → fill defaults → dedup → write `expenses.json`.
5. Start the server and open the app, already grouped and reconciled.

## 6. Accuracy & self-verification protocol (harness)

Financial correctness is non-negotiable. The harness must, for every statement:

1. **Two-pass read.** Extract transactions, then independently re-read the statement
   and diff the two extractions. Any disagreement is investigated, never guessed.
2. **Reconcile to the statement's own totals.** Sum the extracted transactions and
   compare against the statement's stated control figures (e.g. Apple Card "Total
   transactions for this period," balance math). If they don't match, stop and fix.
3. **Integrity checks.** No missed rows, no duplicates (unless a genuine repeat
   charge), every amount parses as a number, every date is valid, transaction count
   matches the statement.
4. **Verification report.** Emit a short report per statement: bank/source, count,
   summed total vs statement total (must reconcile), and any row flagged as uncertain.
   The user sees this before tagging.
5. **Split-math integrity** (applies to both modes): each expense's shares sum back to
   its amount; each person's grand total equals the sum of their shares across expenses.

Only data that passes 1–4 is written to `expenses.json`.

## 7. Categorization

- **Default buckets:** Coffee, Grocery, Restaurants, Beauty, Shopping, Transport,
  Subscriptions, Miscellaneous. The set can grow.
- **Offline brain:** keyword → category dictionary (e.g. `STARBUCKS`→Coffee,
  `SAFEWAY`/`INDIA CASH & CARRY`→Grocery, `SEPHORA`→Beauty, `SHAHI DARBAR`→Restaurants,
  `UBER`→Transport, `SPOTIFY`/`UDEMY`→Subscriptions). Unknown → Miscellaneous.
- **Learning:** re-categorizing a merchant ("always") saves to `rules.json` and applies
  on every future ingest. Miscellaneous shrinks over time.
- **Smart brain:** Claude categorizes unknown merchants by reasoning; may add categories.

## 8. Screens

### Upload
Drag-drop PDFs (app-upload mode); shows count read and how many matched existing rules.
Harness mode pre-populates and opens straight to Review with the verification report shown.

### Review list
Expenses **grouped by category**, Miscellaneous last. Each row: date, merchant, amount,
source, category, status. Per-row actions:

- **Personal (once)** / **Personal (always this merchant)**
- **Split (once)** / **Split (always this merchant)** → split editor
- **Change category (once / always)**

"Remove" maps to **Personal (once)**.

### Split editor
- Pick which **people** share the expense (multi-select).
- Equal by default, **you included**.
- Override: custom amounts/percentages, or **exclude yourself**.

### Submit → Totals
After review, **Submit** locks in the tagging and shows a **totals summary**: how much
**each person owes** (sum of their shares), with split-math integrity verified.

### People & Settings
- Manage people; set **default partner** + **default split**.
- Set the **statement folder** path the harness scans.
- View/edit merchant rules and category mappings.

### Review & Publish
- Review the export, then publish:
  - **Per-person CSV:** date, merchant, total, their share, category.
  - **Combined CSV:** all split expenses, a column per person's share.

## 9. Split math

- Equal split divides the amount among all participants **including you** by default
  (split with Nitin = 2 ways; with Nitin + Priya = 3 ways).
- Per-expense overrides: change participants, set custom shares, or exclude yourself.
- CSV shows each **other** person their share (not yours).
- All split math is verified per §6 (step 5).

## 10. Tech & architecture

- **Python 3** (stdlib only + `pypdf`): a tiny local server (`http.server`) serves the
  frontend and reads/writes `expenses.json`, `rules.json`, `settings.json`. No web
  framework, no Node, no build step.
- **Python modules** (unit-tested with built-in `unittest`):
  - `parser` — Apple Card PDF/text → transactions (`pypdf` for text extraction).
  - `categorizer` — keyword dictionary + rule application.
  - `splitter` — split math + CSV generation.
  - `totals` — per-person totals from tagged expenses.
- **Frontend:** plain HTML/CSS/JS (vanilla), talks to the local server via `fetch`. The
  browser is a thin UI; all parsing/logic lives server-side in Python (one implementation,
  reused by both app-upload and harness modes).
- **`LAUNCH.md`:** exact copy-paste prompt that tells a Claude Code session to scan the
  statement folder, run the deterministic Python parser, apply the **self-verification
  protocol (§6)**, apply `rules.json`, write `expenses.json`, start the server, open the app.

### Module boundaries

| Module | Does | Depends on |
|---|---|---|
| `money` | integer-cent math (no float errors) | stdlib |
| `merchant` | description → normalized merchant + match key | stdlib |
| `parser` | PDF/text → `[{date, description, amount, ...}]` + reconciliation | `pypdf` |
| `categorizer` | merchant + rules → `{category, status, split}` | `rules.json` shape |
| `splitter` | expenses → per-person/combined CSV strings | data model, `money` |
| `totals` | expenses → per-person owed amounts | data model, `money` |
| `store` | read/write JSON data files | stdlib |
| `server` | persistence + serving | all of the above |
| `frontend` | UI for review/tag/submit/export | server endpoints |

## 11. Testing

- `python3 -m unittest` (built-in, zero install).
- `parser` against a committed **synthetic Apple Card text fixture** (count, amounts,
  merchant extraction, Payments excluded, **reconciles to statement total**), plus an
  **optional integration test** against the real January 2026 PDF that skips when the
  file is absent (the real statement is never committed).
- `splitter` (equal, custom, exclude-self, per-person vs combined CSV).
- `totals` (per-person sums; integrity check that shares reconcile to amounts).
- `categorizer` (keyword hits, rule precedence, Miscellaneous fallback, learning).

## 12. Out of scope (for now / YAGNI)

- **OCR for scanned/image statements.** Harness handles text-based PDFs only; image-only
  statements are out until we add OCR.
- Additional **offline** bank parsers beyond Apple Card (multi-bank is a harness capability;
  offline parsing grows one bank at a time as needed).
- Multi-user accounts, authentication, cloud sync.
- Payback/settlement tracking (who actually paid) — the app produces CSVs + totals; actual
  reconciliation is manual.
- A standalone "bring-your-own Anthropic API key" button (the harness covers smart mode).
