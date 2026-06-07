import unittest
from src.pdf_export import per_person_pdf, combined_pdf

PEOPLE = [{"id": "p1", "name": "Nitin"}, {"id": "p2", "name": "Priya"}]


def exp(eid, merchant, amount, participants, category="Coffee", status="split"):
    return {"id": eid, "date": "2026-01-01", "merchant": merchant, "amount": amount,
            "category": category, "status": status, "source": "AppleCard 2026-01",
            "rawDescription": merchant, "matchKey": merchant.upper(),
            "split": {"participants": participants, "includeSelf": True, "shares": "equal"}}


EXPENSES = [
    exp("a", "STARBUCKS", 30.00, ["p1"]),
    exp("b", "SAFEWAY", 30.00, ["p1", "p2"], category="Grocery"),
    exp("c", "PERSONAL", 9.99, [], status="personal"),
]


class TestPdfExport(unittest.TestCase):
    def test_per_person_pdf_is_valid_pdf(self):
        data = per_person_pdf(EXPENSES, "p2", PEOPLE, "2026-06-07")
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(len(data), 500)

    def test_combined_pdf_is_valid_pdf(self):
        data = combined_pdf(EXPENSES, PEOPLE, "2026-06-07")
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(len(data), 500)

    def test_per_person_pdf_handles_no_rows(self):
        data = per_person_pdf([EXPENSES[2]], "p1", PEOPLE, "2026-06-07")
        self.assertTrue(data.startswith(b"%PDF"))

    def test_non_latin_merchant_does_not_crash(self):
        e = [exp("d", "CAFÉ MÜNCHEN ☕", 12.00, ["p1"])]
        data = per_person_pdf(e, "p1", PEOPLE, "2026-06-07")
        self.assertTrue(data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
