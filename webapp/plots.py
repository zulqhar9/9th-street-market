"""Interactive Plotly charts for the website, styled to match the site theme (.streamlit/config.toml)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PRIMARY = "#64D2FF"   # accent blue
MUTED = "#8E8E93"     # benchmark grey
GAIN = "#32D74B"
LOSS = "#FF9A92"
STOCK = "#D1D1D6"     # individual stocks on scatter charts
TEXT = "#F5F5F7"
TEXT_2 = "#C4C4C9"
GRID = "#5A5A60"
CARD = "#4A4A4F"
FONT = "-apple-system, BlinkMacSystemFont, Inter, Segoe UI, sans-serif"


def _layout(fig: go.Figure, height: int = 360, pct_y: bool = False) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=28, b=8),
        legend=dict(orientation="h", y=1.1, x=0, font=dict(color=TEXT_2)),
        hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=TEXT),
        hoverlabel=dict(bgcolor="#1C1C22", bordercolor="#66666C", font=dict(family=FONT, color=TEXT)),
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
    fig.update_xaxes(tickformat=".1%", zeroline=True, zerolinecolor="#66666C")
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
    fig.add_hline(y=1, line_color="#66666C", line_width=1)
    fig.update_yaxes(title="Value of ₹1 invested", tickprefix="₹")
    return _layout(fig, height=400)


def drawdown(dd: pd.Series) -> go.Figure:
    fig = go.Figure(go.Scatter(x=dd.index, y=dd, fill="tozeroy", fillcolor="rgba(255,154,146,0.16)", line=dict(color=LOSS, width=1.5),
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
    fig.add_hline(y=0, line_color="#66666C", line_width=1)
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


def stock_chart(ohlc: pd.DataFrame, candles: bool, intraday: bool, prefix: str = "₹",
                session: tuple[float, float] | None = (9.25, 15.5), decimals: int = 2) -> go.Figure:
    """Price chart for a stock page: candlesticks or a line coloured by the move over the period.

    session is the exchange's trading hours in local hours (9.25 = 9:15 am), used to hide overnight
    and weekend gaps. None for markets that never close, like crypto.
    """
    up = ohlc["Close"].iloc[-1] >= ohlc["Close"].iloc[0]
    if candles:
        trace = go.Candlestick(x=ohlc.index, open=ohlc["Open"], high=ohlc["High"], low=ohlc["Low"],
                               close=ohlc["Close"], increasing_line_color=GAIN, decreasing_line_color=LOSS,
                               increasing_fillcolor=GAIN, decreasing_fillcolor=LOSS, name="Price")
    else:
        color = GAIN if up else LOSS
        trace = go.Scatter(x=ohlc.index, y=ohlc["Close"], mode="lines", name="Price",
                           line=dict(color=color, width=2), fill="tozeroy",
                           fillcolor="rgba(50,215,75,0.08)" if up else "rgba(255,154,146,0.08)",
                           hovertemplate=f"{prefix}%{{y:,.{decimals}f}}<extra></extra>")
    fig = go.Figure(trace)
    lo, hi = ohlc["Low"].min(), ohlc["High"].max()
    pad = (hi - lo) * 0.08 or hi * 0.01
    fig.update_yaxes(range=[lo - pad, hi + pad], tickprefix=prefix)
    fig.update_xaxes(rangeslider_visible=False, tickformat="%H:%M" if intraday else None)
    if session is None:
        pass  # trades 24/7: nothing to hide
    elif intraday:  # hide overnight gaps in multi-day intraday charts
        fig.update_xaxes(rangebreaks=[dict(bounds=[session[1], session[0]], pattern="hour"),
                                      dict(bounds=["sat", "mon"])])
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


def compare_lines(series: dict[str, pd.Series]) -> go.Figure:
    """Percentage change from the start of the period, one line per stock, all starting at 0%."""
    palette = [PRIMARY, "#FF9F0A", "#BF5AF2", GAIN]
    fig = go.Figure([
        go.Scatter(x=s.index, y=s / s.iloc[0] - 1, mode="lines", name=name,
                   line=dict(color=palette[i % 4], width=2),
                   hovertemplate=f"{name}: %{{y:+.1%}}<extra></extra>")
        for i, (name, s) in enumerate(series.items())
    ])
    fig.add_hline(y=0, line_color="#66666C", line_width=1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return _layout(fig, height=420, pct_y=True)


def sector_bars(changes: pd.Series) -> go.Figure:
    """Horizontal bars, one per sector, green for up and red for down, best at the top."""
    s = changes.dropna().sort_values()
    span = max(abs(s.min()), abs(s.max()), 0.005)
    inside = [abs(v) > 0.55 * span for v in s]  # long bars carry their label inside, so it never clips
    fig = go.Figure(go.Bar(x=s, y=s.index, orientation="h",
                           marker_color=[GAIN if v >= 0 else LOSS for v in s],
                           text=[f"{v:+.2%}" for v in s], cliponaxis=False,
                           textposition=["inside" if i else "outside" for i in inside],
                           insidetextanchor="end",
                           insidetextfont=dict(color="#1C1C22"), outsidetextfont=dict(color=TEXT),
                           hovertemplate="%{y}: %{x:+.2%}<extra></extra>"))
    fig.update_xaxes(tickformat=".1%", zeroline=True, zerolinecolor="#66666C", range=[-span * 1.3, span * 1.3])
    fig = _layout(fig, height=max(300, 30 * len(s) + 60))
    fig.update_layout(hovermode="closest", showlegend=False, uniformtext=dict(minsize=11, mode="show"))
    return fig


def sip_growth(yearly: pd.DataFrame) -> go.Figure:
    """Stacked area: money put in (grey) and the growth on top (blue), year by year, in lakhs."""
    invested = yearly["invested"] / 1e5
    gains = (yearly["value"] - yearly["invested"]) / 1e5
    fig = go.Figure([
        go.Scatter(x=yearly["year"], y=invested, name="Invested", stackgroup="one",
                   line=dict(color="#C4C4C9", width=0), fillcolor="rgba(199,199,204,0.40)",
                   hovertemplate="Year %{x}: ₹%{y:.2f} lakh invested<extra></extra>"),
        go.Scatter(x=yearly["year"], y=gains, name="Growth", stackgroup="one",
                   line=dict(color=PRIMARY, width=0), fillcolor="rgba(100,210,255,0.55)",
                   hovertemplate="Year %{x}: ₹%{y:.2f} lakh growth<extra></extra>"),
    ])
    fig.update_xaxes(title="Year", dtick=1 if len(yearly) <= 15 else 5)
    fig.update_yaxes(tickprefix="₹", ticksuffix=" L", title="Lakh rupees")
    fig = _layout(fig, height=380)
    fig.update_layout(margin=dict(l=8, r=24, t=28, b=8))  # room for the last year label
    return fig
