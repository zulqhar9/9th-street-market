"""Tests for the SIP calculator maths (no network)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyser import sip  # noqa: E402


class SipTests(unittest.TestCase):
    def test_flat_sip_matches_closed_form(self):
        df = sip.schedule(5_000, 0.12, 10)
        self.assertAlmostEqual(df["value"].iloc[-1], sip.future_value(5_000, 0.12, 10), places=4)
        self.assertEqual(df["invested"].iloc[-1], 5_000 * 120)

    def test_known_value(self):
        # ₹5,000/month for 10 years at 12% a year is about ₹11.6 lakh (standard SIP calculators agree).
        self.assertAlmostEqual(sip.future_value(5_000, 0.12, 10), 1_161_695, delta=5)

    def test_zero_return_is_just_the_money_put_in(self):
        df = sip.schedule(1_000, 0.0, 3)
        self.assertAlmostEqual(df["value"].iloc[-1], 36_000)

    def test_step_up_raises_instalments_each_year(self):
        df = sip.schedule(10_000, 0.12, 3, step_up=0.10)
        self.assertEqual(sorted(df["instalment"].round(2).unique()), [10_000.0, 11_000.0, 12_100.0])
        self.assertAlmostEqual(df["invested"].iloc[-1], 12 * (10_000 + 11_000 + 12_100))

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            sip.schedule(0, 0.12, 10)


if __name__ == "__main__":
    unittest.main()
