"""SIP (Systematic Investment Plan) maths: monthly investing with optional yearly step-up.

Uses the convention of most Indian SIP calculators: a monthly rate of (annual return / 12),
and each instalment is invested at the start of the month, so it earns that month's return.
"""
from __future__ import annotations

import pandas as pd


def schedule(monthly: float, annual_return: float, years: int, step_up: float = 0.0) -> pd.DataFrame:
    """Month-by-month table: month, year, instalment, invested (running total) and value.

    step_up raises the monthly instalment by that fraction at the start of each new year
    (0.10 = invest 10% more each year).
    """
    if monthly <= 0 or years <= 0:
        raise ValueError("Monthly amount and years must be positive.")
    i = annual_return / 12
    rows, value, invested, amount = [], 0.0, 0.0, float(monthly)
    for m in range(1, years * 12 + 1):
        if m > 1 and (m - 1) % 12 == 0:
            amount *= 1 + step_up
        invested += amount
        value = (value + amount) * (1 + i)
        rows.append((m, (m - 1) // 12 + 1, amount, invested, value))
    return pd.DataFrame(rows, columns=["month", "year", "instalment", "invested", "value"])


def future_value(monthly: float, annual_return: float, years: int) -> float:
    """Closed-form value of a flat SIP (no step-up), for checking the schedule."""
    i, n = annual_return / 12, years * 12
    if i == 0:
        return monthly * n
    return monthly * ((1 + i) ** n - 1) / i * (1 + i)


def yearly(df: pd.DataFrame) -> pd.DataFrame:
    """Year-end totals from a monthly schedule."""
    return df.groupby("year").last()[["invested", "value"]].reset_index()
