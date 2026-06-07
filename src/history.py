"""Persistent, deduplicated history of immutable review snapshots."""
import json
import os

from src.snapshot import fingerprint, render_html
from src.reports import per_person_totals, owner_total, total_spent, statements_included


def _dir(data_dir):
    d = os.path.join(data_dir, "history")
    os.makedirs(d, exist_ok=True)
    return d


def _index_path(data_dir):
    return os.path.join(_dir(data_dir), "index.json")


def load_index(data_dir):
    p = _index_path(data_dir)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save_index(data_dir, idx):
    with open(_index_path(data_dir), "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2)


def read_snapshot(data_dir, snap_id):
    """Return the HTML for a snapshot id, or None."""
    for rec in load_index(data_dir):
        if rec["id"] == snap_id:
            path = os.path.join(_dir(data_dir), rec["file"])
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return f.read()
    return None


def maybe_snapshot(data_dir, expenses, people, generated_on, stamp):
    """Create a snapshot unless the current state matches the most recent one.

    Returns (record, created_bool).
    """
    idx = load_index(data_dir)
    fp = fingerprint(expenses, people)
    if idx and idx[-1].get("fingerprint") == fp:
        return idx[-1], False
    snap_id = f"{stamp}-{len(idx)}"
    fname = f"snapshot-{snap_id}.html"
    with open(os.path.join(_dir(data_dir), fname), "w", encoding="utf-8") as f:
        f.write(render_html(expenses, people, generated_on))
    rec = {
        "id": snap_id,
        "timestamp": generated_on,
        "fingerprint": fp,
        "file": fname,
        "spent": total_spent(expenses),
        "you": owner_total(expenses),
        "owed": per_person_totals(expenses),
        "statements": statements_included(expenses),
        "expenseCount": len(expenses),
    }
    idx.append(rec)
    _save_index(data_dir, idx)
    return rec, True
