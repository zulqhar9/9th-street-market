"""Tests for the capital gains tax calculator (no network)."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyser import tax  # noqa: E402


class TaxTests(unittest.TestCase):
    def test_short_term_gain_at_20_percent_plus_cess(self):
        r = tax.capital_gains(100, 1_000, 1_500, date(2025, 1, 10), date(2025, 6, 10))
        self.assertFalse(r.long_term)
        self.assertAlmostEqual(r.gain, 50_000)
        self.assertAlmostEqual(r.tax, 10_000)
        self.assertAlmostEqual(r.total_tax, 10_400)

    def test_long_term_gain_above_exemption(self):
        r = tax.capital_gains(100, 1_000, 3_000, date(2023, 5, 1), date(2025, 5, 1))
        self.assertTrue(r.long_term)
        self.assertAlmostEqual(r.exempt, 1_25_000)
        self.assertAlmostEqual(r.taxable, 75_000)
        self.assertAlmostEqual(r.tax, 75_000 * 0.125)

    def test_long_term_gain_under_exemption_is_tax_free(self):
        r = tax.capital_gains(10, 1_000, 5_000, date(2022, 1, 1), date(2025, 1, 1))
        self.assertEqual(r.total_tax, 0)

    def test_exemption_already_used_this_year(self):
        r = tax.capital_gains(10, 1_000, 5_000, date(2022, 1, 1), date(2025, 1, 1), exemption_used=1_00_000)
        self.assertAlmostEqual(r.exempt, 25_000)
        self.assertAlmostEqual(r.taxable, 15_000)

    def test_twelve_months_exactly_is_still_short_term(self):
        self.assertFalse(tax.is_long_term(date(2024, 3, 15), date(2025, 3, 15)))
        self.assertTrue(tax.is_long_term(date(2024, 3, 15), date(2025, 3, 16)))

    def test_old_rates_before_23_july_2024(self):
        r = tax.capital_gains(100, 1_000, 1_500, date(2024, 1, 10), date(2024, 7, 22))
        self.assertAlmostEqual(r.rate, 0.15)
        old = tax.rules_for(date(2024, 3, 31))
        self.assertEqual((old.ltcg_rate, old.ltcg_exemption), (0.10, 1_00_000))

    def test_grandfathering_steps_up_cost(self):
        r = tax.capital_gains(10, 500, 2_000, date(2016, 1, 1), date(2025, 1, 1), fmv_2018=1_200)
        self.assertAlmostEqual(r.cost, 12_000)
        self.assertAlmostEqual(r.gain, 8_000)

    def test_loss_has_no_tax_and_charges_add_to_cost(self):
        r = tax.capital_gains(10, 1_000, 900, date(2025, 1, 1), date(2025, 2, 1), charges=50)
        self.assertAlmostEqual(r.gain, -1_050)
        self.assertEqual(r.total_tax, 0)

    def test_financial_year_label(self):
        self.assertEqual(tax.financial_year(date(2026, 3, 31)), "FY 2025-26")
        self.assertEqual(tax.financial_year(date(2026, 4, 1)), "FY 2026-27")

    def test_rejects_sale_before_purchase(self):
        with self.assertRaises(ValueError):
            tax.capital_gains(1, 100, 120, date(2025, 2, 1), date(2025, 1, 1))


if __name__ == "__main__":
    unittest.main()
