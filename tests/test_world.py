"""Tests for world market hours, US stock list and dollar formatting (no network)."""
import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyser import world  # noqa: E402
from analyser.live import IST  # noqa: E402

NY = world.MARKETS["US"].zone


class MarketHoursTests(unittest.TestCase):
    def test_new_york_open_on_a_weekday_morning(self):
        s = world.market_status(world.MARKETS["US"], datetime(2026, 11, 24, 10, 0, tzinfo=NY))
        self.assertEqual(s.state, "open")

    def test_closed_at_weekends_and_overnight(self):
        us = world.MARKETS["US"]
        self.assertEqual(world.market_status(us, datetime(2026, 11, 28, 11, 0, tzinfo=NY)).state, "closed")
        self.assertEqual(world.market_status(us, datetime(2026, 11, 24, 17, 0, tzinfo=NY)).state, "closed")

    def test_works_from_indian_time(self):
        # 8:30 pm IST on a Tuesday in November is 10:00 am in New York.
        s = world.market_status(world.MARKETS["US"], datetime(2026, 11, 24, 20, 30, tzinfo=IST))
        self.assertTrue(s.is_open)

    def test_tokyo_lunch_break(self):
        jp = world.MARKETS["JP"]
        s = world.market_status(jp, datetime(2026, 11, 24, 12, 0, tzinfo=jp.zone))
        self.assertEqual(s.label, "Lunch break")

    def test_holiday_when_nothing_traded_today(self):
        us = world.MARKETS["US"]
        now = datetime(2026, 11, 26, 11, 0, tzinfo=NY)          # Thanksgiving
        last = datetime(2026, 11, 25, 15, 55, tzinfo=NY)
        self.assertEqual(world.market_status(us, now, last).state, "holiday")

    def test_us_hours_in_ist_follow_daylight_saving(self):
        summer, _ = world.hours_in_ist(world.MARKETS["US"], date(2026, 7, 1))
        winter, _ = world.hours_in_ist(world.MARKETS["US"], date(2026, 12, 1))
        self.assertEqual((summer.hour, summer.minute), (19, 0))
        self.assertEqual((winter.hour, winter.minute), (20, 0))


class ListAndFormatTests(unittest.TestCase):
    def test_us_list_has_big_names_with_yahoo_symbols(self):
        us = world.us_equities().set_index("symbol")
        self.assertIn("AAPL", us.index)
        self.assertIn("BRK-B", us.index)
        self.assertGreater(len(us), 4000)

    def test_usd_short(self):
        self.assertEqual(world.usd_short(3.214e12), "$3.21T")
        self.assertEqual(world.usd_short(452.04e9), "$452.0B")
        self.assertEqual(world.usd_short(950_000), "$950,000")


if __name__ == "__main__":
    unittest.main()
