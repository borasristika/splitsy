# Design brief — Expense Splitter (paste into Claude / a UI design tool)

> Paste everything in the fenced block below into Claude (use Artifacts) or any
> "design me a UI" tool. It will produce a single interactive HTML/CSS mockup that
> we then implement for real.

```
You are designing the UI for a personal web app called "Expense Splitter."

GOAL
Produce ONE self-contained, interactive HTML file (inline CSS, a little vanilla JS for
tab switching and opening the split dialog) that I can open in a browser and click
through. No frameworks, no build step, no external CDNs or libraries. System font stack
or a single Google Font via <link> is fine. Use realistic SAMPLE DATA (below) so it
looks alive. This is a high-fidelity clickable mockup, not a real backend.

WHAT THE APP DOES (context)
It's a local, single-user tool. I upload my credit-card/bank statements; the app lists
every expense and lets me mark each one as "personal" (just mine) or "split" with one or
more people. It remembers per-merchant rules ("always personal" / "always split"). It
groups expenses by category. At the end it shows how much each person owes me and lets me
export CSVs or push the expenses to Splitwise. It must feel trustworthy with money:
numbers are clear, totals are obvious, nothing feels sloppy.

VISUAL DIRECTION: PLAYFUL & COLORFUL
- Friendly, lively, and fun — NOT a stiff banking app — but still clean and readable.
- Bold, cheerful accent palette. Define a small design system inline: a primary color,
  2–3 secondary colors, success (green) and warning (amber/red) states, plus a distinct
  COLOR + EMOJI ICON per expense category (see categories). Round, soft cards with gentle
  shadows. Generous spacing. Expressive but legible headings; relaxed, human microcopy
  (e.g. "Nice — that all adds up ✨", "Just yours", "Split it").
- Money must stay crisp: tabular/monospaced figures, right-aligned, never ambiguous.
- Color-code categories consistently everywhere (group headers, little chips on rows).
- Must be accessible: strong contrast, don't rely on color alone (pair color with text/icon),
  visible focus states, works at desktop widths ~1000–1280px (desktop-first; graceful down
  to ~700px).

CATEGORIES (each gets a color + emoji)
Coffee ☕, Grocery 🛒, Restaurants 🍽️, Beauty 💄, Shopping 🛍️, Transport 🚗,
Subscriptions 🔁, Miscellaneous 🧩. Miscellaneous is always shown LAST.

GLOBAL LAYOUT
- A top app bar with the app name/logo (make a fun little wordmark) and a tab nav:
  "Review", "Totals", "People & Settings".
- Directly under the bar, a dismissible VERIFICATION BANNER that shows after an upload:
  success style — "✓ AppleCard Jan 2026: 42 transactions, $920.55 — reconciles with your
  statement 🎉"; and a warning variant — "⚠ Parsed total $X doesn't match the statement's
  $Y. Take a look." Design both states.

SCREEN 1 — REVIEW (the main screen)
- An upload zone at the top: a big friendly drag-&-drop / "Upload statement PDF" control,
  with a tiny note that it can also be populated by the companion tool.
- Below it, the expense list GROUPED BY CATEGORY. Each group is a card with a colored
  header (category color + emoji + name + count + group subtotal).
- Each expense ROW shows: date, merchant name, a small category chip, a "split with…"
  subtitle (e.g. "Split with Nitin" or "Just yours"), and the amount (right-aligned).
- Each row has 4 quick actions (design these as clear, friendly buttons/toggles):
  "Personal" (this one only), "Always personal" (remember this merchant),
  "Split…" (opens the split dialog), "Always split" (remember this merchant).
- A row currently marked PERSONAL looks visually de-emphasized (dimmed / muted), so
  split vs personal is obvious at a glance. Show the current state clearly (e.g. the
  active choice is highlighted).
- Show at least 8–10 sample rows spread across several categories, including one personal
  row and one split-with-two-people row.

SPLIT DIALOG (modal) — opened by "Split…"
- Title: "Split: <merchant> — $<amount>".
- A checklist of people to split with (checkboxes), plus an "Include me" toggle (on by
  default). A friendly line explaining the result, e.g. "3 ways — everyone pays $10.00".
- Cancel / Save buttons. Design it as a cheerful rounded modal.

SCREEN 2 — TOTALS
- A celebratory header summarizing the split, e.g. "Here's who owes you 💸".
- A clear list/cards: each person with their avatar/initial bubble (colorful), name, and
  the amount they owe (large, prominent). Show 1–2 people with realistic amounts.
- For each person: a "Download CSV" button and a Splitwise area — a small group dropdown
  ("No group (direct)" / a couple of sample groups) and a "Push <name> to Splitwise"
  button. Also one overall "Download combined CSV" button.
- After a push, show a friendly result toast/inline message ("Pushed 12, skipped 3 already
  sent ✅").

SCREEN 3 — PEOPLE & SETTINGS
- "People" section: list of people with colorful initial bubbles and a remove (x); an
  "Add person" inline form.
- "Defaults" section: a "Default partner" dropdown and a note that new expenses default to
  splitting 2 ways with them.
- "Statement folder" field (for the companion tool).
- "Splitwise (optional)" section: a password field for an API key + "Connect" button; once
  connected, a happy "Connected ✓" state and a person → Splitwise-friend mapping (a small
  row per person with a dropdown). Design both the disconnected and connected states.

SAMPLE DATA (use these, with plausible categories)
- 2025-12-31  SHEIN.COM            $33.13  (Shopping)   Split with Nitin
- 2025-12-31  SEPHORA              $38.19  (Beauty)     Split with Nitin
- 2025-12-31  HANKOOK SUPERMARKET  $24.73  (Grocery)    Split with Nitin
- 2026-01-01  SHAHI DARBAR         $45.05  (Restaurants) Split with Nitin & Priya
- 2026-01-02  SPOTIFY              $11.99  (Subscriptions) Just yours (personal)
- 2026-01-02  SAFEWAY              $16.60  (Grocery)    Split with Nitin
- 2026-01-03  STARBUCKS            $0.55   (Coffee)     Split with Nitin
- 2026-01-05  UBER *TRIP           $15.63  (Transport)  Split with Nitin
- 2026-01-08  APPLE.COM/BILL       $15.91  (Subscriptions) Just yours (personal)
- 2026-01-14  AMC                  $27.99  (Miscellaneous) Split with Nitin
People: Nitin (owes $460.15), Priya (owes $22.53). Sample groups: "Roommates", "Trip".

DELIVERABLE
A single HTML file implementing all three screens with the tab nav, the verification
banner (both states, even if one is hidden by default), the split modal, and the playful
visual system described above. Prioritize a design I can hand to a developer and have them
rebuild quickly. Keep the markup semantic and the CSS organized with comments so it's easy
to adapt.
```

## After you get the mockup
Send me the generated HTML (or paste it / drop the file in this folder). I'll adapt it
into the real app — wiring the live data, the upload/parse flow, tagging, totals, CSV
export, and the Splitwise push that already work under the hood. The mockup defines the
look; the existing backend stays.
