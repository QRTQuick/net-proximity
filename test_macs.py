import unittest

from backend.models import normalize_mac


class TestNormalizeMac(unittest.TestCase):
    def test_colon_mac(self):
        self.assertEqual(normalize_mac("AA:BB:CC:DD:EE:FF"), "aa:bb:cc:dd:ee:ff")

    def test_dash_mac(self):
        self.assertEqual(normalize_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")

    def test_raw_mac(self):
        self.assertEqual(normalize_mac("aabbccddeeff"), "aa:bb:cc:dd:ee:ff")

    def test_invalid_mac(self):
        self.assertIsNone(normalize_mac("not-a-mac"))


if __name__ == "__main__":
    unittest.main()
