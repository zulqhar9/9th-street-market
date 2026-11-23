"""Download daily prices from Yahoo Finance (NSE tickers end in .NS)."""
from __future__ import annotations

import pandas as pd
import yfinance as yf


def download_prices(tickers: list[str], start: str) -> tuple[pd.DataFrame, set[str]]:
    """Return long-format prices (date, ticker, close, volume) and any tickers with no data."""
    raw = yf.download(
        tickers, start=start, auto_adjust=True, progress=False, group_by="column", threads=True
    )
    if raw.empty:
        raise RuntimeError("Yahoo Finance returned no data. Check your internet connection and tickers.")

    close, volume = raw["Close"], raw["Volume"]
    if isinstance(close, pd.Series):  # single ticker on some yfinance versions
        close, volume = close.to_frame(tickers[0]), volume.to_frame(tickers[0])

    def to_long(frame: pd.DataFrame, value: str) -> pd.DataFrame:
        return frame.rename_axis("date").reset_index().melt(
            id_vars="date", var_name="ticker", value_name=value
        )

    prices = to_long(close, "close").merge(to_long(volume, "volume"), on=["date", "ticker"])
    prices = prices.dropna(subset=["close"])
    prices["date"] = pd.to_datetime(prices["date"]).dt.strftime("%Y-%m-%d")

    missing = set(tickers) - set(prices["ticker"])
    return prices[["date", "ticker", "close", "volume"]], missing
