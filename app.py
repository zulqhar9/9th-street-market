"""Nain Capital Analytics website.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Nain Capital Analytics", page_icon="📈", layout="wide")

page = st.navigation([
    st.Page("webapp/dashboard.py", title="Market Dashboard", icon="📊", default=True),
    st.Page("webapp/portfolio.py", title="Portfolio Analyser", icon="🧮"),
])
page.run()
