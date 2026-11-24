"""Tests for NSE market-hours detection (no network needed)."""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyser.live import IST, market_status  # noqa: E402


def ist(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=IST)


class MarketStatusTests(unittest.TestCase):
    def test_open_on_a_normal_trading_afternoon(self):
        is_open, _ = market_status(ist(2026, 11, 23, 14, 0), last_trade=ist(2026, 11, 23, 13, 55))
        self.assertTrue(is_open)

    def test_closed_on_weekend(self):
        is_open, _ = market_status(ist(2026, 11, 22, 11, 0))  # Sunday
        self.assertFalse(is_open)

    def test_closed_after_hours(self):
        is_open, _ = market_status(ist(2026, 11, 23, 16, 0))
        self.assertFalse(is_open)

    def test_weekday_holiday_detected_from_missing_trades(self):
        is_open, label = market_status(ist(2026, 11, 24, 13, 50), last_trade=ist(2026, 11, 23, 15, 25))
        self.assertFalse(is_open)
        self.assertIn("holiday", label)

    def test_no_holiday_call_in_first_minutes_after_open(self):
        is_open, _ = market_status(ist(2026, 11, 24, 9, 20), last_trade=ist(2026, 11, 23, 15, 25))
        self.assertTrue(is_open)


if __name__ == "__main__":
    unittest.main()
