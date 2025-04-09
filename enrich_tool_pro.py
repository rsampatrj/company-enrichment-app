import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote_plus

st.set_page_config(page_title="Bing Company Enrichment Tool", layout="wide")
st.title("🔎 Company Enrichment via Bing")

uploaded_file = st.file_uploader("📤 Upload CSV with 'Company Name'", type="csv")
sample_df = pd.DataFrame({"Company Name": ["Eurostove", "Walford Timber Limited"]})
st.download_button("⬇️ Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def bing_search(query):
    encoded = quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Top result
        link_tag = soup.select_one("li.b_algo h2 a")
        top_link = link_tag['href'] if link_tag else ""

        # Knowledge panel (LinkedIn specific info)
        panel = soup.select_one("div.b_entityTP")
        panel_text = panel.get_text(separator="\n") if panel else ""
        desc = re.search(r'About\n(.*?)\n', panel_text, re.DOTALL)
        employees = re.search(r'Employees\n(.*?)\n', panel_text)
        industry = re.search(r'Industry\n(.*?)\n', panel_text)
        hq = re.search(r'Headquarters\n(.*?)\n', panel_text)

        return {
            "top_link": top_link,
            "description": desc.group(1).strip() if desc else "",
            "employees": employees.group(1).strip() if employees else "",
            "industry": industry.group(1).strip() if industry else "",
            "hq": hq.group(1).strip() if hq else "",
        }
    except Exception as e:
        return {"top_link": "", "description": "", "employees": "", "industry": "", "hq": ""}

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)

    for i, row in df.iterrows():
        name = row["Company Name"]

        site_result = bing_search(f'"{name}"')
        linkedin_result = bing_search(f'"{name}" Linkedin')

        results.append({
            "Input Company Name": name,
            "Matched Domain": site_result["top_link"],
            "Website URL": site_result["top_link"],
            "LinkedIn URL": linkedin_result["top_link"],
            "LinkedIn Description": linkedin_result["description"],
            "Employee Size": linkedin_result["employees"],
            "Industry": linkedin_result["industry"],
            "Headquarters": linkedin_result["hq"]
        })
        progress.progress((i + 1) / len(df))
        time.sleep(0.5)

    result_df = pd.DataFrame(results)
    st.success("✅ Enrichment Completed")
    st.dataframe(result_df)
    st.download_button("📥 Download Enriched CSV", result_df.to_csv(index=False), "bing_enriched_results.csv")
