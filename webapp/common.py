"""Small pieces shared by several pages: news list, time labels, company-name tidying."""
import re

import pandas as pd
import streamlit as st

from analyser import live


def short_name(name: str) -> str:
    """'Larsen & Toubro Ltd.' -> 'Larsen & Toubro'."""
    return re.sub(r"\s+(Ltd\.?|Limited)$", "", name.strip())


def time_ago(ts: pd.Timestamp) -> str:
    minutes = int((pd.Timestamp.now(tz="UTC") - ts).total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 1)} min ago"
    if minutes < 48 * 60:
        return f"{minutes // 60} h ago"
    return ts.tz_convert(live.IST).strftime("%d %b")


def render_news(items: pd.DataFrame, show_company: bool = True) -> None:
    """Headlines as links (plain markdown, never raw HTML from the feed)."""
    if items.empty:
        st.info("No recent headlines found.")
        return
    for row in items.itertuples():
        title = row.title.replace("[", "(").replace("]", ")")  # keep the link markdown intact
        url = row.url.replace(")", "%29").replace(" ", "%20")
        st.markdown(f"**[{title}]({url})**")
        meta = [row.source] + ([row.company] if show_company else []) + [time_ago(row.published)]
        st.caption(" · ".join(meta))
    st.caption("Headlines link to the original publishers.")
