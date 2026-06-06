import unittest
from src.splitter import compute_shares


def split_exp(amount, participants, include_self=True, shares="equal"):
    return {"amount": amount, "status": "split",
            "split": {"participants": participants, "includeSelf": include_self, "shares": shares}}


class TestSplitter(unittest.TestCase):
    def test_equal_two_way_with_self(self):
        e = split_exp(30.00, ["p1"], include_self=True)
        self.assertEqual(compute_shares(e), {"p1": 15.00})

    def test_equal_three_way_with_self(self):
        e = split_exp(30.00, ["p1", "p2"], include_self=True)
        self.assertEqual(compute_shares(e), {"p1": 10.00, "p2": 10.00})

    def test_equal_excludes_self(self):
        e = split_exp(30.00, ["p1", "p2"], include_self=False)
        self.assertEqual(compute_shares(e), {"p1": 15.00, "p2": 15.00})

    def test_remainder_cent_is_deterministic(self):
        e = split_exp(10.00, ["p1", "p2"], include_self=True)  # 3 ways
        shares = compute_shares(e)
        self.assertEqual(shares, {"p1": 3.33, "p2": 3.33})

    def test_custom_shares_passthrough(self):
        e = split_exp(30.00, ["p1", "p2"], shares={"p1": 20.00, "p2": 10.00})
        self.assertEqual(compute_shares(e), {"p1": 20.00, "p2": 10.00})

    def test_custom_shares_must_reconcile(self):
        e = split_exp(30.00, ["p1", "p2"], shares={"p1": 20.00, "p2": 5.00})
        with self.assertRaises(ValueError):
            compute_shares(e)

    def test_personal_has_no_shares(self):
        e = {"amount": 5.0, "status": "personal",
             "split": {"participants": [], "includeSelf": True, "shares": "equal"}}
        self.assertEqual(compute_shares(e), {})


if __name__ == "__main__":
    unittest.main()
