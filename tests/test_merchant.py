import unittest
from src.merchant import extract_merchant, match_key


class TestMerchant(unittest.TestCase):
    def test_extract_simple(self):
        self.assertEqual(
            extract_merchant("STARBUCKS 05981 348 W EL CAMINO REAL SUNNYVALE 94087 CA USA"),
            "STARBUCKS")

    def test_extract_dotcom(self):
        self.assertEqual(
            extract_merchant("SHEIN.COM 383 madison ave NEW YORK 10179 NY USA"),
            "SHEIN.COM")

    def test_extract_strips_sq_prefix(self):
        self.assertEqual(
            extract_merchant("SQ *SHAHI DARBAR INDIA26953 Mission Blvd Ste F Hayward 94544 CA USA"),
            "SHAHI DARBAR INDIA")

    def test_extract_no_number(self):
        self.assertEqual(extract_merchant("Spotify USA"), "Spotify USA")

    def test_match_key_uppercases_and_caps_tokens(self):
        self.assertEqual(match_key("STARBUCKS"), "STARBUCKS")
        self.assertEqual(match_key("Spotify USA"), "SPOTIFY USA")
        self.assertEqual(match_key("SHAHI DARBAR INDIA RESTAURANT EXTRA"), "SHAHI DARBAR INDIA")


if __name__ == "__main__":
    unittest.main()
