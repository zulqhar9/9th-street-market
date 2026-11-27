"""Crypto: the biggest coins in rupees or dollars, 24-hour moves, charts, and India's crypto tax in brief."""
import pandas as pd
import streamlit as st

from analyser import crypto, live
from analyser.world import USD_INR
from webapp import plots, style, widgets

REFRESH_SECONDS = 60
# Timeframe -> (Yahoo period, interval, intraday?)
TIMEFRAMES = {"1D": ("2d", "15m", True), "1W": ("7d", "1h", True), "1M": ("1mo", "1d", False),
              "1Y": ("1y", "1d", False), "5Y": ("5y", "1wk", False)}


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_snapshot():
    return crypto.snapshot()


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_chart(ticker: str, frame: str, rupees: bool) -> pd.DataFrame:
    period, interval, _ = TIMEFRAMES[frame]
    ohlc = live.history(ticker, period, interval)
    if frame == "1D":
        ohlc = ohlc.loc[ohlc.index[-1] - pd.Timedelta(hours=24):]
    if rupees:  # convert at each day's exchange rate, not today's
        fx = live.history(USD_INR, "5y" if frame == "5Y" else period, "1d" if not TIMEFRAMES[frame][2] else interval)
        rate = fx["Close"]
        rate.index = rate.index.tz_convert(ohlc.index.tz) if rate.index.tz is not None else rate.index
        rate = rate.reindex(rate.index.union(ohlc.index)).ffill().bfill().reindex(ohlc.index)
        ohlc = ohlc.copy()
        for col in ["Open", "High", "Low", "Close"]:
            ohlc[col] = ohlc[col] * rate
    return ohlc


def money(x: float, cur: str) -> str:
    d = crypto.decimals_for(x)
    return f"₹{widgets.indian(x, d)}" if cur == "₹" else f"${x:,.{d}f}"


style.header(
    "Live markets · Crypto",
    "Crypto",
    "The biggest cryptocurrencies, priced in rupees or dollars. Crypto trades 24 hours a day, so changes "
    "here are over the last 24 hours. Prices from Yahoo Finance. Crypto is very volatile and lightly "
    "regulated in India; nothing here is investment advice.",
)

cur = st.segmented_control("Currency", ["₹", "$"], default="₹", key="crypto_currency",
                           label_visibility="collapsed") or "₹"


@st.fragment(run_every=REFRESH_SECONDS)
def board() -> None:
    try:
        coins, lines, rate = get_snapshot()
    except Exception as err:  # noqa: BLE001
        st.warning(f"Couldn't load crypto prices right now ({err}). Retrying in {REFRESH_SECONDS} seconds.")
        return
    use_inr = cur == "₹" and rate is not None
    tiles = []
    for t, r in coins.iterrows():
        price = r["price"] * rate if use_inr else r["price"]
        tiles.append({"name": f"{r['name']} · {r['symbol']}", "price": price, "change": r["change_pct"],
                      "change_pct": r["change_pct"], "state": "open", "label": "24/7",
                      "price_text": money(price, "₹" if use_inr else "$"), "change_text": "24h · ",
                      "session": lines.get(t), "foot": "Last 24 hours"})
    st.markdown(widgets.index_board(tiles), unsafe_allow_html=True)
    if rate:
        st.caption(f"US$1 = ₹{rate:.2f}. Rupee prices are global prices converted at this rate; Indian exchanges "
                   f"may show slightly different prices. Updated {pd.Timestamp.now(tz=live.IST):%I:%M %p} IST.")


board()

st.subheader("Chart")
names = {t: f"{n} ({s})" for t, (n, s) in crypto.COINS.items()}
c1, c2, c3 = st.columns([2, 2, 1])
coin = c1.selectbox("Coin", list(names), format_func=names.get, label_visibility="collapsed")
with c2:
    frame = st.segmented_control("Timeframe", list(TIMEFRAMES), default="1M", key="crypto_frame",
                                 label_visibility="collapsed") or "1M"
with c3:
    view = st.segmented_control("Chart type", ["Line", "Candles"], default="Line", key="crypto_view",
                                label_visibility="collapsed") or "Line"
try:
    ohlc = get_chart(coin, frame, cur == "₹")
except Exception:  # noqa: BLE001
    st.warning("No chart data for this coin and timeframe right now.")
else:
    first, last = ohlc["Close"].iloc[0], ohlc["Close"].iloc[-1]
    st.markdown(f"**{last / first - 1:+.2%}** over {'the last 24 hours' if frame == '1D' else frame} "
                f"({money(first, cur)} → {money(last, cur)})")
    st.plotly_chart(plots.stock_chart(ohlc, candles=(view == "Candles"), intraday=TIMEFRAMES[frame][2],
                                      prefix=cur, session=None, decimals=crypto.decimals_for(last)),
                    use_container_width=True, config={"displayModeBar": False})

with st.expander("How crypto is taxed in India", icon=":material/receipt_long:"):
    st.markdown(
        "- **30% flat tax** on any profit, plus 4% cess, no matter how long you held or what you earn.\n"
        "- **No set-off for losses:** a loss on one coin can't reduce the tax on a gain from another, or on "
        "any other income, and it can't be carried forward.\n"
        "- **1% TDS** is deducted when you sell above a small yearly threshold, and counts towards your tax.\n"
        "- Only the cost of buying the coin can be deducted, not fees or other expenses.\n\n"
        "Budget 2026 left these rules unchanged. Check with a tax professional for your own situation.")
