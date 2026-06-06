import tempfile
import unittest
from src.store import Store, default_settings


class TestStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = Store(self.dir)

    def test_defaults_when_empty(self):
        self.assertEqual(self.store.load_expenses(), [])
        self.assertEqual(self.store.load_rules(), {})
        s = self.store.load_settings()
        self.assertEqual(s["defaultSplitWays"], 2)
        self.assertIn("Miscellaneous", s["categories"])

    def test_roundtrip_expenses(self):
        self.store.save_expenses([{"id": "x", "amount": 1.0}])
        self.assertEqual(self.store.load_expenses(), [{"id": "x", "amount": 1.0}])

    def test_roundtrip_rules(self):
        self.store.save_rules({"STARBUCKS": {"matchKey": "STARBUCKS", "handling": "personal", "category": None}})
        self.assertEqual(self.store.load_rules()["STARBUCKS"]["handling"], "personal")

    def test_default_settings_shape(self):
        s = default_settings()
        self.assertEqual(s["people"], [])
        self.assertIsNone(s["defaultPartnerId"])


if __name__ == "__main__":
    unittest.main()
