"""World markets: major global indices, top US stocks, US stock search and exchange trading hours.

Prices come from Yahoo Finance like the rest of the site (US stocks about real time to 15 minutes
delayed, other exchanges up to 20 minutes). Exchange hours are regular sessions; public holidays
are detected from whether anything has traded today, the same way as for the NSE.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from analyser.live import DATA, IST


@dataclass(frozen=True)
class Market:
    key: str
    country: str
    exchange: str
    tz: str
    open: time
    close: time
    lunch: tuple[time, time] | None = None

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)


MARKETS = {m.key: m for m in [
    Market("US", "United States", "NYSE · Nasdaq", "America/New_York", time(9, 30), time(16, 0)),
    Market("UK", "United Kingdom", "London Stock Exchange", "Europe/London", time(8, 0), time(16, 30)),
    Market("DE", "Germany", "Frankfurt (Xetra)", "Europe/Berlin", time(9, 0), time(17, 30)),
    Market("JP", "Japan", "Tokyo Stock Exchange", "Asia/Tokyo", time(9, 0), time(15, 30), (time(11, 30), time(12, 30))),
    Market("HK", "Hong Kong", "Hong Kong Exchange", "Asia/Hong_Kong", time(9, 30), time(16, 0), (time(12, 0), time(13, 0))),
    Market("AU", "Australia", "ASX", "Australia/Sydney", time(10, 0), time(16, 0)),
    Market("IN", "India", "NSE · BSE", "Asia/Kolkata", time(9, 15), time(15, 30)),
]}


@dataclass(frozen=True)
class Index:
    ticker: str
    name: str
    market: str


INDICES = [
    Index("^GSPC", "S&P 500", "US"),
    Index("^IXIC", "Nasdaq", "US"),
    Index("^DJI", "Dow Jones", "US"),
    Index("^FTSE", "FTSE 100", "UK"),
    Index("^GDAXI", "DAX", "DE"),
    Index("^N225", "Nikkei 225", "JP"),
    Index("^HSI", "Hang Seng", "HK"),
    Index("^AXJO", "ASX 200", "AU"),
]

# The largest US companies, plus Accenture as the closest US peer of India's IT firms.
US_TOP = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon", "GOOGL": "Alphabet (Google)",
    "META": "Meta", "AVGO": "Broadcom", "TSLA": "Tesla", "BRK-B": "Berkshire Hathaway", "JPM": "JPMorgan Chase",
    "LLY": "Eli Lilly", "V": "Visa", "WMT": "Walmart", "NFLX": "Netflix", "ORCL": "Oracle", "ACN": "Accenture",
}
USD_INR = "INR=X"


def us_equities() -> pd.DataFrame:
    """Every US-listed common stock and ADR (about 5,900): symbol, name, exchange, ticker, label."""
    df = pd.read_csv(DATA / "us_equities.csv", dtype=str, keep_default_na=False)
    df["ticker"] = df["symbol"]
    df["label"] = df["name"] + " (" + df["exchange"] + ": " + df["symbol"] + ")"
    return df


@dataclass(frozen=True)
class Status:
    state: str          # "open", "lunch", "closed" or "holiday"
    local: datetime     # the exchange's local time now

    @property
    def is_open(self) -> bool:
        return self.state == "open"

    @property
    def label(self) -> str:
        return {"open": "Open", "lunch": "Lunch break", "closed": "Closed", "holiday": "Holiday"}[self.state]


def market_status(market: Market, now: datetime | None = None, last_trade: datetime | None = None) -> Status:
    """Whether an exchange is trading now, in its own time zone.

    If it should be open but nothing has traded today 15 minutes after the open, it's a holiday.
    """
    local = (now or datetime.now(IST)).astimezone(market.zone)
    t = local.time()
    if local.weekday() >= 5 or not market.open <= t <= market.close:
        return Status("closed", local)
    if market.lunch and market.lunch[0] <= t < market.lunch[1]:
        return Status("lunch", local)
    settled = (datetime.combine(local.date(), market.open) + timedelta(minutes=15)).time()
    if last_trade is not None and t >= settled and last_trade.astimezone(market.zone).date() < local.date():
        return Status("holiday", local)
    return Status("open", local)


def hours_in_ist(market: Market, on: date | None = None) -> tuple[datetime, datetime]:
    """Opening and closing time in IST on a given day (daylight saving shifts these for the US, UK and Europe)."""
    on = on or datetime.now(market.zone).date()
    start = datetime.combine(on, market.open, market.zone).astimezone(IST)
    end = datetime.combine(on, market.close, market.zone).astimezone(IST)
    return start, end


def last_sessions(tickers: list[str], zones: dict[str, ZoneInfo]) -> dict[str, pd.Series]:
    """5-minute prices for each ticker's latest trading session, worked out in its own time zone
    (a US session crosses midnight in India, so one shared calendar day would cut it in half)."""
    data = yf.download(tickers, period="5d", interval="5m", auto_adjust=False, progress=False, threads=True)
    if data.empty:
        raise RuntimeError("Yahoo Finance returned no data. Try again in a minute.")
    close = data["Close"]
    close = close.to_frame(tickers[0]) if isinstance(close, pd.Series) else close
    out = {}
    for t in tickers:
        if t not in close:
            continue
        s = close[t].dropna()
        if s.empty:
            continue
        s.index = s.index.tz_convert(zones.get(t, IST))
        out[t] = s[s.index.date == s.index[-1].date()]
    return out


def usd_short(x: float | None) -> str:
    """$3.21T, $452.0B, $12.3M, $950,000."""
    if x is None or pd.isna(x):
        return "n/a"
    for size, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(x) >= size:
            return f"${x / size:,.2f}{unit}" if unit == "T" else f"${x / size:,.1f}{unit}"
    return f"${x:,.0f}"
