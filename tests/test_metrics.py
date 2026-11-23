"""Unit tests for the metric calculations, using small hand-made price series.

Run with:  python -m unittest discover tests
"""
import math
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyser import metrics  # noqa: E402


def series(values, start="2024-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


class MetricTests(unittest.TestCase):
    def test_max_drawdown(self):
        # Peak 120, trough 90 -> 25% fall, even though it later recovers to a new high.
        self.assertAlmostEqual(metrics.max_drawdown(series([100, 120, 90, 110, 130])), -0.25)

    def test_cagr_doubling_in_one_year(self):
        prices = pd.Series([100.0, 200.0], index=pd.to_datetime(["2023-01-01", "2024-01-01"]))
        self.assertAlmostEqual(metrics.cagr(prices), 1.0, places=2)

    def test_beta_of_market_is_one(self):
        rets = metrics.daily_returns(series([100, 101, 99, 103, 102, 105]))
        self.assertAlmostEqual(metrics.beta(rets, rets), 1.0)

    def test_sharpe_of_flat_series_is_nan(self):
        rets = metrics.daily_returns(series([100] * 10))
        self.assertTrue(math.isnan(metrics.sharpe_ratio(rets, 0.0)))

    def test_portfolio_index_ignores_new_money(self):
        # Stock A is flat; stock B is bought on day 3 and stays flat.
        # Buying B adds money but must not count as a gain.
        prices = pd.DataFrame(
            {"A": [100, 100, 100, 100], "B": [50, 50, 50, 50]},
            index=pd.bdate_range("2024-01-01", periods=4),
            dtype=float,
        )
        holdings = pd.DataFrame({
            "ticker": ["A", "B"],
            "shares": [1, 10],
            "buy_date": ["2024-01-01", "2024-01-03"],
        })
        index = metrics.portfolio_index(prices, holdings)
        self.assertTrue((index == 1.0).all())

    def test_portfolio_index_weights_by_value(self):
        # Equal money in A and B; A rises 10%, B is flat -> portfolio up 5%.
        prices = pd.DataFrame(
            {"A": [100, 110], "B": [100, 100]},
            index=pd.bdate_range("2024-01-01", periods=2),
            dtype=float,
        )
        holdings = pd.DataFrame({"ticker": ["A", "B"], "shares": [1, 1],
                                 "buy_date": ["2024-01-01", "2024-01-01"]})
        self.assertAlmostEqual(metrics.portfolio_index(prices, holdings).iloc[-1], 1.05)


if __name__ == "__main__":
    unittest.main()
