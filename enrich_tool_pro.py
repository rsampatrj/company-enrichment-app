import streamlit as st
import pandas as pd
import requests
import re
from urllib.parse import unquote, urlparse
import whois
import time

st.set_page_config(page_title="Company Enrichment Tool", layout="wide")
st.title("🧠 Company Enrichment Tool (v2) — Google Cache Edition")

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Walford Timber Limited", "Oak Student Letts", "Globescan Incorporated"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

@st.cache_data(show_spinner=False)
def extract_real_url(google_url):
    match = re.search(r"/url\\?q=(https?://[^&]+)", google_url)
    return unquote(match.group(1)) if match else None

@st.cache_data(show_spinner=True)
def search_google_cache(company_name):
    query = company_name.strip().replace(" ", "%20")
    url = f"https://webcache.googleusercontent.com/search?q=cache:{query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            links = re.findall(r'href=["\'](.*?)["\']', resp.text)
            filtered = [l for l in links if 'http' in l and not any(x in l for x in ['google', 'youtube', 'facebook', 'twitter', 'amazon'])]
            final_links = [extract_real_url(l) or l for l in filtered]
            return list(set(final_links))[:3]
        return []
    except Exception as e:
        return []

@st.cache_data(show_spinner=False)
def get_domain_info(domain):
    try:
        w = whois.whois(domain)
        return {
            "WHOIS Created": w.creation_date,
            "WHOIS Expiry": w.expiration_date,
            "WHOIS Registrar": w.registrar,
        }
    except Exception:
        return {
            "WHOIS Created": "",
            "WHOIS Expiry": "",
            "WHOIS Registrar": "",
        }

@st.cache_data(show_spinner=False)
def get_logo(domain):
    return f"https://logo.clearbit.com/{domain}" if domain else ""

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        company = row["Company Name"]
        links = search_google_cache(company)
        website = links[0] if links else ""
        domain = urlparse(website).netloc if website else ""
        info = get_domain_info(domain) if domain else {}
        logo_url = get_logo(domain)

        results.append({
            "Input Company Name": company,
            "Matched Domain": domain,
            "Website URL": website,
            "Confidence Score": len(links) * 10,
            "WHOIS Created": info.get("WHOIS Created"),
            "WHOIS Expiry": info.get("WHOIS Expiry"),
            "WHOIS Registrar": info.get("WHOIS Registrar"),
            "Logo URL": logo_url
        })
        progress.progress((i + 1) / len(df))
        time.sleep(0.2)

    result_df = pd.DataFrame(results)
    st.success("✅ Enrichment Complete")
    st.dataframe(result_df)
    st.download_button("📥 Download Results", result_df.to_csv(index=False), "enriched_results.csv")
