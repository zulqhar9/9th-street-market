"""Finishing touches the theme file can't express: card styling, heading spacing, page header.

Colours follow the "Midnight" theme in .streamlit/config.toml.
"""
import streamlit as st

_CSS = """
<style>
/* Headings: tight tracking, like large display type */
h1, h2, h3 { letter-spacing: -0.022em; }
h1 { line-height: 1.08; }

/* Metric tiles as soft grey cards with a hairline edge (shadows don't read on dark) */
[data-testid="stMetric"] {
    background: #17171C;
    border: 0.5px solid #2A2A31 !important;
    padding: 1.1rem 1.25rem;
}
[data-testid="stMetricLabel"] p { color: #8E8E93; font-weight: 500; }

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
    background: #17171C;
    border: 0.5px solid #2A2A31;
    border-radius: 18px;
    padding: 0.5rem;
}
[data-testid="stForm"] { padding: 1rem 1.25rem; }

/* Pill-style tabs (segmented control look) */
[data-testid="stTabs"] [role="tablist"] {
    gap: 0.25rem; border: none !important; box-shadow: none !important;
    background: #1C1C22; border-radius: 980px; padding: 0.2rem; width: fit-content; max-width: 100%;
    overflow-x: auto;
}
[data-testid="stTabs"] [role="tablist"]::before, [data-testid="stTabs"] [role="tablist"]::after,
[data-testid="stTab"]::before, [data-testid="stTab"]::after { display: none !important; }
[data-testid="stTab"] {
    border: none !important; border-radius: 980px; padding: 0.3rem 0.95rem; margin: 0 !important;
    background: transparent; box-shadow: none !important; white-space: nowrap;
}
[data-testid="stTab"] p { color: #A1A1A6; font-weight: 500; }
[data-testid="stTab"][aria-selected="true"] { background: #2C2C34; }
[data-testid="stTab"][aria-selected="true"] p { color: #F5F5F7; }
[data-testid="stTabs"] [role="tablist"] + div[aria-hidden], [data-testid="stTabs"] hr { display: none; }

/* Quieter dividers and captions */
hr { border-color: #2A2A31 !important; }
[data-testid="stCaptionContainer"] { color: #8E8E93; }

/* Hide the Streamlit footer */
footer { visibility: hidden; }

.eyebrow { color: #0A84FF; font-size: 0.82rem; font-weight: 600; letter-spacing: 0.06em;
           text-transform: uppercase; margin-bottom: -0.6rem; }
.lede { color: #A1A1A6; font-size: 1.15rem; line-height: 1.5; max-width: 46rem; margin-top: -0.3rem; }
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
