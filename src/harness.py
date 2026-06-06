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
