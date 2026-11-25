"""Finishing touches the theme file can't express: card styling, heading spacing, page header.

Colours follow the "Midnight" theme in .streamlit/config.toml.
"""
import streamlit as st

_CSS = """
<style>
/* Headings: tight tracking, like large display type */
h1, h2, h3 { letter-spacing: -0.022em; }
h1 { line-height: 1.08; }

/* Metric tiles as iOS-style grey cards: no border, generous rounding */
[data-testid="stMetric"] {
    background: #4A4A4F;
    border: none !important;
    border-radius: 22px;
    padding: 1.1rem 1.25rem;
}
[data-testid="stMetricLabel"] p { color: #C4C4C9; font-weight: 500; }
/* Scale big numbers with the window so prices like ₹1,373.90 fit in four cards across */
[data-testid="stMetricValue"] { font-size: clamp(1.4rem, 2vw, 2.25rem) !important; }

/* Responsive columns: 4 across, then a 2x2 grid, then 1 per row (never an odd 3 + 1) */
[data-testid="stHorizontalBlock"] { flex-wrap: wrap; row-gap: 1rem; container-type: inline-size; }
@container (max-width: 50rem) {
    [data-testid="stColumn"] { min-width: calc(50% - 0.5rem) !important; }
}
@container (max-width: 26rem) {
    [data-testid="stColumn"] { min-width: 100% !important; }
}

/* Tables, charts and forms sit on the same cards */
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"], [data-testid="stForm"] {
    background: #4A4A4F;
    border: none;
    border-radius: 22px;
    padding: 0.5rem;
}
[data-testid="stForm"] { padding: 1rem 1.25rem; }

/* Pill-style tabs (segmented control look) */
[data-testid="stTabs"] [role="tablist"] {
    gap: 0.25rem; border: none !important; box-shadow: none !important;
    background: #4A4A4F; border-radius: 980px; padding: 0.2rem; width: fit-content; max-width: 100%;
    overflow-x: auto;
}
[data-testid="stTabs"] [role="tablist"]::before, [data-testid="stTabs"] [role="tablist"]::after,
[data-testid="stTab"]::before, [data-testid="stTab"]::after { display: none !important; }
[data-testid="stTab"] {
    border: none !important; border-radius: 980px; padding: 0.3rem 0.95rem; margin: 0 !important;
    background: transparent; box-shadow: none !important; white-space: nowrap;
}
[data-testid="stTab"] p { color: #C7C7CC; font-weight: 500; }
[data-testid="stTab"][aria-selected="true"] { background: #6A6A70; }
[data-testid="stTab"][aria-selected="true"] p { color: #F5F5F7; }
[data-testid="stTabs"] [role="tablist"] + div[aria-hidden], [data-testid="stTabs"] hr { display: none; }

/* Quieter dividers and captions */
hr { border-color: #5A5A60 !important; }
[data-testid="stCaptionContainer"] { color: #C4C4C9; }

/* Hide the Streamlit footer */
footer { visibility: hidden; }

.eyebrow { color: #64D2FF; font-size: 0.82rem; font-weight: 600; letter-spacing: 0.06em;
           text-transform: uppercase; margin-bottom: -0.6rem; }
.lede { color: #C7C7CC; font-size: 1.15rem; line-height: 1.5; max-width: 46rem; margin-top: -0.3rem; }
</style>
"""


def apply() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def header(eyebrow: str, title: str, lede: str) -> None:
    """Small blue label, large title, and a grey one-paragraph introduction."""
    apply()
    st.markdown(f'<p class="eyebrow">{eyebrow}</p>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<p class="lede">{lede}</p>', unsafe_allow_html=True)
