import os
import tempfile
import unittest
from src.snapshot import fingerprint, render_html
from src import history

PEOPLE = [{"id": "p1", "name": "Nitin"}]


def exp(eid, merchant, amount, participants, status="split", category="Coffee"):
    return {"id": eid, "date": "2026-01-01", "merchant": merchant, "amount": amount,
            "category": category, "status": status, "source": "AppleCard 2026-01",
            "rawDescription": merchant, "matchKey": merchant.upper(),
            "split": {"participants": participants, "includeSelf": True, "shares": "equal"}}


class TestSnapshotFingerprint(unittest.TestCase):
    def test_same_state_same_fingerprint(self):
        a = [exp("a", "STARBUCKS", 30.0, ["p1"])]
        b = [exp("a", "STARBUCKS", 30.0, ["p1"])]
        self.assertEqual(fingerprint(a, PEOPLE), fingerprint(b, PEOPLE))

    def test_change_changes_fingerprint(self):
        a = [exp("a", "STARBUCKS", 30.0, ["p1"])]
        b = [exp("a", "STARBUCKS", 30.0, [], status="personal")]
        self.assertNotEqual(fingerprint(a, PEOPLE), fingerprint(b, PEOPLE))

    def test_render_html_has_totals(self):
        html = render_html([exp("a", "STARBUCKS", 30.0, ["p1"])], PEOPLE, "2026-06-07T12:00:00")
        self.assertIn("<html", html)
        self.assertIn("Total spent", html)
        self.assertIn("Nitin owes you", html)


class TestHistoryDedup(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.exps = [exp("a", "STARBUCKS", 30.0, ["p1"])]

    def test_first_snapshot_created_then_deduped(self):
        rec1, created1 = history.maybe_snapshot(self.dir, self.exps, PEOPLE, "t1", "20260607-120000")
        self.assertTrue(created1)
        rec2, created2 = history.maybe_snapshot(self.dir, self.exps, PEOPLE, "t2", "20260607-120100")
        self.assertFalse(created2)              # unchanged -> no new snapshot
        self.assertEqual(rec1["id"], rec2["id"])
        self.assertEqual(len(history.load_index(self.dir)), 1)

    def test_change_creates_new_snapshot(self):
        history.maybe_snapshot(self.dir, self.exps, PEOPLE, "t1", "20260607-120000")
        changed = [exp("a", "STARBUCKS", 30.0, [], status="personal")]
        rec, created = history.maybe_snapshot(self.dir, changed, PEOPLE, "t2", "20260607-120100")
        self.assertTrue(created)
        self.assertEqual(len(history.load_index(self.dir)), 2)
        self.assertIsNotNone(history.read_snapshot(self.dir, rec["id"]))

    def test_snapshot_file_is_readable_html(self):
        rec, _ = history.maybe_snapshot(self.dir, self.exps, PEOPLE, "t1", "20260607-120000")
        html = history.read_snapshot(self.dir, rec["id"])
        self.assertIn("<html", html)


if __name__ == "__main__":
    unittest.main()
