import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import time
import re
import io

# Detect company column
def detect_company_column(df):
    for col in df.columns:
        if "company" in col.lower():
            return col
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, str)).mean() > 0.7:
            return col
    return df.columns[0]

# Scraper using Playwright
def scrape_bing_playwright(company, retries=3):
    for attempt in range(retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                query = f"https://www.bing.com/search?q=%22{company}%22"
                page.goto(query, timeout=15000)
                page.wait_for_timeout(2000)

                soup = BeautifulSoup(page.content(), "html.parser")
                browser.close()

                # Top result
                top = soup.find("li", class_="b_algo")
                top_title = top.find("h2").text.strip() if top else ""
                top_url = top.find("a")["href"] if top else ""
                top_snippet = top.find("p").text.strip() if top and top.find("p") else ""

                # Right panel
                panel = soup.find("div", class_="b_entityTP")
                summary_data = {}
                if panel:
                    for row in panel.find_all("div", class_="b_vList"):
                        label = row.find("div", class_="b_term") or row.find("div", class_="b_snippetTitle")
                        value = row.find("div", class_="b_def") or row.find("div", class_="b_snippetValue")
                        if label and value:
                            summary_data[label.text.strip()] = value.text.strip()

                return {
                    "Company": company,
                    "Top Result Title": top_title,
                    "Top Result URL": top_url,
                    "Top Result Snippet": top_snippet,
                    **summary_data
                }

        except PlaywrightTimeout as e:
            time.sleep(2)
            if attempt == retries - 1:
                return {
                    "Company": company,
                    "Top Result Title": "TIMEOUT",
                    "Top Result URL": "",
                    "Top Result Snippet": str(e)
                }

# Streamlit App
st.title("🚀 Fast Company Info Scraper (Playwright + Bing)")

uploaded_file = st.file_uploader("Upload CSV with company names", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    company_col = detect_company_column(df)
    companies = df[company_col].dropna().unique().tolist()
    st.success(f"Detected company column: **{company_col}** with {len(companies)} entries")

    if st.button("Start Scraping"):
        results = []
        progress_bar = st.progress(0)
        status = st.empty()

        for i, company in enumerate(companies):
            status.text(f"Scraping: {company} ({i+1}/{len(companies)})")
            result = scrape_bing_playwright(company)
            results.append(result)
            progress_bar.progress((i + 1) / len(companies))

        result_df = pd.DataFrame(results)
        st.success("✅ All done!")
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name="bing_results.csv", mime="text/csv")
