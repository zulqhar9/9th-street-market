"""Tests for the widget board helpers (no network)."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from webapp.widgets import DOWN, UP, indian, sparkline  # noqa: E402


class IndianGroupingTests(unittest.TestCase):
    def test_lakh_and_crore_grouping(self):
        self.assertEqual(indian(108155), "1,08,155")
        self.assertEqual(indian(12345678), "1,23,45,678")
        self.assertEqual(indian(999), "999")
        self.assertEqual(indian(25349.65, 2), "25,349.65")

    def test_negative_uses_true_minus_sign(self):
        self.assertEqual(indian(-450.95, 2), "−450.95")


class SparklineTests(unittest.TestCase):
    def test_colour_follows_direction(self):
        self.assertIn(UP, sparkline(pd.Series([1.0, 2.0, 3.0]), 100, 30))
        self.assertIn(DOWN, sparkline(pd.Series([3.0, 2.0, 1.0]), 100, 30))

    def test_too_short_series_draws_nothing(self):
        self.assertEqual(sparkline(pd.Series([1.0]), 100, 30), "")


if __name__ == "__main__":
    unittest.main()
