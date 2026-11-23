"""Portfolio Analyser: risk and return of any NSE portfolio vs the NIFTY 50, using the shared analysis code."""
from pathlib import Path

import pandas as pd
import streamlit as st

from analyser import BENCHMARK, BENCHMARK_NAME, analysis, db, metrics
from analyser.fetch import download_prices
from webapp import plots, style

ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(ttl=60 * 60, show_spinner=False)
def load_prices(tickers: tuple[str, ...], start: str) -> tuple[pd.DataFrame, set[str]]:
    return download_prices(list(tickers), start=start)


def default_holdings() -> pd.DataFrame:
    h = pd.read_csv(ROOT / "portfolio.csv", dtype={"ticker": str, "name": str})
    h["buy_date"] = pd.to_datetime(h["buy_date"]).dt.date
    return h


def clean(edited: pd.DataFrame) -> pd.DataFrame:
    h = edited.dropna(subset=["ticker", "shares", "buy_date"]).copy()
    h["ticker"] = h["ticker"].str.strip().str.upper()
    h = h[(h["ticker"] != "") & (h["shares"] > 0)].drop_duplicates("ticker")
    h["name"] = h["name"].fillna("").str.strip()
    h.loc[h["name"] == "", "name"] = h["ticker"]
    h["buy_date"] = pd.to_datetime(h["buy_date"]).dt.strftime("%Y-%m-%d")
    return h.reset_index(drop=True)


style.header(
    "Portfolio analytics",
    "Portfolio Analyser",
    "How has a portfolio really performed against the NIFTY 50, and how much risk did it take? "
    "The sample holds ₹10,000 in each of today's 10 largest NSE companies from January 2021. "
    "Edit the table to try your own stocks (NSE tickers end in .NS). Nothing you enter is saved.",
)

with st.form("holdings"):
    edited = st.data_editor(
        default_holdings(), num_rows="dynamic", hide_index=True, use_container_width=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", help="e.g. RELIANCE.NS", required=True),
            "name": st.column_config.TextColumn("Company"),
            "shares": st.column_config.NumberColumn("Shares", min_value=1, step=1, required=True),
            "buy_date": st.column_config.DateColumn("Bought on", format="DD MMM YYYY", required=True),
        })
    c1, c2 = st.columns([1, 3])
    risk_free = c1.number_input("Risk-free rate (% a year)", 0.0, 15.0, 6.5, 0.5,
                                help="Used for the Sharpe ratio. 6.5% is roughly an Indian government bond yield.")
    st.form_submit_button("Analyse portfolio", type="primary")

holdings = clean(edited)
if holdings.empty:
    st.info("Add at least one holding to analyse.")
    st.stop()

with st.spinner("Downloading prices and calculating..."):
    try:
        prices, missing = load_prices(tuple(holdings["ticker"]) + (BENCHMARK,), holdings["buy_date"].min())
    except Exception as err:  # noqa: BLE001
        st.error(f"Couldn't download prices: {err}")
        st.stop()
    if missing:
        st.warning(f"No price data for {', '.join(sorted(missing))}. Check the ticker symbols.")

    conn = db.connect(Path(":memory:"))  # same schema and SQL as the command-line report
    db.save_holdings(conn, holdings)
    db.save_prices(conn, prices)
    try:
        result = analysis.run(conn, holdings, risk_free / 100)
    except ValueError as err:
        st.error(str(err))
        st.stop()
    finally:
        conn.close()

port, bench = result.table.loc["Portfolio"], result.table.loc[BENCHMARK_NAME]
cost, value = result.positions["cost"].sum(), result.positions["market_value"].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Portfolio value", f"₹{value:,.0f}", f"{value / cost - 1:+.1%}", border=True,
          help=f"₹{cost:,.0f} invested, now worth ₹{value:,.0f}.")
m2.metric("Annual return", f"{port.cagr:+.1%}", f"{port.cagr - bench.cagr:+.1%} vs {BENCHMARK_NAME}", border=True)
m3.metric("Worst fall from peak", f"{port.max_drawdown:.1%}", f"{BENCHMARK_NAME}: {bench.max_drawdown:.1%}",
          delta_color="off", delta_arrow="off", border=True)
m4.metric("Sharpe ratio", f"{port.sharpe:.2f}", f"{BENCHMARK_NAME}: {bench.sharpe:.2f}",
          delta_color="off", delta_arrow="off", border=True)

st.subheader(f"Growth of ₹1: portfolio vs {BENCHMARK_NAME}")
st.plotly_chart(plots.growth(result.portfolio, result.close[BENCHMARK], BENCHMARK_NAME), use_container_width=True)
st.subheader("Drawdown (fall from previous peak)")
st.plotly_chart(plots.drawdown(metrics.drawdown(result.portfolio)), use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Risk vs return")
    st.plotly_chart(plots.risk_return(result.table), use_container_width=True)
with right:
    st.subheader("Allocation by current value")
    st.plotly_chart(plots.allocation(result.positions), use_container_width=True)

if len(result.holdings) > 1:
    st.subheader("Correlation of daily returns")
    st.caption("Close to 1 means two stocks move together, so holding both adds less diversification.")
    st.plotly_chart(plots.correlation(result.stock_returns), use_container_width=True)

st.subheader("Holdings")
st.dataframe(
    result.positions[["name", "shares", "buy_date", "buy_price", "last_price", "cost", "market_value",
                      "total_return"]].assign(total_return=lambda d: d["total_return"] * 100),
    hide_index=True, use_container_width=True,
    column_config={
        "name": "Company", "shares": "Shares", "buy_date": "Bought",
        "buy_price": st.column_config.NumberColumn("Buy price", format="₹%.2f"),
        "last_price": st.column_config.NumberColumn("Latest", format="₹%.2f"),
        "cost": st.column_config.NumberColumn("Cost", format="₹%,.0f"),
        "market_value": st.column_config.NumberColumn("Value", format="₹%,.0f"),
        "total_return": st.column_config.NumberColumn("Return", format="%+.1f%%"),
    })

st.subheader("Risk and return")
pct = ["total_return", "cagr", "volatility", "max_drawdown"]
st.dataframe(
    result.table.drop(columns="kind").assign(**{c: result.table[c] * 100 for c in pct}),
    use_container_width=True,
    column_config={
        "total_return": st.column_config.NumberColumn("Total return", format="%+.1f%%"),
        "cagr": st.column_config.NumberColumn("CAGR", format="%+.1f%%"),
        "volatility": st.column_config.NumberColumn("Volatility", format="%.1f%%"),
        "max_drawdown": st.column_config.NumberColumn("Max drawdown", format="%.1f%%"),
        "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
        "beta": st.column_config.NumberColumn("Beta", format="%.2f"),
    })
st.caption("Each stock is measured from its own buy date. For analysis and learning only, not investment advice.")
