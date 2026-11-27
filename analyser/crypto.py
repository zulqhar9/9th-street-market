"""Crypto prices: the biggest coins in dollars and rupees, with true 24-hour changes.

Crypto trades around the clock, so "today" means the last 24 hours, not a calendar day.
Prices are global (US$) prices from Yahoo Finance converted at the market exchange rate;
Indian exchanges such as CoinDCX or WazirX can show slightly different rupee prices.
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from analyser.world import USD_INR

COINS = {
    "BTC-USD": ("Bitcoin", "BTC"), "ETH-USD": ("Ethereum", "ETH"), "XRP-USD": ("XRP", "XRP"),
    "BNB-USD": ("BNB", "BNB"), "SOL-USD": ("Solana", "SOL"), "DOGE-USD": ("Dogecoin", "DOGE"),
    "ADA-USD": ("Cardano", "ADA"), "TRX-USD": ("TRON", "TRX"),
}


def change_24h(series: pd.Series) -> tuple[float, float, pd.Series]:
    """Latest price, change since the price 24 hours earlier, and the last 24 hours of prices."""
    s = series.dropna()
    if len(s) < 2:
        raise ValueError("Not enough prices.")
    now = s.index[-1]
    window = s.loc[now - pd.Timedelta(hours=24):]
    before = s.loc[:now - pd.Timedelta(hours=24)]
    base = before.iloc[-1] if len(before) else window.iloc[0]
    return float(s.iloc[-1]), float(s.iloc[-1] / base - 1), window


def snapshot() -> tuple[pd.DataFrame, dict[str, pd.Series], float | None]:
    """Price and 24h change for every coin (in US$), their last-24h price lines, and the US$→₹ rate."""
    data = yf.download(list(COINS) + [USD_INR], period="3d", interval="15m", auto_adjust=False,
                       progress=False, threads=True)
    if data.empty:
        raise RuntimeError("Yahoo Finance returned no data. Try again in a minute.")
    close = data["Close"]
    rows, lines = [], {}
    for t, (name, symbol) in COINS.items():
        if t not in close:
            continue
        try:
            price, chg, window = change_24h(close[t])
        except ValueError:
            continue
        rows.append({"ticker": t, "name": name, "symbol": symbol, "price": price, "change_pct": chg})
        lines[t] = window
    rate = close[USD_INR].dropna() if USD_INR in close else pd.Series(dtype=float)
    return pd.DataFrame(rows).set_index("ticker"), lines, (float(rate.iloc[-1]) if len(rate) else None)


def decimals_for(price: float) -> int:
    """Enough decimals for cheap coins ($0.0581) without cluttering big ones ($61,777.69)."""
    return 2 if price >= 1 else 4 if price >= 0.01 else 6
