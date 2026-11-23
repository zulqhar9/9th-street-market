"""Interactive Plotly charts for the website. Colours match the PNG report charts."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PRIMARY = "#1F6FB2"
MUTED = "#9AA5B1"
GAIN = "#2E8B57"
LOSS = "#C8553D"
STOCK = "#3B4A5A"


def _layout(fig: go.Figure, height: int = 360, pct_y: bool = False) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.08, x=0), hovermode="x unified")
    if pct_y:
        fig.update_yaxes(tickformat=".0%")
    return fig


def intraday_line(series: pd.Series, name: str) -> go.Figure:
    s = series.dropna()
    color = GAIN if len(s) and s.iloc[-1] >= s.iloc[0] else LOSS
    fig = go.Figure(go.Scatter(x=s.index, y=s, mode="lines", name=name, line=dict(color=color, width=2)))
    fig.update_xaxes(tickformat="%H:%M")
    return _layout(fig, height=320)


def change_bars(changes: pd.Series) -> go.Figure:
    s = changes.sort_values()
    fig = go.Figure(go.Bar(x=s, y=s.index, orientation="h",
                           marker_color=[GAIN if v >= 0 else LOSS for v in s],
                           text=[f"{v:+.2%}" for v in s], textposition="outside",
                           hovertemplate="%{y}: %{x:+.2%}<extra></extra>"))
    fig.update_xaxes(tickformat=".1%", zeroline=True, zerolinecolor="#888")
    fig.update_layout(hovermode="closest")
    return _layout(fig, height=380)


def price_line(series: pd.Series, name: str, prefix: str = "₹") -> go.Figure:
    fig = go.Figure(go.Scatter(x=series.index, y=series, mode="lines", name=name,
                               line=dict(color=PRIMARY, width=2),
                               hovertemplate=f"%{{x|%d %b}}: {prefix}%{{y:,.0f}}<extra></extra>"))
    fig.update_layout(hovermode="closest")
    return _layout(fig, height=300)


def growth(portfolio: pd.Series, benchmark: pd.Series, bench_name: str) -> go.Figure:
    bench = benchmark.loc[portfolio.index[0]:].dropna()
    bench = bench / bench.iloc[0]
    fig = go.Figure([
        go.Scatter(x=portfolio.index, y=portfolio, name="Portfolio", line=dict(color=PRIMARY, width=2.5)),
        go.Scatter(x=bench.index, y=bench, name=bench_name, line=dict(color=MUTED, width=2)),
    ])
    fig.add_hline(y=1, line_color="#888", line_width=1)
    fig.update_yaxes(title="Value of ₹1 invested", tickprefix="₹")
    return _layout(fig, height=400)


def drawdown(dd: pd.Series) -> go.Figure:
    fig = go.Figure(go.Scatter(x=dd.index, y=dd, fill="tozeroy", line=dict(color=LOSS, width=1),
                               name="Drawdown"))
    return _layout(fig, height=260, pct_y=True)


def allocation(positions: pd.DataFrame) -> go.Figure:
    d = positions.sort_values("market_value")
    w = d["market_value"] / d["market_value"].sum()
    fig = go.Figure(go.Bar(x=w, y=d["name"], orientation="h", marker_color=PRIMARY,
                           text=[f"{v:.0%}" for v in w], textposition="outside",
                           hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", range=[0, w.max() * 1.2])
    fig.update_layout(hovermode="closest")
    return _layout(fig, height=max(260, 34 * len(d) + 60))


def risk_return(table: pd.DataFrame) -> go.Figure:
    colors = {"portfolio": PRIMARY, "benchmark": MUTED, "stock": STOCK}
    sizes = {"portfolio": 18, "benchmark": 18, "stock": 10}
    fig = go.Figure(go.Scatter(
        x=table["volatility"], y=table["cagr"], mode="markers", text=table.index,
        marker=dict(color=[colors[k] for k in table["kind"]], size=[sizes[k] for k in table["kind"]]),
        hovertemplate="<b>%{text}</b><br>Risk %{x:.1%}<br>Return %{y:.1%} a year<extra></extra>"))
    fig.add_hline(y=0, line_color="#888", line_width=1)
    fig.update_xaxes(title="Annual volatility (risk)", tickformat=".0%")
    fig.update_yaxes(title="Annual return (CAGR)", tickformat=".0%")
    fig.update_layout(hovermode="closest")
    return _layout(fig, height=420)


def correlation(returns: pd.DataFrame) -> go.Figure:
    corr = returns.corr().round(2)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale="Blues", zmin=0, zmax=1, aspect="auto")
    fig.update_layout(hovermode="closest")
    return _layout(fig, height=max(360, 40 * len(corr) + 120))
