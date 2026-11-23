"""Write the results to reports/: a metrics CSV and a readable Markdown summary."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


def _pct(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{x:+.1%}" if x else "0.0%"


def _num(x: float, digits: int = 2) -> str:
    return "n/a" if pd.isna(x) else f"{x:.{digits}f}"


def _money(x: float) -> str:
    return f"₹{x:,.0f}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def write_report(
    positions: pd.DataFrame,
    metrics: pd.DataFrame,
    charts: list[Path],
    out_dir: Path,
    bench_name: str,
    risk_free: float,
) -> Path:
    metrics.drop(columns="kind").to_csv(out_dir / "metrics.csv", float_format="%.6f")
    positions.to_csv(out_dir / "positions.csv", index=False)

    cost, value = positions["cost"].sum(), positions["market_value"].sum()
    port, bench = metrics.loc["Portfolio"], metrics.loc[bench_name]

    pos_rows = [
        [r.name, f"{r.shares:g}", r.buy_date, _money(r.cost), _money(r.market_value), _pct(r.total_return)]
        for r in positions.itertuples()
    ]
    met_rows = [
        [label, _pct(m.total_return), _pct(m.cagr), _pct(m.volatility).lstrip("+"),
         _pct(m.max_drawdown), _num(m.sharpe), _num(m.beta)]
        for label, m in metrics.iterrows()
    ]

    lines = [
        "# Portfolio report",
        "",
        f"Generated {date.today():%d %b %Y}. Prices up to {positions['last_date'].max()}.",
        "",
        "## Summary",
        "",
        f"- Invested **{_money(cost)}**, now worth **{_money(value)}** ({_pct(value / cost - 1)}).",
        f"- Annual return (time-weighted): **{_pct(port.cagr)}** vs {bench_name} **{_pct(bench.cagr)}** "
        f"over the same period.",
        f"- Worst fall from a peak: **{_pct(port.max_drawdown)}** (portfolio) vs {_pct(bench.max_drawdown)} ({bench_name}).",
        f"- Sharpe ratio {_num(port.sharpe)} (risk-free rate assumed {risk_free:.1%} a year); "
        f"beta {_num(port.beta)} to the {bench_name}.",
        "",
        "## Holdings",
        "",
        _table(["Stock", "Shares", "Bought", "Cost", "Value", "Return"], pos_rows),
        "",
        "## Risk and return",
        "",
        "Each stock is measured from its own buy date; the portfolio and benchmark from the first buy date.",
        "",
        _table(["", "Total return", "CAGR", "Volatility", "Max drawdown", "Sharpe", "Beta"], met_rows),
        "",
        "## Charts",
        "",
        *[f"![{c.stem.replace('_', ' ')}]({c.name})\n" for c in charts],
        "_For analysis and learning only. Not investment advice._",
        "",
    ]
    path = out_dir / "summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
