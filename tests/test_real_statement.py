import os
import unittest
from src.pdf_text import extract_text
from src.parser import parse_applecard

REAL = os.path.expanduser("~/Desktop/Apple Card Statement - January 2026.pdf")


@unittest.skipUnless(os.path.exists(REAL), "real statement not present")
class TestRealStatement(unittest.TestCase):
    def test_parses_and_reconciles(self):
        text = extract_text(REAL)
        result = parse_applecard(text, source="AppleCard 2026-01")
        self.assertGreater(len(result["transactions"]), 0)
        if result["reportedTotal"] is not None:
            self.assertTrue(result["reconciles"],
                            f"parsed ${result['sumOfTransactions']} != reported ${result['reportedTotal']}")


if __name__ == "__main__":
    unittest.main()
