"""Capital gains tax calculator for listed Indian shares and equity mutual funds."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from analyser import tax
from webapp import style, widgets

style.header(
    "Money tools",
    "Capital gains tax calculator",
    "Selling shares at a profit? See whether it counts as short-term or long-term, and roughly how much tax "
    "you'd pay under current Indian rules. An estimate only, not tax advice. Check with a tax professional.",
)


def rupees(x: float) -> str:
    sign = "−" if x < 0 else ""
    return f"{sign}₹{widgets.indian(abs(x))}"


c1, c2, c3 = st.columns(3)
qty = c1.number_input("Number of shares", min_value=1, max_value=10_00_00_000, value=100, step=1, format="%d")
buy_price = c2.number_input("Buy price per share (₹)", min_value=0.01, value=1_000.0, step=10.0, format="%.2f")
sell_price = c3.number_input("Sell price per share (₹)", min_value=0.0, value=1_400.0, step=10.0, format="%.2f")
c4, c5, c6 = st.columns(3)
today = date.today()
buy_date = c4.date_input("Bought on", value=today - timedelta(days=200), min_value=date(2000, 1, 1),
                         max_value=today, format="DD/MM/YYYY")
sell_date = c5.date_input("Sold on (or will sell on)", value=today, min_value=date(2000, 1, 1),
                          max_value=today + timedelta(days=5 * 365), format="DD/MM/YYYY")
charges = c6.number_input("Brokerage and charges (₹)", min_value=0.0, value=0.0, step=10.0, format="%.0f",
                          help="Brokerage, exchange and DP charges for buying and selling. STT can't be deducted.")

with st.expander("More options"):
    used = st.number_input("Long-term gains already made this financial year (₹)", min_value=0.0, value=0.0,
                           step=10_000.0, format="%.0f",
                           help="The yearly exemption on long-term gains is shared across all your sales in a "
                                "financial year (April to March).")
    fmv = None
    if buy_date < tax.GRANDFATHER_BEFORE:
        fmv = st.number_input("Price on 31 Jan 2018 (₹)", min_value=0.0, value=0.0, step=10.0, format="%.2f",
                              help="Shares bought before 1 Feb 2018 are 'grandfathered': gains up to that date "
                                   "aren't taxed. Use the highest price the share traded at on 31 Jan 2018.") or None
    else:
        st.caption("Bought before 1 Feb 2018? Set an earlier buy date to enter its 31 Jan 2018 price.")

try:
    r = tax.capital_gains(qty, buy_price, sell_price, buy_date, sell_date, charges, fmv, used)
except ValueError as err:
    st.error(str(err))
    st.stop()

held = f"{r.days_held // 365} y {(r.days_held % 365) // 30} m" if r.days_held >= 365 else f"{r.days_held} days"
gain_colour = widgets.UP if r.gain >= 0 else widgets.DOWN
st.markdown(widgets.CSS + f"""
<div class="wb"><div class="wb-grid">
  <div class="wb-tile"><div class="wb-label">{'Profit' if r.gain >= 0 else 'Loss'}</div>
    <div><div class="wb-value" style="color:{gain_colour}">{rupees(r.gain)}</div>
    <div class="wb-foot" style="margin-top:2px">{r.term} · held {held}</div></div></div>
  <div class="wb-tile"><div class="wb-label">Tax to pay</div>
    <div><div class="wb-value">{rupees(r.total_tax)}</div>
    <div class="wb-foot" style="margin-top:2px">{f"{r.effective_rate:.1%} of your profit" if r.gain > 0 else "No tax on a loss"}</div></div></div>
  <div class="wb-tile" style="grid-column: span 2"><div class="wb-label">Profit after tax</div>
    <div><div class="wb-value" style="font-size:2.2rem">{rupees(r.after_tax_profit)}</div>
    <div class="wb-foot" style="margin-top:2px">from a sale of {rupees(r.sale_value)} · tax falls in {r.financial_year}</div></div></div>
</div></div>""", unsafe_allow_html=True)

if r.gain > 0 and not r.long_term:
    lt_date = (pd.Timestamp(buy_date) + pd.DateOffset(months=12)).date() + timedelta(days=1)
    later = tax.capital_gains(qty, buy_price, sell_price, buy_date, lt_date, charges, fmv, used)
    saving = r.total_tax - later.total_tax
    if saving > 0:
        st.info(f"Holding until **{lt_date:%d %b %Y}** would make this a long-term gain. At the same price "
                f"you'd pay {rupees(later.total_tax)} instead, saving **{rupees(saving)}**. Prices can "
                "move in the meantime, though.")
elif r.gain < 0:
    st.info(f"A {r.term.lower()} loss can be set off against other capital gains this year"
            f"{'' if r.long_term else ' (short-term losses against both short- and long-term gains)'}, "
            "and anything left over can be carried forward for 8 years if you file your return on time.")

st.subheader("How it's worked out")
rows = [
    ("Sale value", rupees(r.sale_value), f"{qty:,} shares × ₹{sell_price:,.2f}"),
    ("Cost", rupees(r.cost), "Buy price × shares, plus charges"
     + (" (31 Jan 2018 price used)" if fmv and r.long_term and r.cost > qty * buy_price + charges else "")),
    ("Profit", rupees(r.gain), f"{r.term}: held {r.days_held:,} days "
                               f"({'more than 12 months' if r.long_term else '12 months or less'})"),
]
if r.long_term:
    rows.append(("Exempt", rupees(r.exempt), f"First ₹{widgets.indian(tax.rules_for(sell_date).ltcg_exemption)} "
                                            f"of long-term gains each year is tax-free"))
rows += [
    ("Taxable", rupees(r.taxable), ""),
    ("Tax", rupees(r.tax), f"{r.rate:.1%} {r.term.lower()} rate for sales "
                           f"{'on or after' if sell_date >= tax.RATE_CHANGE else 'before'} 23 Jul 2024"),
    ("Cess", rupees(r.cess), "4% health and education cess"),
    ("Total tax", rupees(r.total_tax), f"Falls in {r.financial_year}"),
]
st.dataframe(pd.DataFrame(rows, columns=["", "Amount", "How"]), hide_index=True, use_container_width=True)

with st.expander("The rules in short"):
    st.markdown(
        "- **Short-term** (held 12 months or less): taxed at **20%** (15% for sales before 23 Jul 2024).\n"
        "- **Long-term** (held more than 12 months): the first **₹1.25 lakh** of gains each financial year is "
        "tax-free, and the rest is taxed at **12.5%** (₹1 lakh and 10% before Budget 2024).\n"
        "- **Grandfathering:** for shares bought before 1 Feb 2018, gains made up to 31 Jan 2018 aren't taxed.\n"
        "- **Cess** of 4% is added to the tax. Budget 2026 kept all of these rates the same.")
st.caption("Applies to listed shares and equity mutual funds sold through a recognised exchange with STT paid, "
           "for resident individuals. Doesn't include surcharge for very high incomes, or using the basic "
           "exemption limit when total income is low. Intraday trades are business income, not capital gains.")
