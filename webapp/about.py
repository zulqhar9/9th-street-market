"""About: who built this site, what it shows about their skills, and how to get in touch."""
import streamlit as st

from webapp import style

LINKEDIN = "https://www.linkedin.com/in/zulqhar9/"
GITHUB = "https://github.com/zulqhar9/nain-capital-analytics"

style.header(
    "About",
    "Hi, I'm Zulqhar",
    "I'm a Master of IT student in Melbourne with a background in finance and business consulting. "
    "I built Nain Capital Analytics to bring together two things I enjoy: Indian markets and working with data.",
)

c1, c2, _ = st.columns([1, 1, 2])
c1.link_button("LinkedIn", LINKEDIN, icon=":material/person:", use_container_width=True)
c2.link_button("Code on GitHub", GITHUB, icon=":material/code:", use_container_width=True)

st.subheader("Why I built this")
st.write("I've followed financial markets since 2017 and invested in Indian stocks since 2019. I wanted a "
         "clear, honest way to answer questions like *did my portfolio actually beat the market?* and *how "
         "much risk did it take?*, without spreadsheets or paid tools. This site is the result: live market "
         "data, a stock screener, calculators, and a portfolio analyser, all built from scratch.")

st.subheader("Experience")
st.markdown(
    "- **Project Intern, Reporting & Data Lead** · San Carlo Homes for the Aged, Melbourne (2025)  \n"
    "  Part of a four-person team that replaced paper-based staff appraisals with a digital system on "
    "Microsoft Power Platform (Power Apps, Power Automate, SharePoint).\n"
    "- **Business Consultant** · OneCode.in, freelance (2021 – 2023)\n"
    "- **Personal investor** · Indian equities (2019 – present)"
)

st.subheader("Skills this project uses")
skills = ["Python", "SQL (SQLite, window functions)", "pandas", "Data visualisation (Plotly, matplotlib)",
          "Streamlit", "Financial analysis", "Unit testing", "Git and GitHub"]
st.markdown(" ".join(
    f'<span style="display:inline-block;background:#4A4A4F;color:#F5F5F7;border-radius:999px;'
    f'padding:6px 14px;margin:0 6px 8px 0;font-size:0.9rem">{s}</span>' for s in skills),
    unsafe_allow_html=True)

st.subheader("How this site works")
st.markdown(
    "1. **Data:** prices, company figures and news from Yahoo Finance; stock lists from the NSE's public files.\n"
    "2. **Storage and analysis:** portfolio prices go into SQLite and are queried with SQL; risk and return "
    "measures (CAGR, volatility, drawdown, Sharpe ratio, beta) are calculated in pandas.\n"
    "3. **Website:** Streamlit with Plotly charts, refreshing live data every 60 seconds and caching slower "
    "data to stay fast.\n"
    "4. **Quality:** the calculations are covered by unit tests, and every change goes through GitHub before "
    "it reaches the live site."
)

st.subheader("What I'm looking for")
st.write("Graduate and junior roles in **data analytics, business analysis or process automation** in "
         "Melbourne, where business and technology meet. If you'd like to talk, the best way to reach me "
         "is on LinkedIn.")
st.link_button("Connect on LinkedIn", LINKEDIN, type="primary", icon=":material/person_add:")
st.caption("Nain Capital Analytics is a personal project for information and learning. Nothing on this site "
           "is investment advice.")
