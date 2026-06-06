import unittest
from src.reports import per_person_totals, per_person_csv, combined_csv

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
