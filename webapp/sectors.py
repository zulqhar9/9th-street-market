"""Sector view: how each part of the NIFTY 50 (banks, IT, auto, ...) is doing, today and over time."""
import pandas as pd
import streamlit as st

from analyser import live
from webapp import common, plots, style

NIFTY50 = live.nifty50()
TICKERS = NIFTY50["ticker"].tolist()
SHORT = {  # NSE's industry names, shortened for charts
    "Automobile and Auto Components": "Auto",
    "Fast Moving Consumer Goods": "FMCG",
    "Information Technology": "IT",
    "Oil Gas & Consumable Fuels": "Oil & Gas",
    "Construction Materials": "Cement",
    "Financial Services": "Financials",
    "Telecommunication": "Telecom",
}
# Period -> trading days to look back (None = today vs the previous close)
PERIODS = {"Today": 1, "1 week": 5, "1 month": 21, "3 months": 63, "1 year": None}


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_closes() -> pd.DataFrame:
    return live.adjusted_closes(TICKERS, "1y")


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_market_caps() -> pd.Series:
    return live.market_caps(TICKERS)


def period_returns(closes: pd.DataFrame, days: int | None) -> pd.Series:
    """Each stock's return over the last `days` trading days (or the whole year)."""
    closes = closes.ffill()
    start = closes.iloc[0] if days is None else closes.iloc[-1 - min(days, len(closes) - 1)]
    return closes.iloc[-1] / start - 1


style.header(
    "Explore",
    "Sectors",
    "Which parts of the market are leading and which are lagging? NIFTY 50 companies grouped into sectors, "
    "with each sector's move weighted by company size, like the index itself.",
)

frame = st.segmented_control("Period", list(PERIODS), default="Today", key="sector_period",
                             label_visibility="collapsed") or "Today"
with st.spinner("Loading sector data..."):
    try:
        closes = get_closes()
    except Exception as err:  # noqa: BLE001
        st.error(f"Couldn't load prices right now ({err}). Try again in a minute.")
        st.stop()
    try:
        caps = get_market_caps()
    except Exception:  # noqa: BLE001
        caps = pd.Series(dtype=float)

stocks = NIFTY50.set_index("ticker")
stocks["sector"] = stocks["industry"].map(lambda s: SHORT.get(s, s))
stocks["short"] = stocks["name"].map(common.short_name)
stocks["ret"] = period_returns(closes, PERIODS[frame])
stocks["weight"] = caps.reindex(stocks.index).fillna(caps.median() if len(caps) else 1.0)
stocks = stocks.dropna(subset=["ret"])


def mover(row: pd.Series) -> str:
    name = row["short"] if len(row["short"]) <= 18 else row["short"][:17].rstrip() + "…"
    return f"{name} {row['ret']:+.1%}"


def summarise(g: pd.DataFrame) -> pd.Series:
    best, worst = g.loc[g["ret"].idxmax()], g.loc[g["ret"].idxmin()]
    return pd.Series({
        "ret": (g["ret"] * g["weight"]).sum() / g["weight"].sum(),
        "count": len(g), "up": int((g["ret"] > 0).sum()),
        "best": mover(best), "worst": mover(worst) if len(g) > 1 else "–",
        "value": g["weight"].sum(),
    })


sectors = stocks.groupby("sector").apply(summarise, include_groups=False).sort_values("ret", ascending=False)
lead, lag = sectors.index[0], sectors.index[-1]
when = "today" if frame == "Today" else f"over {frame}"
st.markdown(f"### {lead} is leading {when} ({sectors.loc[lead, 'ret']:+.2%}), "
            f"{lag} is lagging ({sectors.loc[lag, 'ret']:+.2%})")

st.plotly_chart(plots.sector_bars(sectors["ret"]), use_container_width=True, config={"displayModeBar": False})

st.dataframe(
    pd.DataFrame({
        "Sector": sectors.index,
        "Change": sectors["ret"].values * 100,
        "Stocks up": [f"{u} of {c}" for u, c in zip(sectors["up"], sectors["count"])],
        "Best": sectors["best"].values,
        "Worst": sectors["worst"].values,
        "Share of NIFTY 50": (sectors["value"] / sectors["value"].sum()).values * 100,
    }),
    hide_index=True, use_container_width=True, height=36 * (len(sectors) + 1) + 4,
    column_config={
        "Change": st.column_config.NumberColumn(f"Change ({frame.lower()})", format="%+.2f%%"),
        "Share of NIFTY 50": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=40,
                                                            help="Combined company value as a share of the "
                                                                 "NIFTY 50 total"),
    },
)

pick = st.selectbox("See the stocks in a sector", list(sectors.index))
g = stocks[stocks["sector"] == pick].sort_values("ret", ascending=False)
st.dataframe(
    pd.DataFrame({
        "Company": g["short"].values,
        "Change": g["ret"].values * 100,
        "Price": closes[g.index].ffill().iloc[-1].values,
        "Details": ["stock?symbol=" + s for s in g["symbol"]],
    }),
    hide_index=True, use_container_width=True,
    column_config={
        "Change": st.column_config.NumberColumn(f"Change ({frame.lower()})", format="%+.2f%%"),
        "Price": st.column_config.NumberColumn("Price (₹)", format="₹%.2f"),
        "Details": st.column_config.LinkColumn("", display_text="Open ›", width="small"),
    },
)
st.caption("Sectors follow NSE's industry classification. Each sector's change is weighted by company value, "
           "so bigger companies count for more. Prices adjusted for dividends and splits, from Yahoo Finance, "
           "delayed about 15 minutes.")
