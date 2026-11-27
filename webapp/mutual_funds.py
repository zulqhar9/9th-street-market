"""Mutual funds: search any Indian mutual fund, compare up to three with the NIFTY 50, and backtest a SIP."""
import pandas as pd
import streamlit as st

from analyser import live
from analyser import mutual_funds as mf
from webapp import plots, style, widgets

FUNDS = mf.funds()
PERIODS = {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10, "Max": None}
YAHOO_PERIOD = {"1Y": "1y", "3Y": "3y", "5Y": "5y", "10Y": "10y", "Max": "max"}
NIFTY_NAME = "NIFTY 50 (index)"


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_nav(code: int) -> pd.Series:
    return mf.nav_history(code)


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_nifty(period: str) -> pd.Series:
    return live.adjusted_closes([live.NIFTY], period)[live.NIFTY].dropna()


def pct(x: float | None, annual: bool = False) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:+.1%}" + (" a yr" if annual else "")


style.header(
    "Money tools",
    "Mutual funds",
    f"Search {len(FUNDS):,} Indian mutual funds, see how they've really performed against the NIFTY 50, and "
    "find out what a monthly SIP in them would be worth today. Daily NAVs from AMFI. Past returns don't "
    "predict future ones, and nothing here is investment advice.",
)

c1, c2, c3 = st.columns([1, 1, 1])
plan = c1.segmented_control("Plan", ["Direct", "Regular"], default="Direct", key="mf_plan",
                            help="Direct plans are bought straight from the fund house and charge lower fees. "
                                 "Regular plans pay a distributor commission, so their returns are a little lower.") \
    or "Direct"
groups = ["All types"] + sorted(FUNDS["group"].unique())
group = c2.selectbox("Type", groups)
pool = FUNDS[(FUNDS["plan"] == plan) & ((FUNDS["group"] == group) | (group == "All types"))]
cats = ["All categories"] + sorted(pool["category"].unique())
cat = c3.selectbox("Category", cats)
if cat != "All categories":
    pool = pool[pool["category"] == cat]

labels = pool.sort_values("label")["label"].tolist()
defaults = [next((l for l in labels if d.lower() in l.lower()), None) for d in mf.DEFAULT_FUNDS]
key = f"mf_pick_{plan}_{group}_{cat}"  # fresh defaults when the filters change
picks = st.multiselect("Funds to compare (up to 3)", labels, default=[d for d in defaults if d],
                       max_selections=3, key=key, placeholder="Search by fund name or fund house")
if not picks:
    st.info("Pick a fund above. Use Type and Category to narrow the list, e.g. Equity → Flexi Cap.")
    st.stop()

chosen = pool.set_index("label").loc[picks]
navs, failed = {}, []
with st.spinner("Fetching NAV history..."):
    for label, row in chosen.iterrows():
        try:
            navs[label] = get_nav(int(row["code"]))
        except Exception:  # noqa: BLE001
            failed.append(label)
if failed:
    st.warning(f"Couldn't load NAV history for {', '.join(failed)} right now. Try again in a minute.")
if not navs:
    st.stop()

# Headline cards: latest NAV and 1-year return
cols = st.columns(len(navs))
for col, (label, nav) in zip(cols, navs.items()):
    r1 = mf.trailing_return(nav, 1)
    col.metric(label, f"₹{nav.iloc[-1]:,.2f}", f"{r1:+.1%} in 1 year" if r1 is not None else "Under 1 year old",
               border=True, help=f"{chosen.loc[label, 'amc']} · {chosen.loc[label, 'category']} · "
                                 f"NAV on {nav.index[-1]:%d %b %Y}")

# Growth of ₹10,000 vs the NIFTY 50
frame = st.segmented_control("Period", list(PERIODS), default="5Y", key="mf_period",
                             label_visibility="collapsed") or "5Y"
years = PERIODS[frame]
end = max(n.index[-1] for n in navs.values())
start = max([n.index[0] for n in navs.values()] + ([end - pd.DateOffset(years=years)] if years else []))
try:
    nifty = get_nifty(YAHOO_PERIOD[frame])
    nifty.index = nifty.index.tz_localize(None)
