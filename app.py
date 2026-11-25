"""9th Street Market website.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="9th Street Market", page_icon="📈", layout="wide")

page = st.navigation({
    "Markets": [
        st.Page("webapp/dashboard.py", title="Market Dashboard", icon=":material/space_dashboard:", default=True),
        st.Page("webapp/stock.py", title="Stock Lookup", icon=":material/search:", url_path="stock"),
        st.Page("webapp/compare.py", title="Compare Stocks", icon=":material/compare_arrows:",
                url_path="compare"),
        st.Page("webapp/sectors.py", title="Sectors", icon=":material/pie_chart:", url_path="sectors"),
        st.Page("webapp/screener.py", title="Stock Screener", icon=":material/filter_list:", url_path="screener"),
    ],
    "Tools": [
        st.Page("webapp/sip.py", title="SIP Calculator", icon=":material/savings:", url_path="sip"),
        st.Page("webapp/tax.py", title="Capital Gains Tax", icon=":material/receipt_long:", url_path="tax"),
        st.Page("webapp/whatif.py", title="What If I Invested?", icon=":material/history:", url_path="what-if"),
        st.Page("webapp/portfolio.py", title="Portfolio Analyser", icon=":material/donut_small:",
                url_path="portfolio"),
    ],
    "More": [
        st.Page("webapp/learn.py", title="Learn", icon=":material/school:", url_path="learn"),
        st.Page("webapp/about.py", title="About", icon=":material/person:", url_path="about"),
    ],
})
page.run()
