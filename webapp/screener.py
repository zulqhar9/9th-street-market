"""Stock screener: filter the NIFTY 50 by sector, valuation, 52-week position and today's move."""
import pandas as pd
import streamlit as st

from analyser import live
from webapp import common, style

NIFTY50 = live.nifty50()


@st.cache_data(ttl=2 * 60 * 60, show_spinner=False)
def get_data() -> pd.DataFrame:
    df = live.screener_data(NIFTY50["ticker"].tolist())
    return NIFTY50.set_index("ticker").join(df, how="left")


style.header(
    "Explore",
    "Stock screener",
    "Filter the NIFTY 50 to find stocks that match what you're looking for: a sector, a valuation range, "
    "or where the price sits in its 52-week range. For research only, not investment advice.",
)

with st.spinner("Loading numbers for all 50 stocks (first load takes about 20 seconds)..."):
    try:
        data = get_data()
    except Exception as err:  # noqa: BLE001
        st.error(f"Couldn't load stock data right now ({err}). Try again in a minute.")
        st.stop()

data["short"] = data["name"].map(common.short_name)

PRESETS = {
    "All": lambda d: d,
    "Near 52-week low": lambda d: d[d["pos52"] <= 0.2],
    "Near 52-week high": lambda d: d[d["pos52"] >= 0.8],
    "Low P/E (under 20)": lambda d: d[d["pe"] < 20],
    "Up today": lambda d: d[d["change_pct"] > 0],
    "Down today": lambda d: d[d["change_pct"] < 0],
}
preset = st.segmented_control("Quick screens", list(PRESETS), default="All", key="screen_preset") or "All"

c1, c2, c3 = st.columns(3)
sectors = c1.multiselect("Sector", sorted(data["industry"].dropna().unique()), placeholder="All sectors")
PE_CAP = 100  # a few stocks have P/E in the hundreds; the top of the slider means "100 or more"
pe_lo, pe_hi = c2.slider("P/E ratio", 0, PE_CAP, (0, PE_CAP), 1,
                         help="Price divided by the last 12 months' earnings per share. Lower can mean "
                              "cheaper, but also slower expected growth. The top end means 100 or more.")
pos_lo, pos_hi = c3.slider("52-week position (%)", 0, 100, (0, 100),
                           help="0% = at the past year's lowest price, 100% = at its highest.")

d = PRESETS[preset](data)
if sectors:
    d = d[d["industry"].isin(sectors)]
if (pe_lo, pe_hi) != (0, PE_CAP):  # untouched slider keeps stocks with no P/E too
    upper = float("inf") if pe_hi == PE_CAP else pe_hi
    d = d[d["pe"].between(pe_lo, upper)]
d = d[d["pos52"].isna() | d["pos52"].between(pos_lo / 100, pos_hi / 100)]

st.markdown(f"**{len(d)} of {len(data)}** stocks match")
if d.empty:
    st.info("No stocks match these filters. Try widening the ranges.")
    st.stop()

d = d.sort_values("market_cap", ascending=False)
st.dataframe(
    pd.DataFrame({
        "Company": d["short"].values,
        "Sector": d["industry"].values,
        "Price": d["price"].values,
        "Today": d["change_pct"].values * 100,
        "P/E": d["pe"].values,
        "52-week position": d["pos52"].values * 100,
        "Market value (₹ cr)": d["market_cap"].values / 1e7,
        "Details": ["stock?symbol=" + s for s in d["symbol"]],
    }),
    hide_index=True, use_container_width=True, height=min(36 * (len(d) + 1) + 4, 720),
    column_config={
        "Price": st.column_config.NumberColumn("Price (₹)", format="₹%.2f"),
        "Today": st.column_config.NumberColumn(format="%+.2f%%"),
        "P/E": st.column_config.NumberColumn(format="%.1f"),
        "52-week position": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
        "Market value (₹ cr)": st.column_config.NumberColumn(format="%,.0f"),
        "Details": st.column_config.LinkColumn("", display_text="Open ›", width="small"),
    },
)
st.caption("Sorted by company value. Click a column to re-sort. P/E and 52-week figures from Yahoo Finance, "
           "refreshed every 2 hours; some companies (e.g. banks with unusual earnings) may show no P/E.")
