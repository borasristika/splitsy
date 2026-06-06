import unittest
from src.splitwise import build_expense_payload, SplitwiseError


def split_exp(amount, participants, include_self=True, merchant="STARBUCKS", date="2026-01-03"):
    return {"amount": amount, "status": "split", "merchant": merchant, "date": date,
            "rawDescription": merchant,
            "split": {"participants": participants, "includeSelf": include_self, "shares": "equal"}}

MAP = {"p1": 111, "p2": 222}


class TestSplitwisePayload(unittest.TestCase):
    def test_two_way_with_self(self):
        e = split_exp(30.00, ["p1"])  # p1 owes 15, I owe 15, I paid 30
        p = build_expense_payload(e, my_user_id=999, person_to_splitwise=MAP, group_id=0)
        self.assertEqual(p["cost"], "30.00")
        self.assertEqual(p["group_id"], 0)
        self.assertEqual(p["description"], "STARBUCKS")
        self.assertEqual(p["date"], "2026-01-03")
        self.assertEqual(p["users__0__user_id"], 999)
        self.assertEqual(p["users__0__paid_share"], "30.00")
        self.assertEqual(p["users__0__owed_share"], "15.00")
        self.assertEqual(p["users__1__user_id"], 111)
        self.assertEqual(p["users__1__paid_share"], "0.00")
        self.assertEqual(p["users__1__owed_share"], "15.00")

    def test_owed_shares_sum_to_cost_with_remainder(self):
        e = split_exp(10.00, ["p1", "p2"])  # 3-way: p1,p2 owe 3.33; I owe 3.34
        p = build_expense_payload(e, my_user_id=999, person_to_splitwise=MAP)
        owed = (float(p["users__0__owed_share"]) + float(p["users__1__owed_share"])
                + float(p["users__2__owed_share"]))
        self.assertEqual(round(owed, 2), 10.00)
        self.assertEqual(p["users__0__owed_share"], "3.34")  # I absorb the remainder
        self.assertEqual(p["users__1__owed_share"], "3.33")
        self.assertEqual(p["users__2__owed_share"], "3.33")

    def test_group_id_passthrough(self):
        e = split_exp(30.00, ["p1"])
        p = build_expense_payload(e, my_user_id=999, person_to_splitwise=MAP, group_id=42)
        self.assertEqual(p["group_id"], 42)

    def test_unmapped_person_raises(self):
        e = split_exp(30.00, ["pX"])
        with self.assertRaises(SplitwiseError):
            build_expense_payload(e, my_user_id=999, person_to_splitwise=MAP)


if __name__ == "__main__":
    unittest.main()
