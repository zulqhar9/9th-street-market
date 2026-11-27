"""Shared, cached data loaders, plus a background warm-up so the slowest pages open instantly.

Streamlit's cache is shared by every visitor in the same server process, so loading the data once
in the background means nobody waits for it on their first visit.
"""
import threading
import time

import pandas as pd
import streamlit as st

from analyser import live

NIFTY50 = live.nifty50()
TICKERS = NIFTY50["ticker"].tolist()
WARM_EVERY_SECONDS = 10 * 60


@st.cache_data(ttl=15 * 60, show_spinner=False)
def screener_prices() -> pd.DataFrame:
    return live.price_ranges(TICKERS)


@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def screener_fundamentals() -> pd.DataFrame:
    return live.fundamentals(TICKERS)


def _warm_forever() -> None:
    while True:
        for load in (screener_prices, screener_fundamentals):
            try:
                load()  # cheap when cached; refreshes after the cache expires
            except Exception:  # noqa: BLE001  (Yahoo hiccup: try again next round)
                pass
        time.sleep(WARM_EVERY_SECONDS)


@st.cache_resource(show_spinner=False)
def start_warmup() -> threading.Thread:
    """Start the warm-up thread once per server process (cache_resource makes this a singleton)."""
    thread = threading.Thread(target=_warm_forever, name="data-warmup", daemon=True)
    thread.start()
    return thread
