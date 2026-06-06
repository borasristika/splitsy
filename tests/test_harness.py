import os
import tempfile
import json
import unittest
from src import harness

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "applecard_sample.txt")


class TestHarness(unittest.TestCase):
    def test_ingest_file_writes_and_reports(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "settings.json"), "w") as f:
            json.dump({"people": [{"id": "p1", "name": "Nitin"}], "defaultPartnerId": "p1",
                       "defaultSplitWays": 2, "categories": [], "statementFolder": None}, f)
        report = harness.ingest_statement_text_file(FIX, source="AppleCard 2026-01", data_dir=d)
        self.assertTrue(report["reconciles"])
        self.assertEqual(report["count"], 4)
        with open(os.path.join(d, "expenses.json")) as f:
            self.assertEqual(len(json.load(f)), 4)


if __name__ == "__main__":
    unittest.main()
