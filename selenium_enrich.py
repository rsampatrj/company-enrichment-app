import streamlit as st 
import pandas as pd
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

st.set_page_config(page_title="Company Enrichment Tool (Selenium + Bing)", layout="wide")
st.title("🌐 Company Enrichment Tool — Selenium + Bing (Headless Chrome)")

@st.cache_resource
def init_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = uc.Chrome(options=options)
    return driver

def search_bing(driver, query):
    driver.get(f"https://www.bing.com/search?q=%7B%22{query}%22%7D")
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    first_result = soup.select_one("li.b_algo h2 a")
    return first_result["href"] if first_result else ""

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Eurostove", "Walford Timber Limited"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    driver = init_driver()
    results = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        company = row["Company Name"]
        website_url = search_bing(driver, company)
        domain = urlparse(website_url).netloc if website_url else ""
        linkedin_url = search_bing(driver, f"{company} Linkedin")

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
