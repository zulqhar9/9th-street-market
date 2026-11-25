"""Capital gains tax on listed Indian shares (and equity mutual funds) sold on a stock exchange.

Rules for resident individuals, where STT was paid on the sale (Sections 111A and 112A):
- Held 12 months or less: short-term gain (STCG), taxed at a flat rate.
- Held more than 12 months: long-term gain (LTCG), taxed above a yearly exemption.
- Rates changed for sales on or after 23 July 2024 (Budget 2024): STCG 15% -> 20%,
  LTCG 10% -> 12.5%, and the LTCG exemption rose from ₹1 lakh to ₹1.25 lakh for
  FY 2024-25 onwards. Budget 2026 left these unchanged.
- Shares bought before 1 Feb 2018 are "grandfathered": their cost can be stepped up to the
  31 Jan 2018 price (capped at the sale price), so gains made before then stay untaxed.
- 4% health and education cess is added to the tax. Surcharge (only for very high incomes)
  and the basic exemption limit are not modelled.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

RATE_CHANGE = date(2024, 7, 23)
GRANDFATHER_BEFORE = date(2018, 2, 1)
CESS = 0.04


@dataclass(frozen=True)
class Rules:
    stcg_rate: float
    ltcg_rate: float
    ltcg_exemption: float


def rules_for(sell_date: date) -> Rules:
    """Rates in force on the day of sale."""
    new = sell_date >= RATE_CHANGE
    exemption = 1_25_000 if sell_date >= date(2024, 4, 1) else 1_00_000  # whole of FY 2024-25 onwards
    return Rules(stcg_rate=0.20 if new else 0.15, ltcg_rate=0.125 if new else 0.10, ltcg_exemption=exemption)


def is_long_term(buy_date: date, sell_date: date) -> bool:
    """True when held for more than 12 months."""
    return sell_date > (pd.Timestamp(buy_date) + pd.DateOffset(months=12)).date()


def financial_year(d: date) -> str:
    """'FY 2025-26' for any date from 1 Apr 2025 to 31 Mar 2026."""
    start = d.year if d.month >= 4 else d.year - 1
    return f"FY {start}-{str(start + 1)[-2:]}"


@dataclass(frozen=True)
class TaxResult:
    long_term: bool
    days_held: int
    cost: float              # what the shares cost, after any grandfathering, plus charges
    sale_value: float
    gain: float              # negative for a loss
    rate: float
    exempt: float            # part of a long-term gain covered by the yearly exemption
    taxable: float
    tax: float               # before cess
    cess: float
    financial_year: str

    @property
    def total_tax(self) -> float:
        return self.tax + self.cess

    @property
    def after_tax_profit(self) -> float:
        return self.gain - self.total_tax

    @property
    def effective_rate(self) -> float:
        return self.total_tax / self.gain if self.gain > 0 else 0.0

    @property
    def term(self) -> str:
        return "Long-term" if self.long_term else "Short-term"


def capital_gains(quantity: float, buy_price: float, sell_price: float, buy_date: date, sell_date: date,
                  charges: float = 0.0, fmv_2018: float | None = None, exemption_used: float = 0.0) -> TaxResult:
    """Tax on one sale.

    charges: brokerage and other costs of buying and selling (STT is not deductible).
    fmv_2018: highest price on 31 Jan 2018, for shares bought before 1 Feb 2018.
    exemption_used: long-term gains already made this financial year that used up the exemption.
    """
    if quantity <= 0 or buy_price <= 0 or sell_price < 0:
        raise ValueError("Quantity and buy price must be positive.")
    if sell_date < buy_date:
        raise ValueError("The sale date can't be before the purchase date.")

    long_term = is_long_term(buy_date, sell_date)
    rules = rules_for(sell_date)
    sale_value = quantity * sell_price

    unit_cost = buy_price
    if long_term and fmv_2018 and buy_date < GRANDFATHER_BEFORE:
        unit_cost = max(buy_price, min(fmv_2018, sell_price))
    cost = quantity * unit_cost + charges
    gain = sale_value - cost

    rate = rules.ltcg_rate if long_term else rules.stcg_rate
    exempt = 0.0
    if long_term and gain > 0:
        exempt = min(gain, max(rules.ltcg_exemption - exemption_used, 0.0))
    taxable = max(gain - exempt, 0.0)
    tax = taxable * rate
    return TaxResult(long_term=long_term, days_held=(sell_date - buy_date).days, cost=cost,
                     sale_value=sale_value, gain=gain, rate=rate, exempt=exempt, taxable=taxable,
                     tax=tax, cess=tax * CESS, financial_year=financial_year(sell_date))
