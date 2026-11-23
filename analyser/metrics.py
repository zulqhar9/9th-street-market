"""Risk and return measures. All functions take pandas Series of prices or daily returns."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().dropna()


def cagr(prices: pd.Series) -> float:
    """Compound annual growth rate between the first and last price."""
    prices = prices.dropna()
    years = (prices.index[-1] - prices.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return (prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1


def annual_volatility(returns: pd.Series) -> float:
    return returns.std() * math.sqrt(TRADING_DAYS)


def drawdown(prices: pd.Series) -> pd.Series:
    """Percentage below the running peak at each date (0 at a new high, negative otherwise)."""
    return prices / prices.cummax() - 1


def max_drawdown(prices: pd.Series) -> float:
    return drawdown(prices.dropna()).min()


def sharpe_ratio(returns: pd.Series, risk_free_annual: float) -> float:
    """Annualised Sharpe ratio using a constant annual risk-free rate."""
    rf_daily = (1 + risk_free_annual) ** (1 / TRADING_DAYS) - 1
    excess = returns - rf_daily
    sd = excess.std()
    return float("nan") if sd == 0 or np.isnan(sd) else excess.mean() / sd * math.sqrt(TRADING_DAYS)


def beta(returns: pd.Series, market_returns: pd.Series) -> float:
    both = pd.concat([returns, market_returns], axis=1, join="inner").dropna()
    var = both.iloc[:, 1].var()
    return float("nan") if var == 0 else both.iloc[:, 0].cov(both.iloc[:, 1]) / var


def portfolio_index(prices: pd.DataFrame, holdings: pd.DataFrame) -> pd.Series:
    """Time-weighted growth of 1.0 invested on the first buy date.

    Each day's return only uses holdings already owned the day before, so buying a
    new stock later adds money to the portfolio without showing up as a fake gain.
    """
    shares = holdings.set_index("ticker")["shares"].astype(float)
    buy_dates = pd.to_datetime(holdings.set_index("ticker")["buy_date"])

    px = prices[shares.index].ffill()
    px = px.loc[px.index >= buy_dates.min()]

    held = pd.DataFrame({t: px.index >= buy_dates[t] for t in px.columns}, index=px.index)
    held_yesterday = held.shift(1, fill_value=False).astype(bool)

    values = px.mul(shares, axis=1)
    today = values.where(held_yesterday).sum(axis=1)
    yesterday = values.shift(1).where(held_yesterday).sum(axis=1)

    daily = (today / yesterday - 1).where(yesterday > 0, 0.0)
    return (1 + daily).cumprod().rename("Portfolio")


def summarise(prices: pd.Series, market: pd.Series, risk_free_annual: float) -> dict[str, float]:
    """Headline metrics for one price (or index) series over its own date range."""
    prices = prices.dropna()
    rets = daily_returns(prices)
    mkt_rets = daily_returns(market.loc[prices.index[0]:].dropna())
    return {
        "total_return": prices.iloc[-1] / prices.iloc[0] - 1,
        "cagr": cagr(prices),
        "volatility": annual_volatility(rets),
        "max_drawdown": max_drawdown(prices),
        "sharpe": sharpe_ratio(rets, risk_free_annual),
        "beta": beta(rets, mkt_rets),
    }
