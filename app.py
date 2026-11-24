"""Nain Capital Analytics website.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Nain Capital Analytics", page_icon="📈", layout="wide")

page = st.navigation([
    st.Page("webapp/dashboard.py", title="Market Dashboard", icon=":material/space_dashboard:", default=True),
    st.Page("webapp/stock.py", title="Stock Lookup", icon=":material/search:", url_path="stock"),
    st.Page("webapp/whatif.py", title="What If I Invested?", icon=":material/savings:", url_path="what-if"),
    st.Page("webapp/portfolio.py", title="Portfolio Analyser", icon=":material/donut_small:", url_path="portfolio"),
])
page.run()
