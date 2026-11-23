# Nain Capital Analytics

**Portfolio risk and return analytics for Indian equities**

A Python + SQL tool that measures how a portfolio of Indian (NSE) stocks has really performed, and how much risk it took to get there, compared with the NIFTY 50 index.

It downloads daily prices, stores them in a SQLite database, calculates standard risk and return measures, and produces a report with charts.

![Growth of 1 rupee: portfolio vs NIFTY 50](reports/growth_vs_benchmark.png)

## What it answers

- **Did my portfolio beat the market?** Time-weighted annual return (CAGR) vs the NIFTY 50.
- **How bumpy was the ride?** Annualised volatility and the worst fall from a peak (max drawdown).
- **Was the return worth the risk?** Sharpe ratio, and beta to the market.
- **Am I really diversified?** Correlation between holdings and allocation by value.

## Example results

On the sample portfolio in `portfolio.csv` (five large-cap NSE stocks bought between 2021 and 2022, prices to Nov 2026):

| | Annual return | Volatility | Max drawdown | Sharpe |
|---|---|---|---|---|
| Portfolio | +1.6% | 16.3% | -39.0% | -0.21 |
| NIFTY 50 | +10.5% | 14.2% | -17.2% | 0.35 |

What the analysis shows:

- **The portfolio underperformed the index by about 9% a year**, with more risk (higher volatility and more than double the drawdown).
- **The two IT stocks drove it.** Infosys (-32%) and TCS (-5%) were the biggest losers, and their daily returns are highly correlated (0.72). The portfolio was less diversified than five stocks suggests.
- **Infosys is the largest position by value despite its loss**, because it was the biggest purchase. Position sizing mattered more than stock count.

| Risk vs return | Correlation |
|---|---|
| ![Risk vs return](reports/risk_return.png) | ![Correlation of daily returns](reports/correlation.png) |

The full output is in [`reports/summary.md`](reports/summary.md).

## How it works

```
portfolio.csv ──► SQLite (holdings)          sql/positions.sql ──► cost, value, gain per stock
Yahoo Finance ──► SQLite (prices) ──────────►sql/monthly_returns.sql
                                     └──────► Python metrics ──► charts + report
```

| Part | What it does |
|---|---|
| `analyser/fetch.py` | Downloads split- and dividend-adjusted daily closes with `yfinance` |
| `sql/schema.sql` | `prices` and `holdings` tables |
| `sql/positions.sql` | Buy price, latest price and gain per holding, using a correlated subquery and `ROW_NUMBER()` |
| `sql/monthly_returns.sql` | Month-end returns using `ROW_NUMBER()` and `LAG()` window functions |
| `analyser/metrics.py` | CAGR, volatility, drawdown, Sharpe, beta, and a time-weighted portfolio index |
| `analyser/charts.py` | Five charts (matplotlib) |
| `tests/test_metrics.py` | Unit tests for the calculations |

### Method notes

- **Time-weighted returns.** Buying a new stock adds money but isn't a gain. The portfolio index only uses holdings owned the day before, so later purchases don't distort performance. This is why the time-weighted return (+9.5% total) differs from the simple invested-vs-value figure (+0.7%): the largest purchase (Infosys) came later and fell.
- **Risk-free rate.** The Sharpe ratio assumes 6.5% a year, roughly an Indian government bond yield. Change it with `--risk-free`.
- **Buy price** is the adjusted close on the first trading day on or after each buy date.

## Run it

Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

python main.py                  # download prices and build the report
python main.py --offline        # rebuild from stored prices, no download
python -m unittest discover tests
```

To analyse your own portfolio, edit `portfolio.csv`:

```csv
ticker,name,shares,buy_date
RELIANCE.NS,Reliance Industries,10,2021-01-04
```

NSE tickers end in `.NS` (BSE: `.BO`). Output goes to `reports/`.

## Tech

Python · pandas · SQLite (window functions, CTEs) · matplotlib · yfinance · unittest

---

*Built for analysis and learning. Not investment advice. The sample portfolio is illustrative.*
