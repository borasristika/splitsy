import unittest
from src.categories import DEFAULT_CATEGORIES, guess_category


class TestCategories(unittest.TestCase):
    def test_known_merchants(self):
        self.assertEqual(guess_category("STARBUCKS"), "Coffee")
        self.assertEqual(guess_category("SAFEWAY"), "Grocery")
        self.assertEqual(guess_category("INDIA CASH & CARRY"), "Grocery")
        self.assertEqual(guess_category("SEPHORA"), "Beauty")
        self.assertEqual(guess_category("UBER *TRIP"), "Transport")
        self.assertEqual(guess_category("SPOTIFY USA"), "Subscriptions")

    def test_unknown_is_miscellaneous(self):
        self.assertEqual(guess_category("ZZQ UNKNOWN VENDOR"), "Miscellaneous")

    def test_miscellaneous_is_last_category(self):
        self.assertEqual(DEFAULT_CATEGORIES[-1], "Miscellaneous")


if __name__ == "__main__":
    unittest.main()
