"""SIP calculator: what a monthly investment grows to, with an optional yearly step-up."""
import streamlit as st

from analyser import sip
from webapp import plots, style, widgets

style.header(
    "Money tools",
    "SIP calculator",
    "See what investing a fixed amount every month could grow to. Add a yearly step-up if you plan to "
    "invest a bit more each year. Returns are an assumption, not a promise, and aren't investment advice.",
)

c1, c2 = st.columns(2)
monthly = c1.number_input("Monthly investment (₹)", min_value=500, max_value=10_00_000, value=5_000,
                          step=500, format="%d")
years = c2.slider("Investment period (years)", 1, 40, 10)
c3, c4 = st.columns(2)
rate = c3.slider("Expected return (% a year)", 1.0, 25.0, 12.0, 0.5,
                 help="12% is a commonly used assumption for equity mutual funds over long periods. "
                      "Real returns vary year to year and can be negative.")
step = c4.slider("Yearly step-up (%)", 0, 25, 0,
                 help="Raise your monthly amount by this much every year, e.g. in line with a pay rise.")

df = sip.schedule(monthly, rate / 100, years, step / 100)
invested, value = df["invested"].iloc[-1], df["value"].iloc[-1]
gains = value - invested

st.markdown(widgets.CSS + f"""
<div class="wb"><div class="wb-grid">
  <div class="wb-tile"><div class="wb-label">You invest</div>
    <div><div class="wb-value">₹{widgets.indian(invested)}</div>
    <div class="wb-foot" style="margin-top:2px">over {years} year{'s' if years > 1 else ''}</div></div></div>
  <div class="wb-tile"><div class="wb-label">Estimated growth</div>
    <div><div class="wb-value" style="color:{widgets.UP}">₹{widgets.indian(gains)}</div>
    <div class="wb-foot" style="margin-top:2px">{gains / invested:.0%} on top of what you put in</div></div></div>
  <div class="wb-tile" style="grid-column: span 2"><div class="wb-label">Total value</div>
    <div><div class="wb-value" style="font-size:2.2rem">₹{widgets.indian(value)}</div>
    <div class="wb-foot" style="margin-top:2px">at {rate:g}% a year{f", with a {step}% yearly step-up" if step else ""}</div></div></div>
</div></div>""", unsafe_allow_html=True)

st.plotly_chart(plots.sip_growth(sip.yearly(df)), use_container_width=True, config={"displayModeBar": False})

if step:
    flat = sip.future_value(monthly, rate / 100, years)
    st.caption(f"Without the step-up, ₹{widgets.indian(monthly)} a month would grow to ₹{widgets.indian(flat)}. "
               f"The step-up adds ₹{widgets.indian(value - flat)}.")
st.caption("Assumes each instalment is invested at the start of the month and grows at a steady rate. "
           "Taxes, fees and inflation are not included.")
