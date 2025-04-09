import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

st.set_page_config(page_title="Company Enrichment Tool", layout="wide")
st.title("🔍 Company Enrichment with Bing + Selenium")

@st.cache_resource
def init_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver

driver = init_driver()

def bing_search(company):
    driver.get(f"https://www.bing.com/search?q={company}")
    time.sleep(2)
    try:
        result = driver.find_element(By.CSS_SELECTOR, "li.b_algo h2 a")
        return result.get_attribute("href")
    except:
        return ""

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)

    for i, row in df.iterrows():
        company = row["Company Name"]
        domain_url = bing_search(company)
        linkedin_url = bing_search(f"{company} linkedin")

        results.append({
            "Company Name": company,
            "Website URL": domain_url,
            "LinkedIn URL": linkedin_url
        })
        progress.progress((i + 1) / len(df))

    result_df = pd.DataFrame(results)
    st.dataframe(result_df)
    st.download_button("📥 Download", result_df.to_csv(index=False), "results.csv")
