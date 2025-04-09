
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import time

st.set_page_config(page_title="Company Enrichment Tool — Bing", layout="wide")
st.title("🔍 Company Enrichment Tool — Bing Search (with Knowledge Panel scraping)")

uploaded_file = st.file_uploader("📤 Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Eurostove", "Globescan", "Acme Corp"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

@st.cache_data(show_spinner=False)
def search_bing(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
    response = requests.get(search_url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract first result
    link_tag = soup.select_one("li.b_algo h2 a")
    first_link = link_tag['href'] if link_tag else ""

    # Extract right panel (knowledge panel)
    panel = soup.select_one("div.b_entityTP")
    description = panel.select_one(".b_entityTP .b_snippet") if panel else None
    description_text = description.get_text(strip=True) if description else ""

    info_table = panel.select(".b_vList li") if panel else []
    info_dict = {}
    for item in info_table:
        parts = item.get_text(":", strip=True).split(":", 1)
        if len(parts) == 2:
            key, value = parts
            info_dict[key.strip()] = value.strip()

    return {
        "first_link": first_link,
        "description": description_text,
        "industry": info_dict.get("Industry", ""),
        "size": info_dict.get("Size", ""),
        "headquarters": info_dict.get("Headquarters", "")
    }

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)

    for i, row in df.iterrows():
        company = row["Company Name"]

        # Step 1: Domain Search
        domain_result = search_bing(f'"{company}"')

        # Step 2: LinkedIn Info Search
        linkedin_result = search_bing(f'"{company}" LinkedIn')

        results.append({
            "Input Company Name": company,
            "Matched Domain": urlparse(domain_result["first_link"]).netloc,
            "Website URL": domain_result["first_link"],
            "LinkedIn URL": linkedin_result["first_link"],
            "Company Description": linkedin_result["description"],
            "Employee Size": linkedin_result["size"],
            "Industry": linkedin_result["industry"],
            "Headquarters": linkedin_result["headquarters"]
        })
        progress.progress((i + 1) / len(df))
        time.sleep(0.5)

    result_df = pd.DataFrame(results)
    st.success("✅ Enrichment Complete")
    st.dataframe(result_df)
    st.download_button("📥 Download Results", result_df.to_csv(index=False), "enriched_results.csv")
