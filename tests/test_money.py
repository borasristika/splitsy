import unittest
from src.money import to_cents, to_dollars, split_equal


class TestMoney(unittest.TestCase):
    def test_to_cents_rounds_half_up(self):
        self.assertEqual(to_cents(33.13), 3313)
        self.assertEqual(to_cents(0.55), 55)
        self.assertEqual(to_cents(15.625), 1563)  # round half up

    def test_to_dollars(self):
        self.assertEqual(to_dollars(3313), 33.13)
        self.assertEqual(to_dollars(5), 0.05)

    def test_split_equal_even(self):
        self.assertEqual(split_equal(3000, 3), [1000, 1000, 1000])

    def test_split_equal_remainder_distributed(self):
        self.assertEqual(split_equal(1000, 3), [334, 333, 333])
        self.assertEqual(sum(split_equal(1000, 3)), 1000)

    def test_split_equal_one_way(self):
        self.assertEqual(split_equal(4505, 1), [4505])


if __name__ == "__main__":
    unittest.main()
