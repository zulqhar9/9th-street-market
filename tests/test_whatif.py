"""Tests for the 'what if I had invested' maths and Indian rupee formatting (no network)."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyser.live import inr_compact, inr_short  # noqa: E402
from analyser.whatif import Outcome, grow  # noqa: E402


class WhatIfTests(unittest.TestCase):
    def test_grow_scales_from_first_price(self):
        prices = pd.Series([50.0, 75.0, 100.0], index=pd.bdate_range("2024-01-01", periods=3))
        value = grow(prices, 10_000)
        self.assertEqual(list(value.round(2)), [10_000.0, 15_000.0, 20_000.0])

    def test_outcome_summary(self):
        value = pd.Series([10_000.0, 8_000.0, 30_000.0],
                          index=pd.to_datetime(["2023-01-01", "2023-06-01", "2024-01-01"]))
        o = Outcome("Test", value, 10_000)
        self.assertAlmostEqual(o.total_return, 2.0)
        self.assertAlmostEqual(o.worst_fall, -0.2)
        self.assertAlmostEqual(o.cagr, 2.0, places=1)

    def test_crypto_converts_per_coin_and_fills_weekend_rates(self):
        from analyser.whatif import BITCOIN, GOLD, USD_INR, to_rupees
        days = pd.to_datetime(["2026-11-20", "2026-11-21", "2026-11-22"])  # Fri, Sat, Sun
        close = pd.DataFrame({BITCOIN: [60_000.0, 61_000.0, 62_000.0], USD_INR: [90.0, None, None]}, index=days)
        self.assertEqual(list(to_rupees(close, BITCOIN)), [5_400_000.0, 5_490_000.0, 5_580_000.0])
        gold = pd.DataFrame({GOLD: [3110.35], USD_INR: [100.0]}, index=days[:1])
        self.assertAlmostEqual(to_rupees(gold, GOLD).iloc[0], 10_000.0, places=0)  # ₹ per gram

    def test_grow_rejects_empty_prices(self):
        with self.assertRaises(ValueError):
            grow(pd.Series(dtype=float), 1000)


class RupeeFormatTests(unittest.TestCase):
    def test_lakh_crore_crore_and_plain(self):
        self.assertEqual(inr_compact(18.28e12), "₹18.28 lakh crore")
        self.assertEqual(inr_compact(4_520e7), "₹4,520 crore")
        self.assertEqual(inr_compact(95_000), "₹95,000")
        self.assertEqual(inr_compact(None), "n/a")

    def test_short_form_for_cards(self):
        self.assertEqual(inr_short(8.9e12), "₹8.90L cr")
        self.assertEqual(inr_short(3_577e7), "₹3,577 cr")


if __name__ == "__main__":
    unittest.main()
