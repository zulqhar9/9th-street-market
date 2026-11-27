"""'What if I had invested?' calculations for stocks, the NIFTY 50, gold and silver (all in rupees)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from analyser import metrics
from analyser.live import GOLD, GRAMS_PER_TROY_OUNCE, NIFTY, SILVER, USD_INR

# Assets that aren't single NSE stocks: display name -> how to price them.
BITCOIN, ETHEREUM = "BTC-USD", "ETH-USD"
SPECIAL = {"NIFTY 50": NIFTY, "Gold": GOLD, "Silver": SILVER, "Bitcoin": BITCOIN, "Ethereum": ETHEREUM}
METALS = (GOLD, SILVER)        # US$ per troy ounce
DOLLAR_PRICED = (BITCOIN, ETHEREUM)  # US$ per coin


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


def to_rupees(close: pd.DataFrame, ticker: str) -> pd.Series:
    """Turn a dollar-priced asset's closes into rupees using each day's exchange rate.

    Gold and silver become rupees per gram; crypto becomes rupees per coin. Crypto also trades at
    weekends when currency markets are shut, so the last known exchange rate is carried forward.
    """
    close = close.sort_index().ffill()
    rupees = close[ticker] * close[USD_INR]
    if ticker in METALS:
        rupees = rupees / GRAMS_PER_TROY_OUNCE
    return rupees.dropna()


def rupee_prices(ticker: str, start: str) -> pd.Series:
    """Daily prices in rupees from `start`. Stocks use dividend-adjusted closes;
    gold, silver and crypto are converted from US$ at each day's exchange rate."""
    dollar_priced = ticker in METALS or ticker in DOLLAR_PRICED
    tickers = [ticker, USD_INR] if dollar_priced else [ticker]
    close = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(ticker)
    if ticker not in close or close[ticker].dropna().empty:
        raise ValueError(f"No prices found for {ticker} from {start}.")
    if dollar_priced:
        return to_rupees(close, ticker)
    return close[ticker].dropna()
