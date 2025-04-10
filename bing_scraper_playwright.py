import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import os, time, shutil

# 1. Setup Headless Browser
def init_driver():
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

# 2. Fuzzy match against title/snippet
def best_match(text, targets):
    scores = [(target, fuzz.ratio(text.lower(), target.lower())) for target in targets]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[0][1] if scores else 0

# 3. Scrape Bing Search Results
def scrape_bing(company, retries=3):
    for attempt in range(retries):
        try:
            driver = init_driver()
            driver.set_page_load_timeout(15)
            driver.get(f"https://www.bing.com/search?q=%22{company}%22")
            time.sleep(2)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            driver.quit()

            # Top organic result
            top = soup.find("li", class_="b_algo")
            top_title = top.find("h2").text.strip() if top else ""
            top_url = top.find("a")["href"] if top else ""
            top_snippet = top.find("p").text.strip() if top and top.find("p") else ""

            # Knowledge panel (right side)
            panel = soup.find("div", class_="b_entityTP")
            summary_data = {}
            if panel:
                for row in panel.find_all("div", class_="b_vList"):
                    label = row.find("div", class_="b_term") or row.find("div", class_="b_snippetTitle")
                    value = row.find("div", class_="b_def") or row.find("div", class_="b_snippetValue")
                    if label and value:
                        summary_data[label.text.strip()] = value.text.strip()

            match_score = best_match(company, [top_title, top_snippet])
            status = "Match" if match_score > 60 else "Low confidence"

            # Save HTML snapshot
            os.makedirs("html_snapshots", exist_ok=True)
            with open(f"html_snapshots/{company.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
                f.write(page_source)

            return {
                "Company": company,
                "Top Result Title": top_title,
                "Top Result URL": top_url,
                "Top Result Snippet": top_snippet,
                "Match Score": match_score,
                "Status": status,
                **summary_data
            }

        except (TimeoutException, WebDriverException) as e:
            time.sleep(1)
            if attempt == retries - 1:
                return {
                    "Company": company,
                    "Top Result Title": "ERROR",
                    "Top Result URL": "ERROR",
                    "Top Result Snippet": str(e),
                    "Match Score": 0,
                    "Status": "Failed"
                }

# 4. Try to auto-detect the "Company" column
def detect_company_column(df):
    for col in df.columns:
        if "company" in col.lower():
            return col
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, str)).mean() > 0.7:
            return col
    return df.columns[0]

# 5. Streamlit App UI
st.title("🔍 Enhanced Bing Company Info Scraper")

uploaded_file = st.file_uploader("Upload a CSV with company names", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    company_col = detect_company_column(df)
    companies = df[company_col].dropna().unique().tolist()
    st.success(f"Detected column: **{company_col}** with {len(companies)} companies")

    if st.button("Start Scraping"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, company in enumerate(companies):
            status_text.text(f"Scraping: {company} ({i+1}/{len(companies)})")
            result = scrape_bing(company)
            results.append(result)
            progress_bar.progress((i + 1) / len(companies))

        result_df = pd.DataFrame(results)
        st.success("✅ Done!")
        st.dataframe(result_df)

        # CSV Download
        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name="bing_company_results.csv", mime="text/csv")

        # HTML Snapshot ZIP
        shutil.make_archive("html_snapshots", 'zip', "html_snapshots")
        with open("html_snapshots.zip", "rb") as f:
            st.download_button("📄 Download HTML Snapshots", f, "html_snapshots.zip", mime="application/zip")
