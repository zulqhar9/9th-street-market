"""Compare stocks: up to four NSE stocks (or the NIFTY 50) side by side, on one chart and one table."""
import pandas as pd
import streamlit as st

from analyser import live, metrics
from webapp import common, plots, style

EQUITIES = live.nse_equities()
NIFTY_LABEL = "NIFTY 50 (index)"
OPTIONS = [NIFTY_LABEL] + EQUITIES["label"].tolist()
TICKER_OF = {NIFTY_LABEL: live.NIFTY, **dict(zip(EQUITIES["label"], EQUITIES["ticker"]))}
DEFAULTS = ["Reliance Industries Limited (RELIANCE)", "Tata Consultancy Services Limited (TCS)",
            "HDFC Bank Limited (HDFCBANK)"]
PERIODS = {"1M": "1mo", "6M": "6mo", "1Y": "1y", "3Y": "3y", "5Y": "5y"}


@st.cache_data(ttl=15 * 60, show_spinner=False)
def get_closes(tickers: tuple[str, ...], period: str) -> pd.DataFrame:
    return live.adjusted_closes(list(tickers), period)


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_facts(ticker: str) -> dict:
    return live.stock_facts(ticker)


def display_name(label: str) -> str:
    return "NIFTY 50" if label == NIFTY_LABEL else common.short_name(label.rsplit(" (", 1)[0])


def money(x: float | None, rupees: bool = True) -> str:
    """₹ amount for stocks; plain points for the index."""
    if x is None or pd.isna(x):
        return "n/a"
    return f"₹{x:,.2f}" if rupees else f"{x:,.2f}"


style.header(
    "Explore",
    "Compare stocks",
    "Put up to four NSE stocks side by side, or check one against the NIFTY 50. See how each has moved "
    "and how their key numbers stack up. For research only, not investment advice.",
)

picks = st.multiselect("Stocks to compare", OPTIONS, default=[d for d in DEFAULTS if d in OPTIONS],
                       max_selections=4, placeholder="Search for a company or symbol")
frame = st.segmented_control("Period", list(PERIODS), default="1Y", key="compare_period",
                             label_visibility="collapsed") or "1Y"
if len(picks) < 2:
    st.info("Pick at least two to compare.")
    st.stop()

names = {TICKER_OF[p]: display_name(p) for p in picks}
with st.spinner("Fetching prices..."):
    try:
        closes = get_closes(tuple(names), PERIODS[frame])
    except Exception as err:  # noqa: BLE001
        st.error(f"Couldn't load prices right now ({err}). Try again in a minute.")
        st.stop()
    facts = {t: get_facts(t) for t in names}

series = {names[t]: closes[t].dropna() for t in names if t in closes and closes[t].dropna().size > 1}
missing = [names[t] for t in names if names[t] not in series]
if missing:
    st.warning(f"No price history for {', '.join(missing)} over this period.")
if not series:
    st.stop()

returns = {n: s.iloc[-1] / s.iloc[0] - 1 for n, s in series.items()}
best = max(returns, key=returns.get)
verb = "did best" if returns[best] >= 0 else "held up best"
st.markdown(f"### Over {frame}, **{best}** {verb}, {returns[best]:+.1%}")

cols = st.columns(len(series))
for col, (n, r) in zip(cols, sorted(returns.items(), key=lambda kv: -kv[1])):
    t = next(t for t, name in names.items() if name == n)
    price = facts[t]["price"] or float(series[n].iloc[-1])
    col.metric(n, money(price, t != live.NIFTY), f"{r:+.1%} over {frame}", border=True)

st.plotly_chart(plots.compare_lines(series), use_container_width=True, config={"displayModeBar": False})


def row(t: str) -> dict:
    n, f = names[t], facts[t]
    s = series.get(n)
    today = f["price"] / f["prev_close"] - 1 if f["price"] and f["prev_close"] else None
    years = (s.index[-1] - s.index[0]).days / 365.25 if s is not None else 0
    is_index = t == live.NIFTY
    return {
        "": n,
        "Price": money(f["price"], not is_index),
        "Today": "n/a" if today is None else f"{today:+.2%}",
        f"Return ({frame})": "n/a" if s is None else f"{returns[n]:+.1%}",
        "Per year": f"{metrics.cagr(s):+.1%}" if s is not None and years >= 0.95 else "–",
        "Volatility": "n/a" if s is None else f"{metrics.annual_volatility(metrics.daily_returns(s)):.0%}",
        "Worst fall": "n/a" if s is None else f"{metrics.max_drawdown(s):.1%}",
        "52-week high": money(f["year_high"], not is_index),
        "52-week low": money(f["year_low"], not is_index),
        "P/E": "–" if is_index or not f["pe"] else f"{f['pe']:.1f}",
        "Market value": "–" if is_index else live.inr_compact(f["market_cap"]),
    }


table = pd.DataFrame([row(t) for t in names]).set_index("").T
st.dataframe(table, use_container_width=True, height=36 * (len(table) + 1) + 4,
             column_config={"_index": st.column_config.Column(width="medium")})
st.caption("Returns use prices adjusted for dividends and splits. Volatility is how much the price swings "
           "in a typical year; worst fall is the biggest drop from a previous high in this period. "
           "Per-year return shows for periods of a year or more. Prices from Yahoo Finance, delayed about "
           "15 minutes.")
