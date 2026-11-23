"""Market Dashboard: India's top 10 stocks, NIFTY 50, gold, silver and news, refreshing itself."""
from datetime import datetime

import pandas as pd
import streamlit as st

from analyser import live
from webapp import plots

REFRESH_SECONDS = 60
NEWS_REFRESH_SECONDS = 30 * 60
ALL_TICKERS = list(live.TOP10) + [live.NIFTY]


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_quotes() -> pd.DataFrame:
    return live.quotes(ALL_TICKERS)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def get_intraday() -> pd.DataFrame:
    return live.intraday(ALL_TICKERS)


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_metals() -> pd.DataFrame:
    return live.metals("1mo")


@st.cache_data(ttl=NEWS_REFRESH_SECONDS, show_spinner=False)
def get_news() -> pd.DataFrame:
    return live.news({**live.TOP10, live.NIFTY: "Indian market"})


def time_ago(ts: pd.Timestamp) -> str:
    minutes = int((pd.Timestamp.now(tz="UTC") - ts).total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 1)} min ago"
    if minutes < 48 * 60:
        return f"{minutes // 60} h ago"
    return ts.tz_convert(live.IST).strftime("%d %b")


st.title("Nain Capital Analytics")
st.caption("A live view of India's 10 largest listed companies, gold and silver, with the latest market news. "
           "Prices from Yahoo Finance, delayed about 15 minutes. For information only, not investment advice.")


@st.fragment(run_every=REFRESH_SECONDS)
def live_panel() -> None:
    is_open, status = live.market_status()
    st.markdown(f"{'🟢' if is_open else '🔴'} **{status}**")

    try:
        q, intra, m = get_quotes(), get_intraday(), get_metals()
    except Exception as err:  # noqa: BLE001
        st.warning(f"Couldn't load prices right now ({err}). Retrying in {REFRESH_SECONDS} seconds.")
        return

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

    # Top 10 table with a sparkline of today's prices
    st.subheader("Top 10 Indian companies")
    stocks = q.drop(index=live.NIFTY, errors="ignore")
    table = pd.DataFrame({
        "Company": [live.TOP10[t] for t in stocks.index],
        "Price (₹)": stocks["price"].values,
        "Change (₹)": stocks["change"].values,
        "Change": stocks["change_pct"].values * 100,
        "Today": [intra[t].dropna().tolist() if t in intra else [] for t in stocks.index],
    })
    styled = table.style.map(lambda v: f"color: {plots.GAIN if v >= 0 else plots.LOSS}",
                             subset=["Change (₹)", "Change"])
    st.dataframe(styled, hide_index=True, use_container_width=True, height=36 * (len(table) + 1) + 4,
                 column_config={
                     "Price (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                     "Change (₹)": st.column_config.NumberColumn(format="%+.2f"),
                     "Change": st.column_config.NumberColumn(format="%+.2f%%"),
                     "Today": st.column_config.LineChartColumn("Today (5-min)", width="medium"),
                 })

    # Charts
    t1, t2, t3, t4 = st.tabs(["NIFTY 50 today", "Top 10: today's moves", "Gold, 1 month", "Silver, 1 month"])
    with t1:
        st.plotly_chart(plots.intraday_line(intra[live.NIFTY], "NIFTY 50"), use_container_width=True)
    with t2:
        moves = pd.Series(stocks["change_pct"].values, index=[live.TOP10[t] for t in stocks.index])
        st.plotly_chart(plots.change_bars(moves), use_container_width=True)
    with t3:
        st.plotly_chart(plots.price_line(m["gold_inr_10g"], "Gold ₹/10 g"), use_container_width=True)
        st.caption("International (COMEX) price converted to rupees. Indian retail and MCX prices are "
                   "higher because they include import duty and GST.")
    with t4:
        st.plotly_chart(plots.price_line(m["silver_inr_kg"], "Silver ₹/kg"), use_container_width=True)
        st.caption("International (COMEX) price converted to rupees, before Indian duty and GST.")

    st.caption(f"Last updated {datetime.now(live.IST):%I:%M:%S %p} IST · refreshes every "
               f"{REFRESH_SECONDS} seconds · prices as of {q['as_of'].max():%d %b %Y}")


@st.fragment(run_every=NEWS_REFRESH_SECONDS)
def news_panel() -> None:
    st.subheader("Market news")
    try:
        items = get_news()
    except Exception:  # noqa: BLE001
        st.info("News is unavailable right now. It will retry shortly.")
        return
    if items.empty:
        st.info("No recent headlines found.")
        return
    for row in items.itertuples():
        title = row.title.replace("[", "(").replace("]", ")")  # keep the link markdown intact
        url = row.url.replace(")", "%29").replace(" ", "%20")
        st.markdown(f"**[{title}]({url})**")
        st.caption(f"{row.source} · {row.company} · {time_ago(row.published)}")
    st.caption("Headlines link to the original publishers. Updated every 30 minutes.")


live_panel()
st.divider()
news_panel()
