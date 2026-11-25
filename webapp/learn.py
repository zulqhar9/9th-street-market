"""Learn: the numbers used on this site, explained in plain English with small try-it-yourself examples."""
import math

import streamlit as st

from webapp import style, widgets

style.header(
    "Learn",
    "The numbers, explained",
    "Short, plain-English guides to the measures used across this site. Change the numbers in each "
    "example to see how they behave.",
)


def result(text: str) -> None:
    st.markdown(f'<div style="font-size:1.35rem;font-weight:600;margin:0.2rem 0 0.4rem">{text}</div>',
                unsafe_allow_html=True)


# P/E ratio
st.subheader("P/E ratio: how much you pay for each rupee of profit")
st.write("The share price divided by the company's profit per share over the last year. A P/E of 25 means "
         "investors pay ₹25 for every ₹1 the company earns in a year. A high P/E usually means people expect "
         "fast growth; a low one can mean the stock is cheap, or that growth is expected to be slow.")
c1, c2 = st.columns(2)
price = c1.number_input("Share price (₹)", 1.0, 1_00_000.0, 1_500.0, 50.0, key="pe_price")
eps = c2.number_input("Profit per share last year (₹)", 0.1, 10_000.0, 60.0, 5.0, key="pe_eps")
pe = price / eps
result(f"P/E = {pe:.1f}")
st.caption(f"You'd pay ₹{pe:.1f} for every ₹1 of yearly profit. At today's profit it would take about "
           f"{pe:.0f} years of earnings to add up to the share price.")
st.divider()

# CAGR
st.subheader("CAGR: the steady yearly growth rate")
st.write("Compound annual growth rate answers: if this investment had grown at the same rate every year, "
         "what would that rate be? It's fairer than total return when comparing investments held for "
         "different lengths of time.")
c1, c2, c3 = st.columns(3)
start = c1.number_input("Start value (₹)", 1.0, 1e9, 10_000.0, 1_000.0, key="cagr_start")
end = c2.number_input("End value (₹)", 1.0, 1e9, 25_000.0, 1_000.0, key="cagr_end")
yrs = c3.number_input("Years", 0.5, 50.0, 5.0, 0.5, key="cagr_years")
cagr = (end / start) ** (1 / yrs) - 1
result(f"CAGR = {cagr:+.1%} a year")
st.caption(f"Total return is {end / start - 1:+.0%}, but spread over {yrs:g} years that's {cagr:+.1%} a year, "
           "compounded.")
st.divider()

# Drawdown
st.subheader("Drawdown: the worst fall along the way")
st.write("Maximum drawdown is the biggest drop from a previous high before a new high is reached. It shows "
         "how painful an investment could feel to hold. Losses are also harder to recover from than they "
         "look, because the bounce back starts from a smaller amount.")
fall = st.slider("If an investment falls by (%)", 5, 90, 30, 5, key="dd_fall")
needed = fall / (100 - fall)
result(f"It needs to rise {needed:.0%} to get back to where it was")
st.caption(f"₹100 falling {fall}% becomes ₹{100 - fall}. Getting back to ₹100 needs a {needed:.0%} gain, "
           f"not a {fall}% one.")
st.divider()

# Sharpe ratio
st.subheader("Sharpe ratio: return for the risk taken")
st.write("It compares how much an investment earned above a safe alternative (like a government bond) with "
         "how much its value jumped around (volatility). Higher is better: more reward per unit of risk. "
         "Above 1 is generally considered good; below 0 means it did worse than the safe option.")
c1, c2, c3 = st.columns(3)
ret = c1.slider("Annual return (%)", -20.0, 40.0, 15.0, 0.5, key="sh_ret")
vol = c2.slider("Volatility (%)", 1.0, 60.0, 18.0, 0.5, key="sh_vol")
rf = c3.slider("Safe rate (%)", 0.0, 10.0, 6.5, 0.25, key="sh_rf")
sharpe = (ret - rf) / vol
result(f"Sharpe ratio = {sharpe:.2f}")
st.caption(f"It earned {ret - rf:+.1f} percentage points above the safe rate, with {vol:g}% volatility.")
st.divider()

# Beta
st.subheader("Beta: how much a stock moves with the market")
st.write("Beta measures how a stock tends to move when the whole market (here, the NIFTY 50) moves. A beta "
         "of 1 moves in line with the market; 1.5 tends to move 50% more; 0.6 moves less, which can make it "
         "steadier in a downturn.")
c1, c2 = st.columns(2)
beta = c1.slider("Stock's beta", 0.0, 2.5, 1.2, 0.1, key="beta_b")
mkt = c2.slider("If the NIFTY 50 moves (%)", -10.0, 10.0, -3.0, 0.5, key="beta_m")
result(f"Expected move ≈ {beta * mkt:+.1f}%")
st.caption("A rough guide only: beta is based on past behaviour and real moves also depend on company news.")
st.divider()

# Compounding
st.subheader("Compounding and the rule of 72")
st.write("Growth earns growth: returns are added to your money, and next year's return is earned on the "
         "bigger total. A quick shortcut is the rule of 72: divide 72 by the yearly return to estimate how "
         "many years it takes to double your money.")
r = st.slider("Yearly return (%)", 1, 30, 12, 1, key="r72")
result(f"Doubles in about {72 / r:.1f} years")
st.caption(f"Exact figure at {r}%: {math.log(2) / math.log(1 + r / 100):.1f} years. "
           f"₹1 lakh at {r}% for 20 years becomes about ₹{widgets.indian(1e5 * (1 + r / 100) ** 20)}.")
st.page_link("webapp/sip.py", label="Try the SIP calculator", icon=":material/savings:")
