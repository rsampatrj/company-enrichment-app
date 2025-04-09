import streamlit as st
import pandas as pd
import requests
import re
import time
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

st.set_page_config(page_title="Company Enrichment Tool (Brave Search Only)", layout="wide")
st.title("🦁 Company Enrichment Tool — Brave Search Only")

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Walford Timber Limited", "Oak Student Letts", "Globescan Incorporated"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

@st.cache_data(show_spinner=False)
def search_brave(company_name, site_filter=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    query = f"{company_name}"
    if site_filter:
        query += f" site:{site_filter}"
    url = f"https://search.brave.com/search?q={query}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and not any(skip in href for skip in ["brave.com", "youtube.com"]):
                links.append(href)
        return links[0] if links else ""
    except:
        return ""

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        company = row["Company Name"]

        website_url = search_brave(company)
        domain = urlparse(website_url).netloc if website_url else ""

        linkedin_url = search_brave(company, site_filter="linkedin.com")

        results.append({
            "Input Company Name": company,
            "Matched Domain": domain,
            "Website URL": website_url,
            "LinkedIn URL": linkedin_url
        })
        progress.progress((i + 1) / len(df))
        time.sleep(0.3)

    result_df = pd.DataFrame(results)
    st.success("✅ Enrichment Complete")
    st.dataframe(result_df)
    st.download_button("📥 Download Results", result_df.to_csv(index=False), "enriched_results.csv")
