"""Finishing touches the theme file can't express: card shadows, heading spacing, page header."""
import streamlit as st

_CSS = """
<style>
/* Headings: tight tracking, like large display type */
h1, h2, h3 { letter-spacing: -0.022em; }
h1 { line-height: 1.08; }

/* Metric tiles as white cards with a soft shadow instead of a hard border */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: none !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 6px 20px rgba(0,0,0,0.05);
    padding: 1.1rem 1.25rem;
}
[data-testid="stMetricLabel"] p { color: #6E6E73; font-weight: 500; }

/* Responsive columns: wrap to two (then one) per row instead of squeezing the numbers */
[data-testid="stHorizontalBlock"] { flex-wrap: wrap; row-gap: 1rem; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: min(100%, 13.5rem); }

/* Tables, charts and forms sit on white cards too */
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"], [data-testid="stForm"] {
    background: #FFFFFF;
    border-radius: 18px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 6px 20px rgba(0,0,0,0.05);
    padding: 0.5rem;
}
[data-testid="stForm"] { border: none; padding: 1rem 1.25rem; }

/* Pill-style tabs (segmented control look) */
[data-testid="stTabs"] [role="tablist"] {
    gap: 0.25rem; border: none !important; box-shadow: none !important;
    background: #E8E8ED; border-radius: 980px; padding: 0.2rem; width: fit-content; max-width: 100%;
    overflow-x: auto;
}
[data-testid="stTabs"] [role="tablist"]::before, [data-testid="stTabs"] [role="tablist"]::after,
[data-testid="stTab"]::before, [data-testid="stTab"]::after { display: none !important; }
[data-testid="stTab"] {
    border: none !important; border-radius: 980px; padding: 0.3rem 0.95rem; margin: 0 !important;
    background: transparent; box-shadow: none !important; white-space: nowrap;
}
[data-testid="stTab"] p { color: #424245; font-weight: 500; }
[data-testid="stTab"][aria-selected="true"] { background: #FFFFFF; box-shadow: 0 1px 4px rgba(0,0,0,0.12) !important; }
[data-testid="stTab"][aria-selected="true"] p { color: #1D1D1F; }
[data-testid="stTabs"] [role="tablist"] + div[aria-hidden], [data-testid="stTabs"] hr { display: none; }

/* Quieter dividers and captions */
hr { border-color: #E5E5EA !important; }
[data-testid="stCaptionContainer"] { color: #86868B; }

/* Hide the Streamlit footer */
footer { visibility: hidden; }

.eyebrow { color: #0071E3; font-size: 0.82rem; font-weight: 600; letter-spacing: 0.06em;
           text-transform: uppercase; margin-bottom: -0.6rem; }
.lede { color: #6E6E73; font-size: 1.15rem; line-height: 1.5; max-width: 46rem; margin-top: -0.3rem; }
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
