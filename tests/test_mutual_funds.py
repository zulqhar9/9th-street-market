"""Tests for the mutual fund list parser, trailing returns and SIP backtests (no network)."""
import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyser import mutual_funds as mf  # noqa: E402

SAMPLE = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date

Open Ended Schemes(Equity Schemes - Large Cap Fund)

Axis Mutual Fund

1001;INF1;-;Axis Bluechip Fund;Direct Plan;Growth Option;60.12;26-Nov-2026
1002;INF2;-;Axis Bluechip Fund;Direct Plan;IDCW Option;20.50;26-Nov-2026
1003;INF3;-;Axis Bluechip Fund;Regular Plan;Growth Option;52.00;26-Nov-2026

Open Ended Schemes(Equity Scheme - Dividend Yield Fund)

Sample Mutual Fund

1004;INF4;-;Sample Dividend Yield Fund;Direct Plan;Growth;30.00;26-Nov-2026
1005;INF5;-;Old Wound Up Fund;Direct Plan;Growth;10.00;01-Jan-2024

Close Ended Schemes(Income)

Sample Mutual Fund

1006;INF6;-;Fixed Term Plan Series 9;Direct Plan;Growth;11.00;26-Nov-2026
"""


def monthly_nav(start: str, years: int, annual: float) -> pd.Series:
    days = pd.bdate_range(start, periods=years * 260)
    t = (days - days[0]).days / 365.25
    return pd.Series(10 * (1 + annual) ** t, index=days)


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.df = mf.parse_navall(SAMPLE).set_index("code")

    def test_keeps_open_ended_growth_options_only(self):
        self.assertEqual(sorted(self.df.index), [1001, 1003, 1004])

    def test_groups_plans_and_categories(self):
        self.assertEqual(self.df.loc[1001, "group"], "Equity")
        self.assertEqual(self.df.loc[1001, "category"], "Large Cap")
        self.assertEqual(self.df.loc[1001, "plan"], "Direct")
        self.assertEqual(self.df.loc[1003, "plan"], "Regular")
        self.assertEqual(self.df.loc[1001, "amc"], "Axis Mutual Fund")

    def test_dividend_yield_funds_are_not_mistaken_for_payout_options(self):
        self.assertEqual(self.df.loc[1004, "category"], "Dividend Yield")

    def test_category_aliases(self):
        self.assertEqual(mf._group_and_category("Open Ended Schemes(Equity Scheme - ELSS)"),
                         ("Equity", "ELSS (tax saver)"))
        self.assertEqual(mf._group_and_category("Open Ended Schemes(Other Scheme - Index Funds)"),
                         ("Index funds & ETFs", "Equity"))


class ReturnTests(unittest.TestCase):
    def test_trailing_return_annualised(self):
        nav = monthly_nav("2020-01-01", 6, 0.12)
        self.assertAlmostEqual(mf.trailing_return(nav, 3), 0.12, delta=0.005)
        self.assertIsNone(mf.trailing_return(nav, 10))

    def test_xirr_of_a_single_deposit(self):
        flows = [(pd.Timestamp("2020-01-01"), -100.0), (pd.Timestamp("2021-01-01"), 110.0)]
        self.assertAlmostEqual(mf.xirr(flows), 0.10, delta=0.002)

    def test_sip_backtest_recovers_steady_growth(self):
        nav = monthly_nav("2018-01-01", 8, 0.12)
        r = mf.sip_backtest(nav, 5_000, 5)
        self.assertEqual(r.instalments, 60)
        self.assertAlmostEqual(r.invested, 300_000)
        self.assertAlmostEqual(r.xirr, 0.12, delta=0.01)
        self.assertGreater(r.value, r.invested)

    def test_sip_backtest_needs_enough_history(self):
        self.assertIsNone(mf.sip_backtest(monthly_nav("2025-01-01", 1, 0.1), 1_000, 5))


if __name__ == "__main__":
    unittest.main()
