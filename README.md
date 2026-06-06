# Expense Splitter

Local tool to turn bank/credit-card statements into a reviewed list of expenses,
tag each as personal or split-with-people, and export CSVs + per-person totals.

See `docs/specs/2026-06-06-expense-splitter-design.md` for the design and
`docs/plans/2026-06-06-expense-splitter.md` for the build plan.

## Quick start
    ./start.sh
Opens the app at http://localhost:8000. Add people in Settings, then upload a statement.

## Run (app mode)
    python3 -m src.server
Then open http://localhost:8000

## Run (harness mode)
Open a Claude Code session in this folder and paste the prompt in `LAUNCH.md`.

## Test
    python3 -m unittest discover -s tests -v

Requires Python 3 and `pypdf` (`python3 -m pip install pypdf`).
