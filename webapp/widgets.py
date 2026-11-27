"""iPhone-style widget board for the dashboard: big NIFTY tile, gold, silver, breadth ring, top mover.

All HTML is built here from numbers and our own stock list, so nothing from outside feeds is injected.
"""
from __future__ import annotations

from html import escape

import pandas as pd

UP, DOWN, FLAT = "#32D74B", "#FF9A92", "#C4C4C9"
TEXT, MUTED, CARD, RING_BG = "#F5F5F7", "#C4C4C9", "#4A4A4F", "#6B3B3B"


def indian(x: float, decimals: int = 0) -> str:
    """Indian digit grouping: 108155 -> '1,08,155'; 25349.65 -> '25,349.65'."""
    neg, x = x < 0, abs(x)
    whole, frac = f"{x:.{decimals}f}".split(".") if decimals else (f"{x:.0f}", "")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return ("−" if neg else "") + whole + (f".{frac}" if frac else "")


def _signed(x: float, decimals: int = 2) -> str:
    return ("+" if x > 0 else "−" if x < 0 else "") + indian(abs(x), decimals)


def pct(x: float) -> str:
    """+1.53% / −1.75% with a true minus sign, matching the point changes."""
    return f"{x:+.2%}".replace("-", "−")


def _colour(change: float) -> str:
    return UP if change > 0 else DOWN if change < 0 else FLAT


def sparkline(series: pd.Series, width: int, height: int, colour: str | None = None) -> str:
    """Smooth SVG line of a price series. Green if it ended higher than it started, unless `colour` is given."""
    s = series.dropna()
    if len(s) < 2:
        return ""
    lo, hi = float(s.min()), float(s.max())
    span = (hi - lo) or 1.0
    step = width / (len(s) - 1)
    pts = " ".join(f"{i * step:.1f},{height - 3 - (v - lo) / span * (height - 6):.1f}" for i, v in enumerate(s))
    colour = colour or (UP if s.iloc[-1] >= s.iloc[0] else DOWN)
    return (f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
            f'aria-hidden="true"><polyline fill="none" stroke="{colour}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" points="{pts}"/></svg>')


def ring(fraction: float, size: int = 64) -> str:
    """Activity-ring style gauge: green arc for the share of stocks that rose."""
    r = size / 2 - 7
    circ = 2 * 3.14159 * r
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" aria-hidden="true">'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{RING_BG}" stroke-width="9"/>'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{UP}" stroke-width="9" '
            f'stroke-linecap="round" stroke-dasharray="{fraction * circ:.1f} {circ:.1f}" '
            f'transform="rotate(-90 {size/2} {size/2})"/></svg>')


CSS = """
<style>
.wb { container-type: inline-size; margin: 0.25rem 0 0.5rem; }
.wb-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.wb-tile { background: #4A4A4F; border-radius: 22px; padding: 16px 18px; min-width: 0;
           display: flex; flex-direction: column; justify-content: space-between; min-height: 118px; }
.wb-big { grid-column: span 2; grid-row: span 2; min-height: 248px; }
.wb-label { color: #C4C4C9; font-size: 0.85rem; font-weight: 500; display: flex; justify-content: space-between;
            align-items: center; gap: 8px; }
.wb-value { color: #F5F5F7; font-size: 1.55rem; font-weight: 600; letter-spacing: -0.02em; margin-top: 6px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.wb-big .wb-value { font-size: 2.6rem; margin-top: 4px; }
.wb-change { font-size: 0.9rem; font-weight: 500; margin-top: 2px; white-space: nowrap; overflow: hidden;
              text-overflow: ellipsis; }
.wb-big .wb-change { font-size: 1.05rem; }
.wb-spark { margin-top: 10px; }
.wb-pill { font-size: 0.75rem; font-weight: 600; padding: 3px 9px; border-radius: 999px; white-space: nowrap; }
.wb-foot { color: #C4C4C9; font-size: 0.8rem; margin-top: 8px; }
.wb-ring { display: flex; align-items: center; gap: 14px; }
@container (max-width: 44rem) {
  .wb-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .wb-big { grid-row: span 1; min-height: 210px; }
  .wb-big .wb-value { font-size: 2.2rem; }
}
</style>
"""


