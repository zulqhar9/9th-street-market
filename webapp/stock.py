"""Stock page: search any NSE-listed or US-listed company, then see its chart, key numbers and news."""
import pandas as pd
import streamlit as st

from analyser import live, world
from webapp import common, plots, style

EQUITIES = live.nse_equities()
US = world.us_equities()
LABELS = EQUITIES["label"].tolist() + US["label"].tolist()
NSE_BY_SYMBOL = EQUITIES.set_index("symbol")
US_BY_SYMBOL = US.set_index("symbol")
US_LABELS = set(US["label"])
NEW_YORK = world.MARKETS["US"].zone

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
def get_history(ticker: str, frame: str, us: bool) -> pd.DataFrame:
    period, interval, _ = TIMEFRAMES[frame]
    return live.history(ticker, period, interval, last_session=(frame == "1D"), tz=NEW_YORK if us else live.IST)


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_facts(ticker: str) -> dict:
    return live.stock_facts(ticker)


@st.cache_data(ttl=30 * 60, show_spinner=False)
def get_news(ticker: str, name: str) -> pd.DataFrame:
    return live.news({ticker: name}, limit=8)


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_usd_inr() -> float | None:
    try:
        return float(live.quotes([world.USD_INR]).loc[world.USD_INR, "price"])
    except Exception:  # noqa: BLE001
        return None


style.header(
    "Stock lookup",
    "Any Indian or US stock",
    f"Search all {len(EQUITIES):,} companies on India's National Stock Exchange and {len(US):,} US-listed "
    "stocks by name or ticker. Prices delayed up to 15 minutes. For information only, not investment advice.",
)

# Pre-select from the link (?symbol=RELIANCE for NSE, ?us=AAPL for the US) so pages can be shared.
wanted, wanted_us = st.query_params.get("symbol", "").upper(), st.query_params.get("us", "").upper()
if wanted_us in US_BY_SYMBOL.index:
    default = LABELS.index(US_BY_SYMBOL.loc[wanted_us, "label"])
elif wanted in NSE_BY_SYMBOL.index:
    default = LABELS.index(NSE_BY_SYMBOL.loc[wanted, "label"])
else:
    default = None

choice = st.selectbox("Search for a company", LABELS, index=default,
                      placeholder="Start typing, e.g. Infosys, TCS or Apple", label_visibility="collapsed")
if not choice:
    st.info("Pick a company above, or open one from the dashboard or World Markets page.")
    st.stop()

is_us = choice in US_LABELS
row = (US if is_us else EQUITIES).loc[lambda d: d["label"] == choice].iloc[0]
param, other = ("us", "symbol") if is_us else ("symbol", "us")
if st.query_params.get(param) != row["symbol"] or other in st.query_params:
    st.query_params.clear()
    st.query_params[param] = row["symbol"]
name, ticker = common.short_name(row["name"]), row["ticker"]
cur = "$" if is_us else "₹"


def money(x: float, decimals: int = 2) -> str:
    return f"{cur}{x:,.{decimals}f}"


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
st.caption(f"{row['exchange'] if is_us else 'NSE'}: {row['symbol']}{sector}")

change = price - prev if prev else None
cap = facts.get("market_cap")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Price", money(price),
          f"{change:+,.2f} ({change / prev:+.2%})" if change is not None else None, border=True)
if is_us:
    rate = get_usd_inr()
    m2.metric("Market value", world.usd_short(cap), border=True,
              help=f"About {live.inr_compact(cap * rate)}" if cap and rate else None)
else:
    m2.metric("Market value", live.inr_short(cap), border=True,
              help=f"{live.inr_compact(cap)} (L cr = lakh crore)")
m3.metric("P/E ratio", f"{facts['pe']:.1f}" if facts.get("pe") else "n/a", border=True,
          help="Price divided by the last 12 months' earnings per share.")
lo52, hi52 = facts.get("year_low"), facts.get("year_high")
pos52 = (price - lo52) / (hi52 - lo52) if lo52 and hi52 and hi52 > lo52 else None
m4.metric("52-week position", f"{pos52:.0%}" if pos52 is not None else "n/a",
          f"{money(lo52, 0)} – {money(hi52, 0)}" if lo52 and hi52 else None, delta_color="off",
          delta_arrow="off", border=True,
          help="Where today's price sits between the past year's low (0%) and high (100%).")
if is_us and (rate := get_usd_inr()):
    st.caption(f"One share costs about ₹{price * rate:,.0f} at US$1 = ₹{rate:.2f}, before your broker's "
               "currency conversion fee.")

c1, c2 = st.columns([3, 1])
with c1:
    frame = st.segmented_control("Timeframe", list(TIMEFRAMES), default="1Y", label_visibility="collapsed") or "1Y"
with c2:
    view = st.segmented_control("Chart type", ["Line", "Candles"], default="Line",
                                label_visibility="collapsed") or "Line"

try:
    ohlc = get_history(ticker, frame, is_us)
except Exception:  # noqa: BLE001
    st.warning("No chart data for this timeframe.")
else:
    first, last = ohlc["Close"].iloc[0], ohlc["Close"].iloc[-1]
    move = last / first - 1
    st.markdown(f"**{move:+.2%}** over {'the last session' if frame == '1D' else frame} "
                f"({'from' if frame != '1D' else 'open'} {money(first)} → {money(last)})")
    st.plotly_chart(plots.stock_chart(ohlc, candles=(view == "Candles"), intraday=TIMEFRAMES[frame][2],
                                      prefix=cur, session=(9.5, 16.0) if is_us else (9.25, 15.5)),
                    use_container_width=True, config={"displayModeBar": False})

day_lo, day_hi, vol = facts.get("day_low"), facts.get("day_high"), facts.get("volume")
bits = []
if day_lo and day_hi:
    bits.append(f"Day range {money(day_lo)} – {money(day_hi)}")
if vol:
    bits.append(f"Volume {vol:,.0f} shares")
if is_us and frame in ("1D", "1W"):
    bits.append("Times in New York time")
if bits:
    st.caption(" · ".join(bits))

st.subheader(f"News on {name}")
try:
    common.render_news(get_news(ticker, name), show_company=False)
except Exception:  # noqa: BLE001
    st.info("News is unavailable right now.")
