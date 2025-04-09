import streamlit as st
import pandas as pd
import requests
import re
import time
from urllib.parse import urlparse

st.set_page_config(page_title="Company Enrichment Tool (v3)", layout="wide")
st.title("🌐 Company Enrichment Tool (v3) — DuckDuckGo + Clearbit")

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Walford Timber Limited", "Oak Student Letts", "Globescan Incorporated"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

@st.cache_data(show_spinner=True)
def search_duckduckgo(company_name, site_filter=None):
    query = company_name
    if site_filter:
        query += f" site:{site_filter}"
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        resp = requests.post(url, headers=headers, timeout=10)
        links = re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)"', resp.text)
        return links[0] if links else ""
    except:
        return ""

@st.cache_data(show_spinner=False)
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

        if not domain:
            website_url = search_duckduckgo(company)
            domain = urlparse(website_url).netloc
        else:
            website_url = f"https://{domain}"

        linkedin_url = search_duckduckgo(company, site_filter="linkedin.com")

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