def board(*, nifty: pd.Series, nifty_intraday: pd.Series, status: str, is_open: bool, session: str,
          gold_now: float, gold_prev: float, silver_now: float, silver_prev: float, usd_inr: float,
          up: int, total: int, top_symbol: str, top_name: str, top_change: float) -> str:
    """HTML for the whole board. Changes are fractions (0.0153 = +1.53%)."""
    pill_bg, pill_fg = ("rgba(50,215,75,.16)", UP) if is_open else ("#5A5A60", MUTED)
    pill_text = "Open" if is_open else ("Holiday" if "holiday" in status else "Closed")
    g_chg, s_chg = gold_now / gold_prev - 1, silver_now / silver_prev - 1

    big = f"""
<div class="wb-tile wb-big">
  <div>
    <div class="wb-label"><span>NIFTY 50</span>
      <span class="wb-pill" style="background:{pill_bg};color:{pill_fg}">● {pill_text}</span></div>
    <div class="wb-value">{indian(nifty['price'], 2)}</div>
    <div class="wb-change" style="color:{_colour(nifty['change'])}">{_signed(nifty['change'])} · {pct(nifty['change_pct'])}</div>
  </div>
  <div class="wb-spark">{sparkline(nifty_intraday, 300, 90, colour=_colour(nifty['change']))}</div>
  <div class="wb-foot">{escape(session)} · US$1 = ₹{usd_inr:.2f}</div>
</div>"""

    def small(label: str, value: str, change: float) -> str:
        return f"""
<div class="wb-tile"><div class="wb-label">{label}</div>
  <div><div class="wb-value">{value}</div>
  <div class="wb-change" style="color:{_colour(change)}">{pct(change)}</div></div></div>"""

    breadth = f"""
<div class="wb-tile"><div class="wb-label">Market breadth</div>
  <div class="wb-ring">{ring(up / total if total else 0)}
    <div><div class="wb-value" style="margin-top:0">{up} / {total}</div>
    <div class="wb-foot" style="margin-top:0">stocks up today</div></div></div></div>"""

    mover = f"""
<div class="wb-tile"><div class="wb-label">Top mover</div>
  <div><div class="wb-value">{escape(top_symbol)}</div>
  <div class="wb-change" style="color:{_colour(top_change)}">{pct(top_change)}
    <span style="color:{MUTED};font-weight:400"> · {escape(top_name)}</span></div></div></div>"""

    return (CSS + '<div class="wb"><div class="wb-grid">' + big
            + small("Gold · 10 g", "₹" + indian(gold_now), g_chg)
            + small("Silver · 1 kg", "₹" + indian(silver_now), s_chg)
            + breadth + mover + "</div></div>")


LIST_CSS = """
<style>
.sl { columns: 2 24rem; column-gap: 28px; margin-top: 0.25rem; }
.sl-row { break-inside: avoid; display: grid; grid-template-columns: minmax(0, 1fr) 76px 104px; align-items: center;
          gap: 12px; padding: 11px 6px; border-bottom: 0.5px solid #5A5A60; text-decoration: none !important;
          border-radius: 12px; transition: background 0.15s ease; }
.sl-row:hover { background: #4A4A4F; }
.sl-sym { color: #F5F5F7; font-size: 0.98rem; font-weight: 600; letter-spacing: -0.01em; }
.sl-name { color: #C4C4C9; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sl-price { color: #F5F5F7; font-size: 0.92rem; text-align: right; font-variant-numeric: tabular-nums; }
.sl-pill { display: block; margin: 4px 0 0 auto; width: 78px; text-align: center; color: #000; font-size: 0.82rem;
           font-weight: 600; padding: 3px 0; border-radius: 7px; font-variant-numeric: tabular-nums; }
.sl-sector { column-span: all; color: #C4C4C9; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.05em;
             text-transform: uppercase; margin: 18px 6px 2px; }
</style>
"""


