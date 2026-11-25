"""Market Dashboard: a widget board (NIFTY 50, gold, silver, breadth, top mover), the NIFTY 50 list, and news."""
from datetime import datetime

import pandas as pd
import streamlit as st

from analyser import live
from webapp import common, plots, style, widgets

REFRESH_SECONDS = 60
NEWS_REFRESH_SECONDS = 30 * 60
NIFTY50 = live.nifty50()
ALL_TICKERS = NIFTY50["ticker"].tolist() + [live.NIFTY]


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_quotes() -> pd.DataFrame:
    return live.quotes(ALL_TICKERS)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_intraday() -> pd.DataFrame:
    return live.intraday(ALL_TICKERS)


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_metals() -> pd.DataFrame:
    return live.metals("1mo")


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_market_caps() -> pd.Series:
    return live.market_caps(NIFTY50["ticker"].tolist())


@st.cache_data(ttl=NEWS_REFRESH_SECONDS, show_spinner=False)
def get_news(tickers: tuple[str, ...]) -> pd.DataFrame:
    names = dict(zip(NIFTY50["ticker"], NIFTY50["name"].map(common.short_name)))
    return live.news({**{t: names[t] for t in tickers}, live.NIFTY: "Indian market"})


style.header(
    "Live markets · India",
    "9th Street Market",
    "The NIFTY 50, gold and silver, and the latest market news, in one place. Prices from Yahoo Finance, "
    "delayed about 15 minutes. For information only, not investment advice.",
)


@st.fragment(run_every=REFRESH_SECONDS)
def live_panel() -> None:
    try:
        q, intra, m = get_quotes(), get_intraday(), get_metals()
    except Exception as err:  # noqa: BLE001
        st.markdown(f"🔴 **{live.market_status()[1]}**")
        st.warning(f"Couldn't load prices right now ({err}). Retrying in {REFRESH_SECONDS} seconds.")
        return

    last_trade = intra[live.NIFTY].dropna().index.max() if live.NIFTY in intra else None
    is_open, status = live.market_status(last_trade=last_trade)

    stocks = NIFTY50.set_index("ticker").join(q[["price", "change", "change_pct"]], how="inner")
    stocks["short"] = stocks["name"].map(common.short_name)
    top = stocks.loc[stocks["change_pct"].abs().idxmax()]

    # iPhone-style widget board: NIFTY 50, gold, silver, market breadth, top mover
    st.markdown(widgets.board(
        nifty=q.loc[live.NIFTY], nifty_intraday=intra[live.NIFTY], status=status, is_open=is_open,
        session="Live, updates every minute" if is_open else
        (f"Last session {last_trade:%a %d %b}" if last_trade is not None else "Market closed"),
        gold_now=m["gold_inr_10g"].iloc[-1], gold_prev=m["gold_inr_10g"].iloc[-2],
        silver_now=m["silver_inr_kg"].iloc[-1], silver_prev=m["silver_inr_kg"].iloc[-2],
        usd_inr=m["usd_inr"].iloc[-1], up=int((stocks["change_pct"] > 0).sum()), total=len(stocks),
        top_symbol=top["symbol"], top_name=top["short"], top_change=top["change_pct"],
    ), unsafe_allow_html=True)
    st.caption("Gold and silver are international prices converted to rupees, before Indian duty and GST.")

    st.subheader("NIFTY 50")
    orders = {"Top gainers": "gainers", "Top losers": "losers", "A–Z": "az", "By sector": "sector"}
    choice = st.segmented_control("Sort", list(orders), default="Top gainers", key="nifty_sort",
                                  label_visibility="collapsed") or "Top gainers"
    st.markdown(widgets.stock_list(stocks, intra, orders[choice]), unsafe_allow_html=True)
    st.caption("Tap a stock for its chart, key numbers and news.")

    # Charts
    t1, t2, t3 = st.tabs(["NIFTY 50 today", "Gold, 1 month", "Silver, 1 month"])
    with t1:
        st.plotly_chart(plots.intraday_line(intra[live.NIFTY], "NIFTY 50"), use_container_width=True)
    with t2:
        st.plotly_chart(plots.price_line(m["gold_inr_10g"], "Gold ₹/10 g"), use_container_width=True)
        st.caption("International (COMEX) price converted to rupees. Indian retail and MCX prices are "
                   "higher because they include import duty and GST.")
    with t3:
        st.plotly_chart(plots.price_line(m["silver_inr_kg"], "Silver ₹/kg"), use_container_width=True)
        st.caption("International (COMEX) price converted to rupees, before Indian duty and GST.")

    st.caption(f"Last updated {datetime.now(live.IST):%I:%M:%S %p} IST · refreshes every "
               f"{REFRESH_SECONDS} seconds · prices as of {q['as_of'].max():%d %b %Y}")


@st.fragment(run_every=NEWS_REFRESH_SECONDS)
def news_panel() -> None:
    st.subheader("Market news")
    try:
        caps = get_market_caps()
        biggest = tuple(caps.sort_values(ascending=False).index[:10]) if len(caps) else \
            tuple(NIFTY50["ticker"][:10])
        items = get_news(biggest)
    except Exception:  # noqa: BLE001
        st.info("News is unavailable right now. It will retry shortly.")
        return
    common.render_news(items)
    st.caption("News covers the 10 largest NIFTY 50 companies and the wider market, updated every 30 minutes.")


live_panel()
st.divider()
news_panel()
