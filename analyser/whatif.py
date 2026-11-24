"""'What if I had invested?' calculations for stocks, the NIFTY 50, gold and silver (all in rupees)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from analyser import metrics
from analyser.live import GOLD, GRAMS_PER_TROY_OUNCE, NIFTY, SILVER, USD_INR

# Assets that aren't single NSE stocks: display name -> how to price them.
SPECIAL = {"NIFTY 50": NIFTY, "Gold": GOLD, "Silver": SILVER}


@dataclass
class Outcome:
    name: str
    value: pd.Series        # value of the investment over time, in rupees
    invested: float

    @property
    def final(self) -> float:
        return float(self.value.iloc[-1])

    @property
    def total_return(self) -> float:
        return self.final / self.invested - 1

    @property
    def cagr(self) -> float:
        return metrics.cagr(self.value)

    @property
    def worst_fall(self) -> float:
        return metrics.max_drawdown(self.value)


def grow(prices: pd.Series, amount: float) -> pd.Series:
    """Value over time of `amount` invested at the first price in `prices`."""
    prices = prices.dropna()
    if prices.empty or prices.iloc[0] <= 0:
        raise ValueError("No usable prices for this period.")
    return amount * prices / prices.iloc[0]


def rupee_prices(ticker: str, start: str) -> pd.Series:
    """Daily prices in rupees from `start`. Stocks use dividend-adjusted closes;
    gold and silver are converted from US$ per ounce to rupees per gram."""
    tickers = [ticker, USD_INR] if ticker in (GOLD, SILVER) else [ticker]
    close = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(ticker)
    if ticker not in close or close[ticker].dropna().empty:
        raise ValueError(f"No prices found for {ticker} from {start}.")
    if ticker in (GOLD, SILVER):
        close = close.ffill()
        return (close[ticker] * close[USD_INR] / GRAMS_PER_TROY_OUNCE).dropna()
    return close[ticker].dropna()