except Exception:  # noqa: BLE001
    nifty = pd.Series(dtype=float)
lines = {}
for label, nav in {**navs, **({NIFTY_NAME: nifty} if not nifty.empty else {})}.items():
    s = nav.loc[start:]
    if len(s) > 1:
        lines[label] = 10_000 * s / s.iloc[0]
if lines:
    st.markdown(f"**₹10,000 invested on {pd.Timestamp(start):%d %b %Y}** would be worth today:")
    st.plotly_chart(plots.value_lines(lines), use_container_width=True, config={"displayModeBar": False})
    if years and start > end - pd.DateOffset(years=years) + pd.Timedelta(days=7):
        st.caption("A fund here is younger than the period picked, so all lines start from its launch.")

# Trailing returns table
rows = []
for label, nav in navs.items():
    rows.append({"Fund": label, "Category": chosen.loc[label, "category"],
                 "6 months": mf.trailing_return(nav, 0.5), "1 year": mf.trailing_return(nav, 1),
                 "3 years": mf.trailing_return(nav, 3), "5 years": mf.trailing_return(nav, 5),
                 "10 years": mf.trailing_return(nav, 10)})
if not nifty.empty:
    long_nifty = get_nifty("max")
    long_nifty.index = long_nifty.index.tz_localize(None)
    rows.append({"Fund": NIFTY_NAME, "Category": "Benchmark",
                 **{k: mf.trailing_return(long_nifty, y) for k, y in
                    [("6 months", 0.5), ("1 year", 1), ("3 years", 3), ("5 years", 5), ("10 years", 10)]}})
table = pd.DataFrame(rows)
st.dataframe(
    table.assign(**{c: table[c].map(lambda v: None if v is None else v * 100) for c in
                    ["6 months", "1 year", "3 years", "5 years", "10 years"]}),
    hide_index=True, use_container_width=True,
    column_config={c: st.column_config.NumberColumn(c, format="%+.1f%%",
                                                    help="Yearly average (CAGR)" if c in ("3 years", "5 years", "10 years")
                                                    else "Total change")
                   for c in ["6 months", "1 year", "3 years", "5 years", "10 years"]},
)
st.caption("3, 5 and 10-year figures are yearly averages (CAGR); 6 months and 1 year are total changes. "
           "Blank means the fund is younger than that.")

# SIP backtest
st.subheader("What would a SIP have made?")
s1, s2 = st.columns(2)
monthly = s1.number_input("Monthly SIP (₹)", min_value=500, max_value=10_00_000, value=5_000, step=500, format="%d")
sip_years = s2.slider("For the last (years)", 1, 15, 5)
results = {label: mf.sip_backtest(nav, monthly, sip_years) for label, nav in navs.items()}
done = {k: v for k, v in results.items() if v is not None}
if not done:
    st.info(f"None of these funds is {sip_years} years old yet. Pick a shorter period.")
else:
    cols = st.columns(len(done))
    for col, (label, r) in zip(cols, done.items()):
        col.metric(label, f"₹{widgets.indian(r.value)}", f"{r.xirr:+.1%} a year (XIRR)", border=True,
                   help=f"{r.instalments} instalments of ₹{widgets.indian(monthly)} = ₹{widgets.indian(r.invested)} "
                        f"invested since {r.start:%b %Y}")
    best_label = max(done, key=lambda k: done[k].value)
    b = done[best_label]
    st.markdown(f"₹{widgets.indian(monthly)} a month in **{best_label}** for the last {sip_years} "
                f"year{'s' if sip_years > 1 else ''} means ₹{widgets.indian(b.invested)} put in, now worth "
                f"**₹{widgets.indian(b.value)}**: a gain of ₹{widgets.indian(b.gain)}.")
    skipped = [k for k, v in results.items() if v is None]
    if skipped:
        st.caption(f"Not enough history for a {sip_years}-year SIP in {', '.join(skipped)}.")

st.caption("NAVs from AMFI via mfapi.in, refreshed every few hours. Fund returns are after the fund's own fees "
           "but before your taxes. The NIFTY 50 line is the price index without dividends, so it slightly "
           "understates the market. XIRR is the yearly return that accounts for when each SIP instalment went in.")
