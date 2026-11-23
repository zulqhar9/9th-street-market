"""One analysis pipeline shared by the command-line report and the website."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import pandas as pd

from analyser import BENCHMARK, BENCHMARK_NAME, db, metrics


@dataclass
class Analysis:
    holdings: pd.DataFrame       # holdings that have price data
    positions: pd.DataFrame      # cost, value and gain per holding (from sql/positions.sql)
    close: pd.DataFrame          # wide table of closes, one column per ticker
    portfolio: pd.Series         # time-weighted growth of 1.0
    table: pd.DataFrame          # risk/return metrics: Portfolio, benchmark, then each stock
    stock_returns: pd.DataFrame  # daily returns of each holding, columns named by company


def run(conn: sqlite3.Connection, holdings: pd.DataFrame, risk_free: float) -> Analysis:
    """Compute every metric from prices and holdings already stored in `conn`."""
    close = db.load_close_prices(conn)
    if BENCHMARK not in close:
        raise ValueError("No benchmark (NIFTY 50) prices stored yet.")
    positions = db.query(conn, "positions")
    holdings = holdings[holdings["ticker"].isin(positions["ticker"])]
    if holdings.empty:
        raise ValueError("No price data for any holding.")

    names = holdings.set_index("ticker")["name"]
    market = close[BENCHMARK]
    portfolio = metrics.portfolio_index(close, holdings)

    rows = {"Portfolio": {**metrics.summarise(portfolio, market, risk_free), "kind": "portfolio"}}
    rows[BENCHMARK_NAME] = {
        **metrics.summarise(market.loc[portfolio.index[0]:], market, risk_free), "kind": "benchmark"
    }
    for h in holdings.itertuples():
        series = close[h.ticker].loc[h.buy_date:]
        rows[names[h.ticker]] = {**metrics.summarise(series, market, risk_free), "kind": "stock"}

    stock_returns = (close[holdings["ticker"]].loc[portfolio.index[0]:]
                     .pct_change().rename(columns=names))
    return Analysis(holdings, positions, close, portfolio,
                    pd.DataFrame.from_dict(rows, orient="index"), stock_returns)
