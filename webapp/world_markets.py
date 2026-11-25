"""World Markets: global indices, the biggest US stocks (in $ or ₹) and trading hours in Indian time."""
from datetime import datetime

import pandas as pd
import streamlit as st

from analyser import live, world
from webapp import style, widgets

REFRESH_SECONDS = 60
INDEX_TICKERS = [i.ticker for i in world.INDICES]
US_TICKERS = list(world.US_TOP)
ZONES = {**{i.ticker: world.MARKETS[i.market].zone for i in world.INDICES},
         **{t: world.MARKETS["US"].zone for t in US_TICKERS}}


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_quotes() -> pd.DataFrame:
    return live.quotes(INDEX_TICKERS + US_TICKERS + [world.USD_INR])


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_sessions() -> dict:
    return world.last_sessions(INDEX_TICKERS + US_TICKERS, ZONES)


style.header(
    "Live markets · World",
    "World markets",
    "The world's major stock markets and the biggest US companies, with prices in dollars or rupees and "
    "trading hours in Indian time. Prices from Yahoo Finance, delayed up to 20 minutes. "
    "For information only, not investment advice.",
)


@st.fragment(run_every=REFRESH_SECONDS)
def panel() -> None:
    try:
        q, sessions = get_quotes(), get_sessions()
    except Exception as err:  # noqa: BLE001
        st.warning(f"Couldn't load world prices right now ({err}). Retrying in {REFRESH_SECONDS} seconds.")
        return

    now = datetime.now(live.IST)
    statuses = {}
    tiles = []
    for idx in world.INDICES:
        if idx.ticker not in q.index:
            continue
        market = world.MARKETS[idx.market]
        session = sessions.get(idx.ticker)
        last = session.index[-1].to_pydatetime() if session is not None and len(session) else None
        status = world.market_status(market, now, last)
        statuses.setdefault(market.key, status)
        r = q.loc[idx.ticker]
        tiles.append({"name": idx.name, "price": r["price"], "change": r["change"], "change_pct": r["change_pct"],
                      "state": status.state, "label": status.label, "session": session,
                      "foot": f"{market.country} · {status.local:%I:%M %p} there".replace(" 0", " ")})
    st.markdown(widgets.index_board(tiles), unsafe_allow_html=True)

    st.subheader("Biggest US stocks")
    rate = float(q.loc[world.USD_INR, "price"]) if world.USD_INR in q.index else None
    c1, c2 = st.columns([3, 1])
    orders = {"Top gainers": "gainers", "Top losers": "losers", "A–Z": "az"}
    with c1:
        choice = st.segmented_control("Sort", list(orders), default="Top gainers", key="us_sort",
                                      label_visibility="collapsed") or "Top gainers"
    with c2:
        cur = st.segmented_control("Currency", ["$", "₹"], default="$", key="us_currency",
                                   label_visibility="collapsed") or "$"
    us = q.loc[[t for t in US_TICKERS if t in q.index], ["price", "change_pct"]].copy()
    us["symbol"], us["short"], us["industry"] = us.index, [world.US_TOP[t] for t in us.index], ""
    if cur == "₹" and rate:
        us["price"] = us["price"] * rate
    st.markdown(widgets.stock_list(us, sessions, orders[choice], currency=cur if rate else "$", link="stock?us="),
                unsafe_allow_html=True)
    if rate:
        st.caption(f"US$1 = ₹{rate:.2f}. Daily changes are in dollars. Tap a stock for its chart and news, "
                   "or search any US stock on the Stock Lookup page.")

    st.subheader("Trading hours in Indian time")
    rows = []
    for m in world.MARKETS.values():
        start, end = world.hours_in_ist(m)
        s = statuses.get(m.key) or world.market_status(m, now)
        lunch = f" (lunch {m.lunch[0]:%H:%M}–{m.lunch[1]:%H:%M} local)" if m.lunch else ""
        next_day = " next day" if end.date() > start.date() else ""
        rows.append({"Market": f"{m.country} · {m.exchange}",
                     "Opens (IST)": start.strftime("%I:%M %p").lstrip("0"),
                     "Closes (IST)": end.strftime("%I:%M %p").lstrip("0") + next_day + lunch,
                     "Now": s.label})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=36 * (len(rows) + 1) + 4)
    st.caption(f"Times shift by an hour when the US, UK and Europe change their clocks for daylight saving. "
               f"Updated {now:%I:%M:%S %p} IST, refreshes every minute.")


panel()
