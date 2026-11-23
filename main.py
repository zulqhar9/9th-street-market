"""Stock Portfolio Analyser.

Usage:
    python main.py                      # download latest prices and build the report
    python main.py --offline            # reuse prices already stored in the database
    python main.py --portfolio my.csv --risk-free 0.07
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from analyser import BENCHMARK, BENCHMARK_NAME, charts, db, metrics
from analyser.report import write_report

ROOT = Path(__file__).resolve().parent
REQUIRED_COLUMNS = {"ticker", "name", "shares", "buy_date"}


def load_portfolio(path: Path) -> pd.DataFrame:
    holdings = pd.read_csv(path, dtype={"ticker": str, "name": str, "buy_date": str})
    missing = REQUIRED_COLUMNS - set(holdings.columns)
    if missing:
        sys.exit(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
    holdings["buy_date"] = pd.to_datetime(holdings["buy_date"]).dt.strftime("%Y-%m-%d")
    if (holdings["shares"] <= 0).any():
        sys.exit("Every holding needs a positive number of shares.")
    if holdings["ticker"].duplicated().any():
        sys.exit("Each ticker should appear only once in the portfolio file.")
    return holdings


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse an NSE stock portfolio against the NIFTY 50.")
    parser.add_argument("--portfolio", type=Path, default=ROOT / "portfolio.csv")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "market.db")
    parser.add_argument("--out", type=Path, default=ROOT / "reports")
    parser.add_argument("--risk-free", type=float, default=0.065,
                        help="annual risk-free rate for the Sharpe ratio (default 0.065 = 6.5%%)")
    parser.add_argument("--offline", action="store_true", help="skip downloading; use stored prices")
    args = parser.parse_args()

    holdings = load_portfolio(args.portfolio)
    conn = db.connect(args.db)
    db.save_holdings(conn, holdings)

    if not args.offline:
        from analyser.fetch import download_prices

        tickers = holdings["ticker"].tolist() + [BENCHMARK]
        print(f"Downloading prices for {len(tickers)} tickers from {holdings['buy_date'].min()}...")
        prices, missing = download_prices(tickers, start=holdings["buy_date"].min())
        print(f"Stored {db.save_prices(conn, prices):,} price rows in {args.db.name}.")
        if missing:
            print(f"Warning: no data for {', '.join(sorted(missing))}. Check the ticker symbols.")

    close = db.load_close_prices(conn)
    if BENCHMARK not in close:
        sys.exit("No benchmark prices stored yet. Run once without --offline.")
    positions = db.query(conn, "positions")
    holdings = holdings[holdings["ticker"].isin(positions["ticker"])]
    if holdings.empty:
        sys.exit("No price data for any holding. Run once without --offline.")

    names = holdings.set_index("ticker")["name"]
    market = close[BENCHMARK]
    portfolio = metrics.portfolio_index(close, holdings)

    rows = {"Portfolio": {**metrics.summarise(portfolio, market, args.risk_free), "kind": "portfolio"}}
    rows[BENCHMARK_NAME] = {
        **metrics.summarise(market.loc[portfolio.index[0]:], market, args.risk_free), "kind": "benchmark"
    }
    for h in holdings.itertuples():
        series = close[h.ticker].loc[h.buy_date:]
        rows[names[h.ticker]] = {**metrics.summarise(series, market, args.risk_free), "kind": "stock"}
    table = pd.DataFrame.from_dict(rows, orient="index")

    args.out.mkdir(parents=True, exist_ok=True)
    stock_returns = close[holdings["ticker"]].loc[portfolio.index[0]:].pct_change().rename(columns=names)
    chart_files = [
        charts.growth_vs_benchmark(portfolio, market, BENCHMARK_NAME, args.out),
        charts.drawdown_chart(metrics.drawdown(portfolio), args.out),
        charts.allocation(positions, args.out),
        charts.risk_return(table, args.out),
        charts.correlation(stock_returns, args.out),
    ]
    monthly = db.query(conn, "monthly_returns")
    monthly.to_csv(args.out / "monthly_returns.csv", index=False)

    report = write_report(positions, table, chart_files, args.out, BENCHMARK_NAME, args.risk_free)
    conn.close()

    port, bench = table.loc["Portfolio"], table.loc[BENCHMARK_NAME]
    print(f"\nPortfolio CAGR {port.cagr:+.1%} vs {BENCHMARK_NAME} {bench.cagr:+.1%}; "
          f"max drawdown {port.max_drawdown:.1%}; Sharpe {port.sharpe:.2f}")
    print(f"Report written to {report}")


if __name__ == "__main__":
    main()
