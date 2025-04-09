import streamlit as st
import pandas as pd
import requests
import re
import time
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

st.set_page_config(page_title="Company Enrichment Tool (Hybrid Cache)", layout="wide")
st.title("🧠 Company Enrichment Tool — Google Cache Hybrid")

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Walford Timber Limited", "Oak Student Letts", "Globescan Incorporated"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

@st.cache_data(show_spinner=False)
def search_google(company_name, site_filter=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    query = f"{company_name}"
    if site_filter:
        query += f" site:{site_filter}"
    url = f"https://www.google.com/search?q={query}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/url?q=" in href:
                clean_url = re.findall(r"/url\\?q=(.*?)&", href)
                if clean_url:
                    decoded_url = unquote(clean_url[0])
                    if not any(skip in decoded_url for skip in ["support.google.com", "policies.google.com"]):
                        links.append(decoded_url)
        return links[0] if links else ""
    except:
        return ""

@st.cache_data(show_spinner=False)
def fetch_clearbit(company_name):
    try:
        resp = requests.get(f"https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}", timeout=10)
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
        domain, logo = fetch_clearbit(company)

        if not domain:
            website_url = search_google(company)
            domain = urlparse(website_url).netloc
        else:
            website_url = f"https://{domain}"

        linkedin_url = search_google(company, site_filter="linkedin.com")

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
