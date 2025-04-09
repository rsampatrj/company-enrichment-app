import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent

st.set_page_config(page_title="Bing Company Enrichment", layout="wide")
st.title("🔍 Bing Company Enrichment Tool with Selenium")

uploaded_file = st.file_uploader("Upload CSV with Company Names", type=["csv"])
sample_df = pd.DataFrame({"Company Name": ["Eurostove", "Macflex International Ltd"]})
st.download_button("⬇️ Download Sample CSV", sample_df.to_csv(index=False), "sample_companies.csv")

def get_driver(user_agent):
    try:
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"❌ Failed to initialize ChromeDriver: {e}")
        return None

def search_bing(driver, company_name, for_linkedin=False):
    query = f'"{company_name} Linkedin"' if for_linkedin else f'"{company_name}"'
    search_url = f"https://www.bing.com/search?q={query}"
    try:
        driver.get(search_url)
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.b_algo h2 a")))
        try:
            link_element = driver.find_element(By.CSS_SELECTOR, "li.b_algo h2 a")
            url = link_element.get_attribute("href")
        except:
            url = ""
        right_panel_data = {"Description": "", "Employee Size": "", "Industry": "", "Headquarters": ""}
        try:
            panel = driver.find_element(By.ID, "b_context")
            panel_text = panel.text
            for line in panel_text.split("\n"):
                if "Headquarters" in line:
                    right_panel_data["Headquarters"] = line.split(":")[-1].strip()
                elif "Industry" in line:
                    right_panel_data["Industry"] = line.split(":")[-1].strip()
                elif "Employees" in line:
                    right_panel_data["Employee Size"] = line.split(":")[-1].strip()
                elif not right_panel_data["Description"]:
                    right_panel_data["Description"] = line.strip()
        except:
            pass
        return url, right_panel_data
    except Exception as e:
        st.warning(f"⚠️ Failed to get results for {company_name}: {e}")
        return "", {"Description": "", "Employee Size": "", "Industry": "", "Headquarters": ""}

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    results = []
    progress = st.progress(0)
    ua = UserAgent()
    user_agent = ua.random
    driver = get_driver(user_agent)
    if driver:
        for i, row in df.iterrows():
            company = row["Company Name"]
            if i % 5 == 0:
                st.write(f"🔎 Searching: {company}")
            website_url, _ = search_bing(driver, company)
            linkedin_url, meta = search_bing(driver, company, for_linkedin=True)
            results.append({
                "Company Name": company,
                "Website URL": website_url,
                "LinkedIn URL": linkedin_url,
                "LinkedIn Description": meta["Description"],
                "Employee Size": meta["Employee Size"],
                "Industry": meta["Industry"],
                "HQ Location": meta["Headquarters"],
            })
            progress.progress((i + 1) / len(df))
        driver.quit()
        result_df = pd.DataFrame(results)
        st.success("✅ Enrichment Complete")
        st.dataframe(result_df)
        st.download_button("📥 Download Results", result_df.to_csv(index=False), "enriched_results.csv")
