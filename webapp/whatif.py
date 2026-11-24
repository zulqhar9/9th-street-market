"""'What if I had invested?' calculator: compare any NSE stock with the NIFTY 50, gold and silver."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from analyser import live, whatif
from webapp import common, plots, style

EQUITIES = live.nse_equities()
OPTIONS = list(whatif.SPECIAL) + EQUITIES["label"].tolist()
TICKER_OF = {**whatif.SPECIAL, **dict(zip(EQUITIES["label"], EQUITIES["ticker"]))}
DEFAULTS = ["NIFTY 50", "Gold", "Reliance Industries Limited (RELIANCE)"]


@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_prices(ticker: str, start: str) -> pd.Series:
    return whatif.rupee_prices(ticker, start)


def display_name(label: str) -> str:
    if label in whatif.SPECIAL:
        return label
    return common.short_name(label.rsplit(" (", 1)[0])


style.header(
    "Investment calculator",
    "What if I had invested?",
    "Pick an amount, a start date and up to four investments: any NSE stock, the NIFTY 50, gold or silver. "
    "See what the money would be worth today. Based on past prices only, not investment advice.",
)

c1, c2 = st.columns(2)
amount = c1.number_input("Amount invested (₹)", min_value=1_000, max_value=10_00_00_000, value=10_000,
                         step=1_000, format="%d")
start = c2.date_input("Invested on", value=date.today() - timedelta(days=5 * 365),
                      min_value=date(2005, 1, 1), max_value=date.today() - timedelta(days=7),
                      format="DD/MM/YYYY")
picks = st.multiselect("Compare up to four", OPTIONS, default=[d for d in DEFAULTS if d in OPTIONS],
                       max_selections=4, placeholder="Search for a stock, or pick NIFTY 50, Gold or Silver")
if not picks:
    st.info("Pick at least one investment to compare.")
    st.stop()

outcomes, failed = [], []
with st.spinner("Fetching prices..."):
    for label in picks:
        try:
            prices = get_prices(TICKER_OF[label], start.isoformat())
            outcomes.append(whatif.Outcome(display_name(label), whatif.grow(prices, amount), amount))
        except Exception:  # noqa: BLE001
            failed.append(display_name(label))
if failed:
    st.warning(f"No price history for {', '.join(failed)} from that date. It may have listed later; "
               "try a more recent start date.")
if not outcomes:
    st.stop()

best = max(outcomes, key=lambda o: o.final)
st.markdown(f"### ₹{amount:,.0f} in {best.name} on {start:%d %b %Y} would be worth "
            f"**₹{best.final:,.0f}** today")

cols = st.columns(len(outcomes))
for col, o in zip(cols, sorted(outcomes, key=lambda o: -o.final)):
    col.metric(o.name, f"₹{o.final:,.0f}", f"{o.total_return:+.1%}", border=True,
               help=f"{o.cagr:+.1%} a year · worst fall along the way {o.worst_fall:.1%}")

st.plotly_chart(plots.value_lines({o.name: o.value for o in outcomes}), use_container_width=True,
                config={"displayModeBar": False})

st.dataframe(
    pd.DataFrame([{
        "Investment": o.name, "Value today": o.final, "Total return": o.total_return * 100,
        "Per year": o.cagr * 100, "Worst fall": o.worst_fall * 100,
    } for o in sorted(outcomes, key=lambda o: -o.final)]),
    hide_index=True, use_container_width=True,
    column_config={
        "Value today": st.column_config.NumberColumn(format="₹%,.0f"),
        "Total return": st.column_config.NumberColumn(format="%+.1f%%"),
        "Per year": st.column_config.NumberColumn(format="%+.1f%%", help="Compound annual growth rate"),
        "Worst fall": st.column_config.NumberColumn(format="%.1f%%", help="Largest drop from a previous high"),
    })
st.caption("Stocks use prices adjusted for dividends and splits, so returns include dividends reinvested. "
           "Gold and silver are international prices in rupees, before Indian duty and GST. Taxes and fees "
           "are ignored. Past returns don't predict future ones.")
