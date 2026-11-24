"""Interactive Plotly charts for the website, styled to match the site theme (.streamlit/config.toml)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PRIMARY = "#0A84FF"   # accent blue
MUTED = "#636366"     # benchmark grey
GAIN = "#30D158"
LOSS = "#FF453A"
STOCK = "#D1D1D6"     # individual stocks on scatter charts
TEXT = "#F5F5F7"
TEXT_2 = "#8E8E93"
GRID = "#26262C"
CARD = "#17171C"
FONT = "-apple-system, BlinkMacSystemFont, Inter, Segoe UI, sans-serif"


def _layout(fig: go.Figure, height: int = 360, pct_y: bool = False) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=28, b=8),
        legend=dict(orientation="h", y=1.1, x=0, font=dict(color=TEXT_2)),
        hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=TEXT),
        hoverlabel=dict(bgcolor="#1C1C22", bordercolor="#3A3A40", font=dict(family=FONT, color=TEXT)),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=TEXT_2))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=TEXT_2))
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
    fig.update_xaxes(tickformat=".1%", zeroline=True, zerolinecolor="#3A3A40")
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
    fig.add_hline(y=1, line_color="#3A3A40", line_width=1)
    fig.update_yaxes(title="Value of ₹1 invested", tickprefix="₹")
    return _layout(fig, height=400)


def drawdown(dd: pd.Series) -> go.Figure:
    fig = go.Figure(go.Scatter(x=dd.index, y=dd, fill="tozeroy", fillcolor="rgba(255,69,58,0.16)", line=dict(color=LOSS, width=1.5),
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
    fig.add_hline(y=0, line_color="#3A3A40", line_width=1)
    fig.update_xaxes(title="Annual volatility (risk)", tickformat=".0%")
    fig.update_yaxes(title="Annual return (CAGR)", tickformat=".0%")
    fig.update_layout(hovermode="closest")
    return _layout(fig, height=420)


def correlation(returns: pd.DataFrame) -> go.Figure:
    corr = returns.corr().round(2)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale=[[0, CARD], [1, PRIMARY]], zmin=0, zmax=1, aspect="auto")
    fig.update_traces(textfont=dict(color=TEXT))
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    fig.update_layout(hovermode="closest")
    return _layout(fig, height=max(360, 40 * len(corr) + 120))
