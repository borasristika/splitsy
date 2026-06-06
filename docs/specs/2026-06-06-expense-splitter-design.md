# Expense Splitter — Design Spec

**Date:** 2026-06-06
**Status:** Approved design, pending implementation plan

## 1. Purpose

A personal, local app that ingests credit-card / bank statements (starting with
Apple Card PDFs), turns them into a reviewable list of expenses, and helps the
user decide which expenses are **personal** vs **split with other people** — then
exports a CSV the user can send to those people for review.

The app is for one user (the owner). There is no multi-user account system and no
cloud database. All data lives in local files on the user's machine.

## 2. Key decisions (settled during brainstorming)

| Topic | Decision |
|---|---|
| Statement format | Apple Card **PDF** (clean, selectable text — verified against a real January 2026 statement). Other banks may come later. |
| Platform | Local **browser app** served by a tiny local **Node** server. No cloud, no external database. |
| Intelligence | **Hybrid.** Works fully offline with a keyword categorizer; can be launched through **Claude Code** for smart LLM categorization. |
| Storage | JSON files on disk: `expenses.json`, `rules.json`, `people.json`/settings. |
| Merchant rules | Matched by **merchant name only** (e.g. tagging "Starbucks" covers all Starbucks locations). |
| People | Named **contacts** (e.g. "Nitin"). Default partner + default split configurable in Settings. |
| Default per expense | Apply saved rule → else **Split 2 ways with default partner (Nitin)**. Category guessed (keyword or Claude); unsure → **Miscellaneous**. |
| Split math | **Equal by default, you included**; override per expense for more people, custom shares, or excluding yourself. |
| Personal / Split actions | Each has **"once"** (this instance) and **"always this merchant"** (a remembered rule). |
| Remove button | Equivalent to **Personal (once)** — pulls the expense out of any split. No separate hard-delete. |
| Categories | Built-in buckets + new ones discovered over time. Re-categorizing a merchant is remembered. Miscellaneous shown last. |
| CSV export | **Per-person** and **combined**, both available. |
| Launch prompt | A `LAUNCH.md` file with an exact copy-paste prompt for the Claude Code smart-mode flow. |

## 3. Two ways to use the app

One codebase, one set of data files, two ingest paths:

| | Offline mode | Smart mode (Claude Code) |
|---|---|---|
| Launch | One-line start command (or Claude Code starts it) | Paste the `LAUNCH.md` prompt into a Claude Code session |
| Parse PDF | Built-in parser | Same built-in parser |
| Categorize | Keyword dictionary (learns from corrections) | Claude Code reasons over merchants, may invent new categories |
| Result | Upload in browser, then tag & export | App opens already grouped, then tag & export |

Both modes read and write the **same files**, so corrections made in one mode are
respected by the other. Smart mode always applies the user's saved `rules.json`
first, and only reasons about merchants that have no rule yet.

### Privacy note

In **offline mode**, nothing leaves the machine. In **smart mode**, statement
text passes through Anthropic's cloud (because the model runs there) during
categorization — the same data exposure as the Anthropic API, but riding on the
user's existing Claude Code session with no separate key or per-call billing. To
limit exposure, smart-mode categorization sends **only merchant names**, not
amounts or personal details.

## 4. Core concepts (data model)

- **Expense** — one transaction:
  `{ id, date, merchant, rawDescription, amount, category, status, split }`
  - `status`: `"split"` | `"personal"`
  - `split` (when status is split): `{ participants: [personIds...], includeSelf: bool, shares: "equal" | { personId: amount } }`
  - `id` is derived from `date + rawDescription + amount` (stable across re-ingests, enables dedup).
- **Person** — `{ id, name }`. The owner ("you") is implicit, not a Person record.
- **Merchant rule** — keyed by normalized merchant name:
  `{ merchantName, handling: "personal" | "split" | null, category: string | null, defaultSplit?: {...} }`
- **Settings** — `{ defaultPartnerId, defaultSplitWays, categories: [...] }`

### Files on disk

- `expenses.json` — current working set of expenses with their tags.
- `rules.json` — remembered merchant handling + category mappings.
- `people.json` — people + settings (or a combined `settings.json`).

These are plain JSON; backing up = copying the files.

## 5. Ingest flow

