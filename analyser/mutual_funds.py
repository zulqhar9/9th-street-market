"""Indian mutual funds: the fund list (from AMFI), NAV history, trailing returns and SIP backtests.

The fund list comes from AMFI's daily NAV file (see scripts/update_stock_lists.py) and is filtered
to open-ended funds' growth options. NAV history comes from mfapi.in, a free public API that
republishes AMFI's NAV records.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from analyser.live import DATA

HISTORY_URL = "https://api.mfapi.in/mf/{code}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; 9th-street-market/1.0)"}

GROUP_RULES = [  # first match wins, checked against the part of AMFI's heading before " - "
    ("Index Funds", "Index funds & ETFs"), ("ETF", "Index funds & ETFs"),
    ("Equity", "Equity"), ("Hybrid", "Hybrid"),
    ("Debt", "Debt"), ("Income", "Debt"), ("Gilt", "Debt"),
    ("Solution Oriented", "Retirement & children's"), ("Life Cycle", "Retirement & children's"),
    ("Children", "Retirement & children's"),
    ("Fund of Funds", "Fund of funds"), ("FoF", "Fund of funds"),
]
CATEGORY_ALIASES = {
    "ELSS": "ELSS (tax saver)", "ELSS- Tax Saver": "ELSS (tax saver)",
    "Sectoral/ Thematic": "Sectoral & thematic", "Sectoral": "Sectoral & thematic", "Thematic": "Sectoral & thematic",
    "Balanced Advantage Fund/ Dynamic Asset Allocation": "Balanced advantage",
    "Dynamic Asset Allocation or Balanced Advantage": "Balanced advantage",
    "Banking and PSU Debt": "Banking and PSU", "Equity Savings": "Equity savings",
    "Multi Asset Allocation": "Multi asset allocation", "Index": "Equity",
}
# Shown first when nothing is picked yet: an active flexi-cap fund and a NIFTY 50 index fund.
DEFAULT_FUNDS = ["Parag Parikh Flexi Cap", "UTI Nifty 50 Index"]


def _group_and_category(heading: str) -> tuple[str, str]:
    """'Open Ended Schemes(Equity Schemes - Large Cap Fund)' -> ('Equity', 'Large Cap')."""
    inner = re.sub(r"^[^(]*\((.*)\)\s*$", r"\1", heading.strip())
    kind, _, cat = inner.partition(" - ")
    # Prefer the scheme type ("Equity Schemes"); fall back to the whole heading ("Other Scheme - Index Funds").
    group = next((g for key, g in GROUP_RULES if key.lower() in kind.lower()), None)
    group = group or next((g for key, g in GROUP_RULES if key.lower() in inner.lower()), "Other")
    cat = re.sub(r"\s+", " ", (cat or kind)).strip()
    cat = re.sub(r"\s+Funds?$", "", cat).strip()
    return group, CATEGORY_ALIASES.get(cat, cat)


def parse_navall(text: str, as_of: date | None = None, max_age_days: int = 30) -> pd.DataFrame:
    """Open-ended growth-option funds from AMFI's NAVAll.txt: code, name, amc, group, category, plan, nav, date.

    Funds whose last NAV is older than `max_age_days` (wound up or merged) are left out.
    """
    rows, heading, amc = [], "", ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            if "Schemes(" in line or "Scheme(" in line:
                heading = line
            else:
                amc = line
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 8 or not heading.startswith("Open Ended"):
            continue
        code, name, plan, option, nav, nav_date = parts[0], parts[3], parts[4], parts[5], parts[6], parts[7]
        # Growth options only. "Dividend Yield" is a fund type, so match payout options, not the word alone.
        if "growth" not in f"{name} {option}".lower() or re.search(r"idcw|dividend|bonus", option.lower()) \
                or re.search(r"idcw|dividend (option|plan|payout|reinvest)|bonus", name.lower()):
            continue
        try:
            value, when = float(nav), datetime.strptime(nav_date, "%d-%b-%Y").date()
        except ValueError:
            continue
        group, category = _group_and_category(heading)
        plan = "Direct" if "direct" in f"{plan} {name}".lower() else "Regular"
        rows.append((int(code), name, amc, group, category, plan, value, when))
    df = pd.DataFrame(rows, columns=["code", "name", "amc", "group", "category", "plan", "nav", "date"])
    if df.empty:
        return df
    latest = as_of or df["date"].max()
    return df[pd.to_datetime(df["date"]) >= pd.Timestamp(latest) - pd.Timedelta(days=max_age_days)]


def funds() -> pd.DataFrame:
    """The stored fund list, with a unique display label for each fund."""
    df = pd.read_csv(DATA / "mutual_funds.csv", dtype={"name": str, "amc": str})
    df["label"] = df["name"].str.replace(r"\s*-\s*(Direct|Regular)\s*Plan.*$", "", regex=True, case=False)
    dupes = df.duplicated(["label", "plan"], keep=False)
    df.loc[dupes, "label"] = df.loc[dupes, "name"] + " (" + df.loc[dupes, "code"].astype(str) + ")"
    return df


def nav_history(code: int) -> pd.Series:
    """Daily NAV for one fund, oldest first."""
    url = HISTORY_URL.format(code=int(code))
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20) as resp:
        payload = json.load(resp)
    data = payload.get("data") or []
    if not data:
        raise RuntimeError(f"No NAV history for fund {code}.")
    s = pd.Series({pd.to_datetime(d["date"], format="%d-%m-%Y"): float(d["nav"]) for d in data}, name="nav")
    s = s[s > 0].sort_index()
    return s[~s.index.duplicated()]


def trailing_return(nav: pd.Series, years: float) -> float | None:
    """Return over the last `years` (annualised when a year or more), or None if the fund is younger."""
    nav = nav.dropna()
    start = nav.index[-1] - pd.DateOffset(months=round(years * 12))
    if nav.index[0] > start:
        return None
    past = nav.loc[:start].iloc[-1]
    growth = nav.iloc[-1] / past
    return growth ** (1 / years) - 1 if years >= 1 else growth - 1


def xirr(flows: list[tuple[pd.Timestamp, float]]) -> float:
    """Annual rate that makes the cash flows' present value zero (money out negative, money in positive)."""
    t0 = flows[0][0]
    times = [((d - t0).days / 365.25, amt) for d, amt in flows]

    def npv(rate: float) -> float:
        return sum(amt / (1 + rate) ** t for t, amt in times)

    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


@dataclass
class SipResult:
    invested: float
    value: float
    xirr: float
    instalments: int
    start: pd.Timestamp

    @property
    def gain(self) -> float:
        return self.value - self.invested


def sip_backtest(nav: pd.Series, monthly: float, years: int) -> SipResult | None:
    """Invest `monthly` on the first NAV date of each month for the last `years`; value it at today's NAV."""
    nav = nav.dropna()
    end = nav.index[-1]
    start = end - pd.DateOffset(years=years)
    if nav.index[0] > start:
        return None
    units, flows = 0.0, []
    for month_start in pd.date_range(start, end, freq="MS"):
        on = nav.loc[month_start:]
        if on.empty or on.index[0] > end:
            break
        units += monthly / on.iloc[0]
        flows.append((on.index[0], -monthly))
    if not flows:
        return None
    value = units * nav.iloc[-1]
    rate = xirr(flows + [(end, value)])
    return SipResult(invested=monthly * len(flows), value=value, xirr=rate, instalments=len(flows),
                     start=flows[0][0])
