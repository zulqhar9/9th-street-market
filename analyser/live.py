"""Live market data for the dashboard: NSE top 10, NIFTY 50, gold, silver and news headlines.

Source: Yahoo Finance via yfinance. Prices are delayed (NSE about 15 minutes, COMEX metals
about 10 minutes). Nothing here is cached; the website caches each call for a set time.
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

IST = ZoneInfo("Asia/Kolkata")

# The 10 largest NSE-listed companies by market value (Nov 2026), largest first.
TOP10 = {
    "RELIANCE.NS": "Reliance Industries",
    "BHARTIARTL.NS": "Bharti Airtel",
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "SBIN.NS": "State Bank of India",
    "TCS.NS": "Tata Consultancy Services",
    "BAJFINANCE.NS": "Bajaj Finance",
    "LT.NS": "Larsen & Toubro",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "HINDUNILVR.NS": "Hindustan Unilever",
}
NIFTY = "^NSEI"
GOLD, SILVER, USD_INR = "GC=F", "SI=F", "INR=X"   # COMEX gold & silver futures (US$/oz), US$ in rupees
GRAMS_PER_TROY_OUNCE = 31.1035

MARKET_OPEN, MARKET_CLOSE = time(9, 15), time(15, 30)


def market_status(now: datetime | None = None) -> tuple[bool, str]:
    """Whether the NSE is in normal trading hours (weekends counted, exchange holidays not)."""
    now = (now or datetime.now(IST)).astimezone(IST)
    is_open = now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE
    label = "Market open" if is_open else "Market closed"
    return is_open, f"{label} · {now:%a %d %b, %I:%M %p} IST"


def _closes(tickers: list[str], **kwargs) -> pd.DataFrame:
    data = yf.download(tickers, auto_adjust=False, progress=False, threads=True, **kwargs)
    if data.empty:
        raise RuntimeError("Yahoo Finance returned no data. Try again in a minute.")
    close = data["Close"]
    return close.to_frame(tickers[0]) if isinstance(close, pd.Series) else close


def quotes(tickers: list[str]) -> pd.DataFrame:
    """Latest price and change vs the previous close, one row per ticker."""
    close = _closes(tickers, period="7d", interval="1d")
    rows = []
    for t in tickers:
        s = close[t].dropna() if t in close else pd.Series(dtype=float)
        if len(s) < 2:
            continue
        price, prev = float(s.iloc[-1]), float(s.iloc[-2])
        rows.append({"ticker": t, "price": price, "prev_close": prev, "change": price - prev,
                     "change_pct": price / prev - 1, "as_of": s.index[-1].date()})
    return pd.DataFrame(rows).set_index("ticker")


def intraday(tickers: list[str]) -> pd.DataFrame:
    """5-minute prices for the latest trading session (today when the market is open)."""
    close = _closes(tickers, period="5d", interval="5m")
    close.index = close.index.tz_convert(IST)
    last_day = close.dropna(how="all").index[-1].date()
    return close[close.index.date == last_day]


def metals(period: str = "1mo") -> pd.DataFrame:
    """Daily gold and silver prices in US$/oz, plus rupee prices (₹ per 10 g gold, ₹ per kg silver).

    These are international (COMEX) prices converted at the market exchange rate. Indian retail
    and MCX prices are higher because they include import duty and GST.
    """
    close = _closes([GOLD, SILVER, USD_INR], period=period, interval="1d").ffill().dropna()
    per_gram = close[USD_INR] / GRAMS_PER_TROY_OUNCE
    return pd.DataFrame({
        "gold_usd_oz": close[GOLD],
        "silver_usd_oz": close[SILVER],
        "usd_inr": close[USD_INR],
        "gold_inr_10g": close[GOLD] * per_gram * 10,
        "silver_inr_kg": close[SILVER] * per_gram * 1000,
    })


def _parse_news(item: dict, company: str) -> dict | None:
    c = item.get("content", item)  # newer yfinance nests the story under "content"
    title = c.get("title")
    url = ((c.get("clickThroughUrl") or {}).get("url")
           or (c.get("canonicalUrl") or {}).get("url") or c.get("link"))
    when = c.get("pubDate") or c.get("providerPublishTime")
    if not (title and url and when):
        return None
    published = (pd.to_datetime(when, unit="s", utc=True) if isinstance(when, (int, float))
                 else pd.to_datetime(when, utc=True))
    source = (c.get("provider") or {}).get("displayName") or c.get("publisher") or "Yahoo Finance"
    return {"title": title.strip(), "url": url, "source": source, "company": company,
            "published": published}


def news(tickers: dict[str, str], limit: int = 25) -> pd.DataFrame:
    """Latest headlines for the given tickers, newest first, duplicates removed."""
    stories = []
    for ticker, company in tickers.items():
        try:
            items = yf.Ticker(ticker).news or []
        except Exception:  # one failing ticker shouldn't empty the whole feed  # noqa: BLE001
            continue
        stories += [s for s in (_parse_news(i, company) for i in items) if s]
    if not stories:
        return pd.DataFrame(columns=["title", "url", "source", "company", "published"])
    df = pd.DataFrame(stories).sort_values("published", ascending=False)
    return df.drop_duplicates("title").head(limit).reset_index(drop=True)
