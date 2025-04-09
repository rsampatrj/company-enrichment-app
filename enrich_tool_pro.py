import streamlit as st 
import pandas as pd
import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote

st.set_page_config(page_title="Company Enrichment Tool (v3)", layout="wide")
st.title("🌐 Company Enrichment Tool (v3) — Brave Search")

uploaded_file = st.file_uploader("📁 Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Walford Timber Limited", "Oak Student Letts", "Globescan Incorporated"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

@st.cache
def search_brave(company_name):
    encoded_query = quote(f'"{company_name}"')
    url = f"https://search.brave.com/search?q={encoded_query}&source=web"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        result_link = soup.select_one("a.result-header")
        return result_link['href'] if result_link else ""
    except:
        return ""

@st.cache
def clearbit_autocomplete(company_name):
    try:
        url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data:
            return data[0].get("domain", ""), data[0].get("logo", "")
        return "", ""
    except:
        return "", ""

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        company = row["Company Name"]
        domain, logo = clearbit_autocomplete(company)

        website_url = search_brave(company)
        if not domain:
            domain = urlparse(website_url).netloc
        if not website_url and domain:
            website_url = f"https://{domain}"

        linkedin_url = search_brave(f"{company} Linkedin")

        results.append({
            "Input Company Name": company,
            "Matched Domain": domain,
            "Website URL": website_url,
            "LinkedIn URL": linkedin_url,
            "Logo URL": logo
        })
        progress.progress((i + 1) / len(df))
        time.sleep(0.3)

    result_df = pd.DataFrame(results)
    st.success("✅ Enrichment Complete")
    st.dataframe(result_df)
    st.download_button("📥 Download Results", result_df.to_csv(index=False), "enriched_results.csv")
