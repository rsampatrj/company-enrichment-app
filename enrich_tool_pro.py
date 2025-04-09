import streamlit as st
import pandas as pd
import requests
import re
import time
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

st.set_page_config(page_title="Company Enrichment Tool (Brave Search Only)", layout="wide")
st.title("🦁 Company Enrichment Tool — Brave Search Only (Smart Matching)")

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Walford Timber Limited", "Oak Student Letts", "Globescan Incorporated"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

def is_similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def clean_company_name(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())

def smart_brave_search(company_name, site_filter=None, max_results=10):
    headers = {"User-Agent": "Mozilla/5.0"}
    query = f"{company_name}"
    if site_filter:
        query += f" site:{site_filter}"
    url = f"https://search.brave.com/search?q={query}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        company_clean = clean_company_name(company_name)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text()
            if not href.startswith("http"):
                continue
            parsed = urlparse(href)
            domain = parsed.netloc
            if any(skip in domain for skip in ["brave.com", "reddit.com", "youtube.com", "torproject.org"]):
                continue
            domain_clean = clean_company_name(domain.split(".")[0])
            score = 0
            if company_clean in domain_clean:
                score += 1.0
            score += is_similar(company_clean, domain_clean)
            score += is_similar(company_name, text)
            results.append((score, href))
            if len(results) >= max_results:
                break
        if results:
            results.sort(reverse=True)
            return results[0][1]  # return URL with best score
        return ""
    except:
        return ""

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        company = row["Company Name"]

        website_url = smart_brave_search(company)
        domain = urlparse(website_url).netloc if website_url else ""

        linkedin_url = smart_brave_search(company, site_filter="linkedin.com")

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
