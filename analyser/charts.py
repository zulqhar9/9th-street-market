"""Chart output (PNG files). Uses one consistent style across every chart."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

PORTFOLIO_COLOR = "#1F6FB2"
BENCHMARK_COLOR = "#9AA5B1"
LOSS_COLOR = "#C8553D"

plt.rcParams.update({
    "figure.dpi": 120,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#E5E8EB",
    "grid.linewidth": 0.8,
    "axes.titleweight": "bold",
    "axes.titlesize": 13,
    "font.size": 10,
})


def _save(fig: plt.Figure, out_dir: Path, name: str) -> Path:
    path = out_dir / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def growth_vs_benchmark(portfolio: pd.Series, benchmark: pd.Series, bench_name: str, out_dir: Path) -> Path:
    bench = benchmark.loc[portfolio.index[0]:].dropna()
    bench = bench / bench.iloc[0]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(portfolio.index, portfolio, color=PORTFOLIO_COLOR, lw=2, label="Portfolio")
    ax.plot(bench.index, bench, color=BENCHMARK_COLOR, lw=1.6, label=bench_name)
    ax.axhline(1, color="#444", lw=0.8)
    ax.set_title(f"Growth of 1 rupee: portfolio vs {bench_name}")
    ax.set_ylabel("Value of 1 rupee invested")
    ax.legend(frameon=False)
    return _save(fig, out_dir, "growth_vs_benchmark.png")


def drawdown_chart(drawdown: pd.Series, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.fill_between(drawdown.index, drawdown, 0, color=LOSS_COLOR, alpha=0.35, lw=0)
    ax.plot(drawdown.index, drawdown, color=LOSS_COLOR, lw=1)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_title("Portfolio drawdown (fall from previous peak)")
    return _save(fig, out_dir, "drawdown.png")


def allocation(positions: pd.DataFrame, out_dir: Path) -> Path:
    data = positions.sort_values("market_value")
    weights = data["market_value"] / data["market_value"].sum()
    fig, ax = plt.subplots(figsize=(7, 0.55 * len(data) + 1.2))
    bars = ax.barh(data["name"], weights, color=PORTFOLIO_COLOR)
    ax.bar_label(bars, labels=[f"{w:.0%}" for w in weights], padding=4)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_xlim(0, weights.max() * 1.18)
    ax.grid(axis="y", visible=False)
    ax.set_title("Allocation by current market value")
    return _save(fig, out_dir, "allocation.png")


def risk_return(metrics: pd.DataFrame, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 5))
    style = {
        "portfolio": (PORTFOLIO_COLOR, 120),
        "benchmark": (BENCHMARK_COLOR, 120),
        "stock": ("#3B4A5A", 60),
    }
    for label, row in metrics.iterrows():
        color, size = style[row["kind"]]
        ax.scatter(row["volatility"], row["cagr"], s=size, color=color, zorder=3)
        ax.annotate(label, (row["volatility"], row["cagr"]), textcoords="offset points", xytext=(6, 4))
    ax.axhline(0, color="#444", lw=0.8)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set_xlabel("Annual volatility (risk)")
    ax.set_ylabel("Annual return (CAGR)")
    ax.set_title("Risk vs return")
    return _save(fig, out_dir, "risk_return.png")


def correlation(returns: pd.DataFrame, out_dir: Path) -> Path:
    corr = returns.corr()
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(corr, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr)), corr.index)
    ax.grid(False)
    for i in range(len(corr)):
        for j in range(len(corr)):
            v = corr.iat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="white" if v > 0.6 else "#222")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Correlation of daily returns")
    return _save(fig, out_dir, "correlation.png")
