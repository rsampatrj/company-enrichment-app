import streamlit as st
import pandas as pd
import requests
import re
import time
from urllib.parse import urlparse

st.set_page_config(page_title="Company Enrichment Tool (Bing Edition)", layout="wide")
st.title("🔎 Company Enrichment Tool (Bing Edition)")

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Walford Timber Limited", "Oak Student Letts", "Globescan Incorporated"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

@st.cache_data(show_spinner=True)
def search_bing(company_name, site_filter=None):
    query = company_name
    if site_filter:
        query += f" site:{site_filter}"
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.bing.com/search?q={query}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        links = re.findall(r'<a href="(https?://[^"]+)"', resp.text)
        clean_links = [l for l in links if not l.startswith("https://www.bing.com") and not "bing.com" in urlparse(l).netloc]
        return clean_links[0] if clean_links else ""
    except:
        return ""

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        company = row["Company Name"]

        website_url = search_bing(company)
        domain = urlparse(website_url).netloc if website_url else ""

        linkedin_url = search_bing(company, site_filter="linkedin.com")

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
    st.download_button("📥 Download Results", result_df.to_csv(index=False), "enriched_results_bing.csv")
