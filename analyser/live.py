"""Live market data for the website: NIFTY 50 stocks, any NSE stock, gold, silver and news headlines.

Source: Yahoo Finance via yfinance. Prices are delayed (NSE about 15 minutes, COMEX metals
about 10 minutes). Nothing here is cached; the website caches each call for a set time.
Stock lists come from NSE's public archives (see scripts/update_stock_lists.py).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

IST = ZoneInfo("Asia/Kolkata")
DATA = Path(__file__).resolve().parent.parent / "data"

NIFTY = "^NSEI"
GOLD, SILVER, USD_INR = "GC=F", "SI=F", "INR=X"   # COMEX gold & silver futures (US$/oz), US$ in rupees
GRAMS_PER_TROY_OUNCE = 31.1035

MARKET_OPEN, MARKET_CLOSE = time(9, 15), time(15, 30)


def _with_ticker(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ticker"] = df["symbol"] + ".NS"
    df["label"] = df["name"] + " (" + df["symbol"] + ")"
    return df


def nifty50() -> pd.DataFrame:
    """The 50 NIFTY companies: symbol, name, industry, ticker, label."""
    return _with_ticker(pd.read_csv(DATA / "nifty50.csv", dtype=str))


def nse_equities() -> pd.DataFrame:
    """Every NSE-listed equity (about 2,600): symbol, name, series, ticker, label."""
    return _with_ticker(pd.read_csv(DATA / "nse_equities.csv", dtype=str, keep_default_na=False))


def market_caps(tickers: list[str]) -> pd.Series:
    """Current market value in rupees for each ticker (missing ones are left out)."""
    def one(t: str) -> tuple[str, float | None]:
        try:
            return t, float(yf.Ticker(t).fast_info["market_cap"])
        except Exception:  # noqa: BLE001
            return t, None
    with ThreadPoolExecutor(max_workers=8) as pool:
        caps = dict(pool.map(one, tickers))
    return pd.Series({t: c for t, c in caps.items() if c}, dtype=float)


def history(ticker: str, period: str, interval: str, last_session: bool = False) -> pd.DataFrame:
    """OHLC price history for one ticker (index in IST for intraday intervals).

    last_session=True keeps only the most recent trading day, so a "today" chart still
    shows the last session on weekends and holidays.
    """
    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No price history for {ticker}.")
    if interval.endswith("m"):
        df.index = df.index.tz_convert(IST)
    if last_session:
        df = df[df.index.date == df.index[-1].date()]
    return df[["Open", "High", "Low", "Close", "Volume"]]


def stock_facts(ticker: str) -> dict:
    """Headline numbers for a stock page. Missing values come back as None."""
    t = yf.Ticker(ticker)
    fi = t.fast_info
    def get(key: str):
        try:
            v = fi[key]
            return None if v is None or pd.isna(v) else float(v)
        except Exception:  # noqa: BLE001
            return None
    facts = {
        "price": get("last_price"), "prev_close": get("previous_close"),
        "day_low": get("day_low"), "day_high": get("day_high"),
        "year_low": get("year_low"), "year_high": get("year_high"),
        "market_cap": get("market_cap"), "volume": get("last_volume"),
        "pe": None, "sector": None,
    }
    try:  # slower, richer endpoint; optional
        info = t.info or {}
        facts["pe"] = info.get("trailingPE")
        facts["sector"] = info.get("sector")
    except Exception:  # noqa: BLE001
        pass
    return facts


def screener_data(tickers: list[str]) -> pd.DataFrame:
    """Key numbers for many stocks at once (fetched in parallel): price, change, 52-week range,
    position in that range (0 = at the low, 1 = at the high), market value and P/E."""
    def one(t: str) -> dict:
        try:
            f = stock_facts(t)
        except Exception:  # noqa: BLE001
            return {"ticker": t}
        return {"ticker": t, **f}
    with ThreadPoolExecutor(max_workers=8) as pool:
        df = pd.DataFrame(list(pool.map(one, tickers))).set_index("ticker")
    df["change_pct"] = df["price"] / df["prev_close"] - 1
    span = df["year_high"] - df["year_low"]
    df["pos52"] = ((df["price"] - df["year_low"]) / span).where(span > 0).clip(0, 1)
    df["pe"] = pd.to_numeric(df["pe"], errors="coerce")
    return df


def inr_short(x: float | None) -> str:
    """Tight version for small cards: ₹18.28L cr, ₹4,520 cr, ₹95,000."""
    if x is None or pd.isna(x):
        return "n/a"
    if x >= 1e12:
        return f"₹{x / 1e12:,.2f}L cr"
    if x >= 1e7:
        return f"₹{x / 1e7:,.0f} cr"
    return f"₹{x:,.0f}"


def inr_compact(x: float | None) -> str:
    """Rupees in Indian units: ₹18.28 lakh crore, ₹4,520 crore, ₹95,000."""
    if x is None or pd.isna(x):
        return "n/a"
    if x >= 1e12:
        return f"₹{x / 1e12:,.2f} lakh crore"
    if x >= 1e7:
        return f"₹{x / 1e7:,.0f} crore"
    return f"₹{x:,.0f}"


def market_status(now: datetime | None = None, last_trade: datetime | None = None) -> tuple[bool, str]:
    """Whether the NSE is trading now.

    Clock and weekday decide normal hours. Exchange holidays fall on weekdays, so when
    `last_trade` (time of the latest intraday price) is given and nothing has traded today
    by 9:30 am, the market is treated as closed for a holiday.
    """
    now = (now or datetime.now(IST)).astimezone(IST)
    in_hours = now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE
    stamp = f"{now:%a %d %b, %I:%M %p} IST"
    if in_hours and last_trade is not None and now.time() >= time(9, 30):
        if last_trade.astimezone(IST).date() < now.date():
            return False, f"Market closed today (exchange holiday) · {stamp}"
    return in_hours, f"{'Market open' if in_hours else 'Market closed'} · {stamp}"


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
