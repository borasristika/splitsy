import unittest
from src.expense import make_expense, expense_id

TX = {
    "date": "2026-01-03", "rawDescription": "STARBUCKS 05981 ... CA USA",
    "merchant": "STARBUCKS", "matchKey": "STARBUCKS", "amount": 0.55,
    "source": "AppleCard 2026-01",
}
SETTINGS = {"people": [{"id": "p1", "name": "Nitin"}],
            "defaultPartnerId": "p1", "defaultSplitWays": 2,
            "categories": [], "statementFolder": None}


class TestExpense(unittest.TestCase):
    def test_id_is_stable(self):
        self.assertEqual(expense_id(TX), expense_id(dict(TX)))

    def test_default_is_split_with_partner(self):
        e = make_expense(TX, rules={}, settings=SETTINGS)
        self.assertEqual(e["status"], "split")
        self.assertEqual(e["split"]["participants"], ["p1"])
        self.assertTrue(e["split"]["includeSelf"])
        self.assertEqual(e["split"]["shares"], "equal")
        self.assertEqual(e["category"], "Coffee")

    def test_rule_marks_personal(self):
        rules = {"STARBUCKS": {"matchKey": "STARBUCKS", "handling": "personal", "category": None}}
        e = make_expense(TX, rules=rules, settings=SETTINGS)
        self.assertEqual(e["status"], "personal")

    def test_rule_overrides_category(self):
        rules = {"STARBUCKS": {"matchKey": "STARBUCKS", "handling": None, "category": "Restaurants"}}
        e = make_expense(TX, rules=rules, settings=SETTINGS)
        self.assertEqual(e["category"], "Restaurants")


if __name__ == "__main__":
    unittest.main()
