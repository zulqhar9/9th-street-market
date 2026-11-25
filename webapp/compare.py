"""Compare stocks: up to four Indian or US stocks (or the NIFTY 50) side by side, on one chart and one table."""
import pandas as pd
import streamlit as st

from analyser import live, metrics, world
from webapp import common, plots, style

EQUITIES = live.nse_equities()
US = world.us_equities()
NIFTY_LABEL = "NIFTY 50 (index)"
SP500_LABEL = "S&P 500 (US index)"
OPTIONS = [NIFTY_LABEL, SP500_LABEL] + EQUITIES["label"].tolist() + US["label"].tolist()
TICKER_OF = {NIFTY_LABEL: live.NIFTY, SP500_LABEL: "^GSPC",
             **dict(zip(EQUITIES["label"], EQUITIES["ticker"])), **dict(zip(US["label"], US["ticker"]))}
US_TICKERS = set(US["ticker"]) | {"^GSPC"}
INDICES = {live.NIFTY, "^GSPC"}
DEFAULTS = ["Tata Consultancy Services Limited (TCS)", "Infosys Limited (INFY)", "Accenture plc Class A (NYSE: ACN)"]
PERIODS = {"1M": "1mo", "6M": "6mo", "1Y": "1y", "3Y": "3y", "5Y": "5y"}


@st.cache_data(ttl=15 * 60, show_spinner=False)
def get_closes(tickers: tuple[str, ...], period: str) -> pd.DataFrame:
    return live.adjusted_closes(list(tickers), period)


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_facts(ticker: str) -> dict:
    return live.stock_facts(ticker)


def display_name(label: str) -> str:
    if label in (NIFTY_LABEL, SP500_LABEL):
        return label.split(" (")[0]
    return common.short_name(label.rsplit(" (", 1)[0]).removesuffix(" Class A")


def money(x: float | None, t: str) -> str:
    """₹ for Indian stocks, $ for US stocks, plain points for an index."""
    if x is None or pd.isna(x):
        return "n/a"
    cur = "" if t in INDICES else "$" if t in US_TICKERS else "₹"
    return f"{cur}{x:,.2f}"


style.header(
    "Explore",
    "Compare stocks",
    "Put up to four Indian or US stocks side by side, or check one against the NIFTY 50 or S&P 500. "
    "See how each has moved and how their key numbers stack up. For research only, not investment advice.",
)

picks = st.multiselect("Stocks to compare", OPTIONS, default=[d for d in DEFAULTS if d in OPTIONS],
                       max_selections=4, placeholder="Search for a company or symbol, Indian or US")
c1, c2 = st.columns([2, 1])
with c1:
    frame = st.segmented_control("Period", list(PERIODS), default="1Y", key="compare_period",
                                 label_visibility="collapsed") or "1Y"
has_us = any(TICKER_OF[p] in US_TICKERS for p in picks)
has_in = any(TICKER_OF[p] not in US_TICKERS for p in picks)
in_rupees = False
if has_us and has_in:
    with c2:
        in_rupees = st.toggle("US returns in rupees", value=True,
                              help="Includes the rupee's move against the dollar, which is what an Indian "
                                   "investor holding US shares actually earns.")
if len(picks) < 2:
    st.info("Pick at least two to compare.")
    st.stop()

names = {TICKER_OF[p]: display_name(p) for p in picks}
with st.spinner("Fetching prices..."):
    try:
        closes = get_closes(tuple(names) + ((world.USD_INR,) if in_rupees else ()), PERIODS[frame])
    except Exception as err:  # noqa: BLE001
        st.error(f"Couldn't load prices right now ({err}). Try again in a minute.")
        st.stop()
    facts = {t: get_facts(t) for t in names}

series = {}
for t, n in names.items():
    s = closes[t].dropna() if t in closes else pd.Series(dtype=float)
    if in_rupees and t in US_TICKERS and world.USD_INR in closes:
        fx = closes[world.USD_INR].ffill().reindex(s.index).ffill().bfill()
        s = (s * fx).dropna()
    if s.size > 1:
        series[n] = s
missing = [n for n in names.values() if n not in series]
if missing:
    st.warning(f"No price history for {', '.join(missing)} over this period.")
if not series:
    st.stop()

returns = {n: s.iloc[-1] / s.iloc[0] - 1 for n, s in series.items()}
best = max(returns, key=returns.get)
verb = "did best" if returns[best] >= 0 else "held up best"
st.markdown(f"### Over {frame}, **{best}** {verb}, {returns[best]:+.1%}")

cols = st.columns(len(series))
ticker_of_name = {n: t for t, n in names.items()}
for col, (n, r) in zip(cols, sorted(returns.items(), key=lambda kv: -kv[1])):
    t = ticker_of_name[n]
    col.metric(n, money(facts[t]["price"], t), f"{r:+.1%} over {frame}", border=True)

st.plotly_chart(plots.compare_lines(series), use_container_width=True, config={"displayModeBar": False})


def row(t: str) -> dict:
    n, f = names[t], facts[t]
    s = series.get(n)
    today = f["price"] / f["prev_close"] - 1 if f["price"] and f["prev_close"] else None
    years = (s.index[-1] - s.index[0]).days / 365.25 if s is not None else 0
    cap = f["market_cap"]
    return {
        "": n,
        "Price": money(f["price"], t),
        "Today": "n/a" if today is None else f"{today:+.2%}",
        f"Return ({frame})": "n/a" if s is None else f"{returns[n]:+.1%}",
        "Per year": f"{metrics.cagr(s):+.1%}" if s is not None and years >= 0.95 else "–",
        "Volatility": "n/a" if s is None else f"{metrics.annual_volatility(metrics.daily_returns(s)):.0%}",
        "Worst fall": "n/a" if s is None else f"{metrics.max_drawdown(s):.1%}",
        "52-week high": money(f["year_high"], t),
        "52-week low": money(f["year_low"], t),
        "P/E": "–" if t in INDICES or not f["pe"] else f"{f['pe']:.1f}",
        "Market value": "–" if t in INDICES else world.usd_short(cap) if t in US_TICKERS else live.inr_compact(cap),
    }


table = pd.DataFrame([row(t) for t in names]).set_index("").T
st.dataframe(table, use_container_width=True, height=36 * (len(table) + 1) + 4,
             column_config={"_index": st.column_config.Column(width="medium")})
notes = ["Returns use prices adjusted for dividends and splits.",
         "Volatility is how much the price swings in a typical year; worst fall is the biggest drop from a "
         "previous high in this period. Per-year return shows for periods of a year or more."]
if has_us:
    notes.append("US returns, volatility and worst fall are in rupees, including the dollar's move."
                 if in_rupees else "US returns are in dollars.")
notes.append("Prices from Yahoo Finance, delayed up to 15 minutes.")
st.caption(" ".join(notes))