1. User provides one or more Apple Card PDFs.
2. Parser extracts transactions:
   - Reads the **Transactions** section (date, description, daily cash %, daily cash $, amount).
   - **Skips** the Payments section and negative/refund rows by default.
   - Splits each description into a **merchant name** (leading text) and the rest (address/store #).
3. For each expense, in priority order:
   1. Matching **merchant rule** → apply its handling + category.
   2. Otherwise → **default: Split 2 ways with the default partner**, plus a category
      from the keyword dictionary (offline) or Claude (smart mode); unknown → Miscellaneous.
4. **Dedup** by `id` so re-uploading the same statement doesn't double-count.
5. Write `expenses.json`. In smart mode, Claude Code then starts the server and opens the app.

## 6. Categorization

- **Default buckets:** Coffee, Grocery, Restaurants, Beauty, Shopping, Transport,
  Subscriptions, Miscellaneous. The set can grow (Claude may add new ones; user may add their own).
- **Offline brain:** a pre-loaded keyword → category dictionary (e.g. `STARBUCKS`→Coffee,
  `SAFEWAY`/`INDIA CASH & CARRY`→Grocery, `SEPHORA`→Beauty, `SHAHI DARBAR`→Restaurants,
  `UBER`→Transport, `SPOTIFY`/`UDEMY`→Subscriptions). Unknown → Miscellaneous.
- **Learning:** when the user re-categorizes a merchant ("always" option), it's saved to
  `rules.json` and applied on every future ingest. Miscellaneous shrinks over time.
- **Smart brain:** Claude Code categorizes unknown merchants by reasoning, and may
  introduce categories beyond the default set when warranted.

## 7. Screens

### Upload
Drag-drop PDFs; shows count of transactions read and how many matched existing rules.
(Offline mode uses this; smart mode pre-populates and skips straight to Review.)

### Review list
Expenses **grouped by category**, Miscellaneous last. Each row shows date, merchant,
amount, category, and current status. Per-row actions:

- **Personal (once)** / **Personal (always this merchant)**
- **Split (once)** / **Split (always this merchant)** → opens split editor
- **Change category (once / always)**

The "Remove" affordance maps to **Personal (once)**.

### Split editor
- Pick which **people** share the expense (multi-select from contacts).
- Equal by default, **you included**.
- Override: custom amounts/percentages per person, or **exclude yourself**.

### People & Settings
- Manage people (add/rename/remove).
- Set **default partner** and **default split** (e.g. 2 ways with Nitin).
- View/edit merchant rules and category mappings.

### Export
- **Per-person CSV:** pick a person → every split expense they share, with date,
  merchant, total, their share, category.
- **Combined CSV:** all split expenses, a column per person's share.

## 8. Split math

- Equal split divides the amount among all participants **including you** by default
  (split with Nitin = 2 ways; with Nitin + Priya = 3 ways).
- Per-expense overrides: change the participant set, set custom shares, or exclude
  yourself so others cover the full amount.
- CSV shows each **other** person their share (not yours).

## 9. Tech & architecture

- **Node** tiny local server:
  - Serves the static frontend.
  - REST-ish endpoints to read/write `expenses.json`, `rules.json`, settings.
  - Hosts shared logic so it runs without Claude Code.
- **Shared JS modules** (used by both server and browser, unit-tested):
  - `parser` — Apple Card PDF → transactions (via `pdfjs-dist`).
  - `categorizer` — keyword dictionary + rule application.
  - `splitter` — split math and CSV generation.
- **Frontend:** plain HTML/CSS/JS (no heavy framework needed for this scope).
- **`LAUNCH.md`:** exact copy-paste prompt instructing a Claude Code session to
  parse provided statements, apply `rules.json`, categorize the rest, write
  `expenses.json`, start the server, and open the app.

### Module boundaries

| Module | Does | Depends on |
|---|---|---|
| `parser` | PDF bytes → `[{date, description, amount, ...}]` | `pdfjs-dist` |
| `categorizer` | transaction + rules → `{category, status, split}` | `rules.json` shape |
| `splitter` | expenses → per-person/combined CSV strings | data model only |
| `server` | persistence + serving | parser, categorizer, splitter |
| `frontend` | UI for review/tag/export | server endpoints |

## 10. Testing

- Unit tests for `parser` against the **real January 2026 Apple Card statement**
  as a fixture (correct transaction count, amounts, merchant extraction, Payments
  section excluded).
- Unit tests for `splitter` (equal, custom, exclude-self, per-person vs combined CSV).
- Unit tests for `categorizer` (keyword hits, rule precedence, Miscellaneous fallback,
  learning persistence).

## 11. Out of scope (for now / YAGNI)

- Banks other than Apple Card (design keeps the parser swappable, but only Apple Card is built).
- OCR for scanned/image PDFs.
- Multi-user accounts, authentication, cloud sync.
- Settling/payment tracking (who actually paid back) — the app produces the CSV; reconciliation is manual.
- The optional "bring-your-own Anthropic API key" button (Claude Code covers the smart path; can be added later).
