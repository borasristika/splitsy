import os
import unittest
from src.ingest import ingest_text

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "applecard_sample.txt")
SETTINGS = {"people": [{"id": "p1", "name": "Nitin"}], "defaultPartnerId": "p1",
            "defaultSplitWays": 2, "categories": [], "statementFolder": None}


class TestIngest(unittest.TestCase):
    def setUp(self):
        with open(FIX, encoding="utf-8") as f:
            self.text = f.read()

    def test_produces_expenses_and_report(self):
        result = ingest_text(self.text, source="AppleCard 2026-01",
                             existing=[], rules={}, settings=SETTINGS)
        self.assertEqual(len(result["expenses"]), 4)
        self.assertTrue(result["report"]["reconciles"])
        self.assertEqual(result["report"]["count"], 4)

    def test_dedup_against_existing(self):
        first = ingest_text(self.text, source="AppleCard 2026-01",
                            existing=[], rules={}, settings=SETTINGS)["expenses"]
        again = ingest_text(self.text, source="AppleCard 2026-01",
                           existing=first, rules={}, settings=SETTINGS)["expenses"]
        self.assertEqual(len(again), 4)


if __name__ == "__main__":
    unittest.main()