def money(x: float, currency: str = "₹", decimals: int = 2) -> str:
    """₹ amounts use Indian grouping (1,08,155.00); $ amounts use international grouping (108,155.00)."""
    return f"₹{indian(x, decimals)}" if currency == "₹" else f"{currency}{x:,.{decimals}f}"


def _row(symbol: str, name: str, price: float, change_pct: float, intraday: pd.Series | None,
         currency: str = "₹", link: str = "stock?symbol=") -> str:
    pill = UP if change_pct > 0 else DOWN if change_pct < 0 else "#8E8E93"
    # Like Apple Stocks: the line takes the same colour as the day's change vs yesterday's close.
    spark = sparkline(intraday, 76, 30, colour=pill if change_pct else None) if intraday is not None else ""
    return (f'<a class="sl-row" href="{escape(link + symbol)}" target="_self">'
            f'<div style="min-width:0"><div class="sl-sym">{escape(symbol)}</div>'
            f'<div class="sl-name">{escape(name)}</div></div>'
            f'<div>{spark}</div>'
            f'<div><div class="sl-price">{money(price, currency)}</div>'
            f'<span class="sl-pill" style="background:{pill}">{pct(change_pct)}</span></div></a>')


def stock_list(stocks: pd.DataFrame, intraday: pd.DataFrame | dict, order: str, currency: str = "₹",
               link: str = "stock?symbol=") -> str:
    """Apple Stocks-style list. `stocks` is indexed by ticker with symbol, short, industry, price, change_pct.

    order: "gainers", "losers", "az" or "sector" (sector adds small section headings).
    """
    if order == "losers":
        d = stocks.sort_values("change_pct")
    elif order == "az":
        d = stocks.sort_values("symbol")
    elif order == "sector":
        d = stocks.sort_values(["industry", "change_pct"], ascending=[True, False])
    else:
        d = stocks.sort_values("change_pct", ascending=False)

    parts, current = [], None
    for ticker, r in d.iterrows():
        if order == "sector" and r["industry"] != current:
            current = r["industry"]
            parts.append(f'<div class="sl-sector">{escape(current)}</div>')
        series = intraday[ticker] if ticker in intraday else None
        parts.append(_row(r["symbol"], r["short"], r["price"], r["change_pct"], series, currency, link))
    return LIST_CSS + '<div class="sl">' + "".join(parts) + "</div>"


def index_board(tiles: list[dict]) -> str:
    """Grid of index tiles. Each dict: name, place, price, change, change_pct, state, session (Series), foot."""
    pills = {"open": ("rgba(50,215,75,.16)", UP), "lunch": ("rgba(255,214,10,.16)", "#FFD60A")}
    parts = []
    for t in tiles:
        bg, fg = pills.get(t["state"], ("#5A5A60", MUTED))
        colour = _colour(t["change"])
        parts.append(f"""
<div class="wb-tile">
  <div class="wb-label"><span>{escape(t['name'])}</span>
    <span class="wb-pill" style="background:{bg};color:{fg}">● {escape(t['label'])}</span></div>
  <div><div class="wb-value">{escape(t.get('price_text') or f"{t['price']:,.2f}")}</div>
    <div class="wb-change" style="color:{colour}">{escape(t.get('change_text') or ('+' if t['change'] > 0 else '−' if t['change'] < 0 else '') + f"{abs(t['change']):,.2f} · ")}{pct(t['change_pct'])}</div></div>
  <div class="wb-spark">{sparkline(t['session'], 200, 44, colour=colour) if t.get('session') is not None else ''}</div>
  <div class="wb-foot" style="margin-top:4px">{escape(t['foot'])}</div>
</div>""")
    return CSS + '<div class="wb"><div class="wb-grid">' + "".join(parts) + "</div></div>"
