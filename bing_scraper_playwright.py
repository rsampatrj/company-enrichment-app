import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import time

def fetch_bing_results(company):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        url = f"https://www.bing.com/search?q=\"{company}\""
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")

        # Top result
        top_result = soup.find("li", class_="b_algo")
        title = top_result.find("h2").text if top_result else ""
        link = top_result.find("a")["href"] if top_result else ""
        snippet = top_result.find("p").text if top_result and top_result.find("p") else ""

        # Side panel / knowledge panel
        panel = soup.find("div", class_="b_entityTP")
        knowledge = {}
        if panel:
            for block in panel.find_all("div", class_="b_vList"):
                key = block.find("div", class_="b_term")
                val = block.find("div", class_="b_def")
                if key and val:
                    knowledge[key.text.strip()] = val.text.strip()

        score = fuzz.ratio(company.lower(), title.lower() if title else "")
        return {
            "Company": company,
            "Top Result Title": title,
            "Top Result URL": link,
            "Top Result Snippet": snippet,
            "Match Score": score,
            "Status": "Match" if score > 60 else "Low Confidence",
            **knowledge
        }
    except Exception as e:
        return {
            "Company": company,
            "Top Result Title": "ERROR",
            "Top Result URL": "ERROR",
            "Top Result Snippet": str(e),
            "Match Score": 0,
            "Status": "Failed"
        }

def detect_company_column(df):
    for col in df.columns:
        if "company" in col.lower():
            return col
    return df.columns[0]

st.title("🔍 Bing Company Info Scraper (Replit Compatible)")

uploaded = st.file_uploader("Upload a CSV with company names", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    company_col = detect_company_column(df)
    companies = df[company_col].dropna().unique().tolist()

    st.success(f"Found {len(companies)} companies in column: {company_col}")

    if st.button("Start Scraping"):
        results = []
        bar = st.progress(0)

        for i, company in enumerate(companies):
            result = fetch_bing_results(company)
            results.append(result)
            bar.progress((i + 1) / len(companies))
            time.sleep(1)  # avoid rate limiting

        result_df = pd.DataFrame(results)
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name="bing_results.csv", mime="text/csv")
