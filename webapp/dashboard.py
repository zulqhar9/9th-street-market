"""Market Dashboard: the NIFTY 50 as a heatmap and table, plus gold, silver and news, refreshing itself."""
from datetime import datetime

import pandas as pd
import streamlit as st

from analyser import live
from webapp import common, plots, style

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
    "Nain Capital Analytics",
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
    st.markdown(f"{'🟢' if is_open else '🔴'} **{status}**")

    # Headline numbers
    nifty = q.loc[live.NIFTY]
    g_now, g_prev = m["gold_inr_10g"].iloc[-1], m["gold_inr_10g"].iloc[-2]
    s_now, s_prev = m["silver_inr_kg"].iloc[-1], m["silver_inr_kg"].iloc[-2]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NIFTY 50", f"{nifty.price:,.2f}", f"{nifty.change:+,.2f} ({nifty.change_pct:+.2%})", border=True)
    c2.metric("Gold · ₹ per 10 g", f"₹{g_now:,.0f}", f"{g_now / g_prev - 1:+.2%}", border=True,
              help=f"International price US${m['gold_usd_oz'].iloc[-1]:,.1f}/oz, converted to rupees.")
    c3.metric("Silver · ₹ per kg", f"₹{s_now:,.0f}", f"{s_now / s_prev - 1:+.2%}", border=True,
              help=f"International price US${m['silver_usd_oz'].iloc[-1]:,.2f}/oz, converted to rupees.")
    c4.metric("US$ in ₹", f"₹{m['usd_inr'].iloc[-1]:.2f}",
              f"{m['usd_inr'].iloc[-1] / m['usd_inr'].iloc[-2] - 1:+.2%}", delta_color="off", border=True)

    # One table of all 50 stocks, used by both the heatmap and the list
    stocks = NIFTY50.set_index("ticker").join(q[["price", "change", "change_pct"]], how="inner")
    try:
        stocks["market_cap"] = get_market_caps()
    except Exception:  # noqa: BLE001  heatmap falls back to equal tiles
        stocks["market_cap"] = None
    if stocks["market_cap"].isna().all():
        stocks["market_cap"] = 1.0
    stocks["short"] = stocks["name"].map(common.short_name)

    up, down = int((stocks["change_pct"] > 0).sum()), int((stocks["change_pct"] < 0).sum())
    st.subheader("NIFTY 50 heatmap")
    st.caption(f"Tile size is company value, colour is today's move. {up} up · {down} down. "
               "Hover a tile for the full name.")
    st.plotly_chart(plots.heatmap(stocks.reset_index()), use_container_width=True,
                    config={"displayModeBar": False})

    st.subheader("NIFTY 50 stocks")
    st.caption("Click a column to sort. Open a stock for its chart, key numbers and news.")
    table = pd.DataFrame({
        "Company": stocks["short"].values,
        "Sector": stocks["industry"].values,
        "Price (₹)": stocks["price"].values,
        "Change (₹)": stocks["change"].values,
        "Change": stocks["change_pct"].values * 100,
        "Today": [intra[t].dropna().tolist() if t in intra else [] for t in stocks.index],
        "Details": ["stock?symbol=" + s for s in stocks["symbol"]],
    }).sort_values("Change", ascending=False)
    styled = table.style.map(lambda v: f"color: {plots.GAIN if v >= 0 else plots.LOSS}",
                             subset=["Change (₹)", "Change"])
    st.dataframe(styled, hide_index=True, use_container_width=True, height=36 * 13,
                 column_config={
                     "Price (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                     "Change (₹)": st.column_config.NumberColumn(format="%+.2f"),
                     "Change": st.column_config.NumberColumn(format="%+.2f%%"),
                     "Today": st.column_config.LineChartColumn("Today (5-min)", width="small"),
                     "Details": st.column_config.LinkColumn("", display_text="Open ›", width="small"),
                 })

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
