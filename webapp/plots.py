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


def heatmap(df: pd.DataFrame) -> go.Figure:
    """Treemap of stocks grouped by sector: tile size = market value, colour = today's % change.

    Expects columns: symbol, name, industry, market_cap, change_pct.
    """
    d = df.dropna(subset=["market_cap", "change_pct"])
    sectors = d.groupby("industry").apply(
        lambda g: pd.Series({"market_cap": g["market_cap"].sum(),
                             "change_pct": (g["change_pct"] * g["market_cap"]).sum() / g["market_cap"].sum()}),
        include_groups=False)
    ids = list(sectors.index) + list(d["symbol"])
    labels = list(sectors.index) + list(d["symbol"])
    parents = [""] * len(sectors) + list(d["industry"])
    values = list(sectors["market_cap"]) + list(d["market_cap"])
    colors = list(sectors["change_pct"]) + list(d["change_pct"])
    names = list(sectors.index) + list(d["name"])
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
        customdata=[[n, c] for n, c in zip(names, colors)],
        marker=dict(colors=colors, colorscale=[[0, LOSS], [0.5, "#2C2C34"], [1, GAIN]], cmid=0,
                    cmin=-0.03, cmax=0.03, line=dict(color=CARD, width=1.5)),
        texttemplate="<b>%{label}</b><br>%{customdata[1]:+.2%}",
        hovertemplate="<b>%{customdata[0]}</b><br>Today %{customdata[1]:+.2%}<extra></extra>",
        textfont=dict(family=FONT, color=TEXT), pathbar=dict(visible=False), tiling=dict(pad=2),
    ))
    fig.update_layout(margin=dict(l=4, r=4, t=4, b=4), height=520, paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT, color=TEXT),
                      hoverlabel=dict(bgcolor="#1C1C22", bordercolor="#3A3A40", font=dict(family=FONT, color=TEXT)))
    return fig


def stock_chart(ohlc: pd.DataFrame, candles: bool, intraday: bool) -> go.Figure:
    """Price chart for a stock page: candlesticks or a line coloured by the move over the period."""
    up = ohlc["Close"].iloc[-1] >= ohlc["Close"].iloc[0]
    if candles:
        trace = go.Candlestick(x=ohlc.index, open=ohlc["Open"], high=ohlc["High"], low=ohlc["Low"],
                               close=ohlc["Close"], increasing_line_color=GAIN, decreasing_line_color=LOSS,
                               increasing_fillcolor=GAIN, decreasing_fillcolor=LOSS, name="Price")
    else:
        color = GAIN if up else LOSS
        trace = go.Scatter(x=ohlc.index, y=ohlc["Close"], mode="lines", name="Price",
                           line=dict(color=color, width=2), fill="tozeroy",
                           fillcolor="rgba(48,209,88,0.08)" if up else "rgba(255,69,58,0.08)",
                           hovertemplate="₹%{y:,.2f}<extra></extra>")
    fig = go.Figure(trace)
    lo, hi = ohlc["Low"].min(), ohlc["High"].max()
    pad = (hi - lo) * 0.08 or hi * 0.01
    fig.update_yaxes(range=[lo - pad, hi + pad], tickprefix="₹")
    fig.update_xaxes(rangeslider_visible=False, tickformat="%H:%M" if intraday else None)
    if intraday:  # hide overnight gaps in multi-day intraday charts
        fig.update_xaxes(rangebreaks=[dict(bounds=[15.5, 9.25], pattern="hour"), dict(bounds=["sat", "mon"])])
    else:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig = _layout(fig, height=420)
    fig.update_layout(showlegend=False, hovermode="x unified")
    return fig


def value_lines(series: dict[str, pd.Series]) -> go.Figure:
    """Value of each investment over time, one line per asset."""
    palette = [PRIMARY, "#FF9F0A", "#BF5AF2", GAIN]
    fig = go.Figure([
        go.Scatter(x=s.index, y=s, mode="lines", name=name, line=dict(color=palette[i % 4], width=2),
                   hovertemplate=f"{name}: ₹%{{y:,.0f}}<extra></extra>")
        for i, (name, s) in enumerate(series.items())
    ])
    fig.update_yaxes(tickprefix="₹")
    return _layout(fig, height=420)
