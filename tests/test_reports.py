import unittest
from src.reports import per_person_totals, per_person_csv, combined_csv, owner_total, total_spent
from src.money import to_cents

PEOPLE = [{"id": "p1", "name": "Nitin"}, {"id": "p2", "name": "Priya"}]


def exp(eid, merchant, amount, participants, category="Misc", include_self=True, shares="equal", status="split"):
    return {"id": eid, "date": "2026-01-01", "merchant": merchant, "amount": amount,
            "category": category, "status": status, "source": "AppleCard 2026-01",
            "rawDescription": merchant, "matchKey": merchant.upper(),
            "split": {"participants": participants, "includeSelf": include_self, "shares": shares}}


EXPENSES = [
    exp("a", "STARBUCKS", 30.00, ["p1"]),            # p1 owes 15
    exp("b", "SAFEWAY", 30.00, ["p1", "p2"]),        # p1,p2 owe 10 each
    exp("c", "PERSONAL THING", 9.99, [], status="personal"),
]


class TestReports(unittest.TestCase):
    def test_per_person_totals(self):
        self.assertEqual(per_person_totals(EXPENSES), {"p1": 25.00, "p2": 10.00})

    def test_total_spent(self):
        # 30 + 30 + 9.99
        self.assertEqual(total_spent(EXPENSES), 69.99)

    def test_total_spent_equals_owner_plus_others(self):
        others = sum(to_cents(v) for v in per_person_totals(EXPENSES).values())
        self.assertEqual(to_cents(total_spent(EXPENSES)), to_cents(owner_total(EXPENSES)) + others)

    def test_owner_total(self):
        # STARBUCKS 30 split p1 -> you 15; SAFEWAY 30 split p1,p2 -> you 10; personal 9.99 -> you 9.99
        self.assertEqual(owner_total(EXPENSES), 34.99)

    def test_breakdown_reconciles_to_grand_total(self):
        # owner + everyone else must equal the sum of all expense amounts, to the cent
        others = sum(to_cents(v) for v in per_person_totals(EXPENSES).values())
        you = to_cents(owner_total(EXPENSES))
        grand = sum(to_cents(e["amount"]) for e in EXPENSES)
        self.assertEqual(you + others, grand)

    def test_breakdown_reconciles_with_remainder_cents(self):
        # 3-way split of 10.00 (you + p1 + p2): you 3.34, p1 3.33, p2 3.33 -> sums to 10.00
        exps = [exp("r", "ODD", 10.00, ["p1", "p2"])]
        others = sum(to_cents(v) for v in per_person_totals(exps).values())
        you = to_cents(owner_total(exps))
        self.assertEqual(you + others, 1000)
        self.assertEqual(owner_total(exps), 3.34)

    def test_per_person_csv_only_their_expenses(self):
        csv = per_person_csv(EXPENSES, "p2", PEOPLE)
        lines = csv.strip().splitlines()
        self.assertEqual(lines[0], "Date,Merchant,Category,Total,Your Share")
        self.assertEqual(len(lines), 2)  # header + 1 expense for p2
        self.assertIn("SAFEWAY", lines[1])
        self.assertTrue(lines[1].endswith("10.0") or lines[1].endswith("10.00"))

    def test_combined_csv_has_column_per_person(self):
        csv = combined_csv(EXPENSES, PEOPLE)
        header = csv.strip().splitlines()[0]
        self.assertEqual(header, "Date,Merchant,Category,Total,Nitin,Priya")


if __name__ == "__main__":
    unittest.main()
