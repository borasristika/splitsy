import os
import unittest
from src.parser import parse_applecard

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "applecard_sample.txt")


class TestParser(unittest.TestCase):
    def setUp(self):
        with open(FIX, encoding="utf-8") as f:
            self.result = parse_applecard(f.read(), source="AppleCard 2026-01")

    def test_skips_payments_section(self):
        descs = [t["rawDescription"] for t in self.result["transactions"]]
        self.assertFalse(any("ACH Deposit" in d for d in descs))

    def test_transaction_count(self):
        self.assertEqual(len(self.result["transactions"]), 4)

    def test_first_transaction_fields(self):
        t = self.result["transactions"][0]
        self.assertEqual(t["date"], "2025-12-31")
        self.assertEqual(t["amount"], 33.13)
        self.assertEqual(t["merchant"], "SHEIN.COM")
        self.assertEqual(t["source"], "AppleCard 2026-01")

    def test_ignores_promo_subline(self):
        uber = [t for t in self.result["transactions"] if t["merchant"].startswith("UBER")][0]
        self.assertEqual(uber["amount"], 15.63)

    def test_reconciles_to_reported_total(self):
        total = round(sum(t["amount"] for t in self.result["transactions"]), 2)
        self.assertEqual(total, 105.80)
        self.assertEqual(self.result["reportedTotal"], 105.80)
        self.assertTrue(self.result["reconciles"])


if __name__ == "__main__":
    unittest.main()
