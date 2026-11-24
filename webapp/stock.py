"""Stock page: search any NSE-listed company, then see its chart, key numbers and news."""
import pandas as pd
import streamlit as st

from analyser import live
from webapp import common, plots, style

EQUITIES = live.nse_equities()
LABELS = EQUITIES["label"].tolist()
BY_SYMBOL = EQUITIES.set_index("symbol")

# Timeframe -> (Yahoo period, interval, intraday?)
TIMEFRAMES = {
    "1D": ("5d", "5m", True),
    "1W": ("5d", "30m", True),
    "1M": ("1mo", "1d", False),
    "6M": ("6mo", "1d", False),
    "1Y": ("1y", "1d", False),
    "5Y": ("5y", "1wk", False),
}


@st.cache_data(ttl=60, show_spinner=False)
def get_history(ticker: str, frame: str) -> pd.DataFrame:
    period, interval, _ = TIMEFRAMES[frame]
    return live.history(ticker, period, interval, last_session=(frame == "1D"))


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_facts(ticker: str) -> dict:
    return live.stock_facts(ticker)


@st.cache_data(ttl=30 * 60, show_spinner=False)
def get_news(ticker: str, name: str) -> pd.DataFrame:
    return live.news({ticker: name}, limit=8)


style.header(
    "Stock lookup",
    "Any NSE stock",
    f"Search all {len(EQUITIES):,} companies listed on the National Stock Exchange by name or ticker. "
    "Prices delayed about 15 minutes. For information only, not investment advice.",
)

# Pre-select from the link (?symbol=RELIANCE) so pages can be shared and opened from the dashboard.
wanted = st.query_params.get("symbol", "").upper()
default = LABELS.index(BY_SYMBOL.loc[wanted, "label"]) if wanted in BY_SYMBOL.index else None

choice = st.selectbox("Search for a company", LABELS, index=default, placeholder="Start typing, e.g. Infosys or TCS",
                      label_visibility="collapsed")
if not choice:
    st.info("Pick a company above, or open one from the NIFTY 50 table on the dashboard.")
    st.stop()

row = EQUITIES.loc[EQUITIES["label"] == choice].iloc[0]
if st.query_params.get("symbol") != row["symbol"]:
    st.query_params["symbol"] = row["symbol"]
name, ticker = common.short_name(row["name"]), row["ticker"]

try:
    facts = get_facts(ticker)
except Exception:  # noqa: BLE001
    facts = {}
price, prev = facts.get("price"), facts.get("prev_close")
if price is None:
    st.error(f"No live price for {name} ({row['symbol']}) right now. It may be suspended, "
             "recently renamed, or listed only on a special segment.")
    st.stop()

st.subheader(name)
sector = f" · {facts['sector']}" if facts.get("sector") else ""
st.caption(f"NSE: {row['symbol']}{sector}")

change = price - prev if prev else None
m1, m2, m3, m4 = st.columns(4)
m1.metric("Price", f"₹{price:,.2f}",
          f"{change:+,.2f} ({change / prev:+.2%})" if change is not None else None, border=True)
m2.metric("Market value", live.inr_short(facts.get("market_cap")), border=True,
          help=f"{live.inr_compact(facts.get('market_cap'))} (L cr = lakh crore)")
m3.metric("P/E ratio", f"{facts['pe']:.1f}" if facts.get("pe") else "n/a", border=True,
          help="Price divided by the last 12 months' earnings per share.")
lo52, hi52 = facts.get("year_low"), facts.get("year_high")
pos52 = (price - lo52) / (hi52 - lo52) if lo52 and hi52 and hi52 > lo52 else None
m4.metric("52-week position", f"{pos52:.0%}" if pos52 is not None else "n/a",
          f"₹{lo52:,.0f} – ₹{hi52:,.0f}" if lo52 and hi52 else None, delta_color="off", delta_arrow="off",
          border=True, help="Where today's price sits between the past year's low (0%) and high (100%).")

c1, c2 = st.columns([3, 1])
with c1:
    frame = st.segmented_control("Timeframe", list(TIMEFRAMES), default="1Y", label_visibility="collapsed") or "1Y"
with c2:
    view = st.segmented_control("Chart type", ["Line", "Candles"], default="Line",
                                label_visibility="collapsed") or "Line"

try:
    ohlc = get_history(ticker, frame)
except Exception:  # noqa: BLE001
    st.warning("No chart data for this timeframe.")
else:
    first, last = ohlc["Close"].iloc[0], ohlc["Close"].iloc[-1]
    move = last / first - 1
    st.markdown(f"**{move:+.2%}** over {'the last session' if frame == '1D' else frame} "
                f"({'from' if frame != '1D' else 'open'} ₹{first:,.2f} → ₹{last:,.2f})")
    st.plotly_chart(plots.stock_chart(ohlc, candles=(view == "Candles"), intraday=TIMEFRAMES[frame][2]),
                    use_container_width=True, config={"displayModeBar": False})

day_lo, day_hi, vol = facts.get("day_low"), facts.get("day_high"), facts.get("volume")
bits = []
if day_lo and day_hi:
    bits.append(f"Day range ₹{day_lo:,.2f} – ₹{day_hi:,.2f}")
if vol:
    bits.append(f"Volume {vol:,.0f} shares")
if bits:
    st.caption(" · ".join(bits))

st.subheader(f"News on {name}")
try:
    common.render_news(get_news(ticker, name), show_company=False)
except Exception:  # noqa: BLE001
    st.info("News is unavailable right now.")
