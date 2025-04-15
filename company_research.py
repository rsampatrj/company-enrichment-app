import streamlit as st
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from urllib.parse import urlparse
import time
import io
import base64

# Global configuration
MAX_WORKERS = 20  # Number of concurrent browsers
RETRY_ATTEMPTS = 2
WAIT_TIME = 0.5

def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc
    return domain.replace('www.', '') if domain.startswith('www.') else domain

def create_driver():
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    return driver

def search_company_info(company_name, driver):
    try:
        driver.get(f"https://duckduckgo.com/?q={company_name}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article.result')))
        result = driver.find_element(By.CSS_SELECTOR, 'article.result')
        title = result.find_element(By.CSS_SELECTOR, 'h2 a').text
        url = result.find_element(By.CSS_SELECTOR, 'h2 a').get_attribute('href')
        return {'domain': extract_domain(url), 'name': title}
    except Exception as e:
        return {'domain': 'Not found', 'name': 'Not found'}

def search_linkedin(query, driver):
    try:
        driver.get(f"https://duckduckgo.com/?q={query}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article.result')))
        result = driver.find_element(By.CSS_SELECTOR, 'article.result')
        url = result.find_element(By.CSS_SELECTOR, 'h2 a').get_attribute('href')
        name = result.find_element(By.CSS_SELECTOR, 'h2 a').text.split('|')[0].strip()
        return {'linkedin_url': url, 'linkedin_name': name}
    except:
        return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}

def process_company(company, driver):
    try:
        company_info = search_company_info(company, driver)
        time.sleep(WAIT_TIME)
        
        # Original LinkedIn search
        linkedin_original = search_linkedin(f"{company} | LinkedIn", driver)
        time.sleep(WAIT_TIME)
        
        # Site Company search
        site_company_search = (f"{company_info['name']} | LinkedIn" if company_info['name'] != 'Not found' 
                              else "Invalid Company Name")
        linkedin_site_company = search_linkedin(site_company_search, driver) if company_info['name'] != 'Not found' else {
            'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}
        time.sleep(WAIT_TIME)
        
        # Site Domain search
        site_domain_search = (f"site:linkedin.com/company {company_info['domain']}" 
                            if company_info['domain'] != 'Not found' else "Invalid Domain")
        linkedin_site_domain = search_linkedin(site_domain_search, driver) if company_info['domain'] != 'Not found' else {
            'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}
        time.sleep(WAIT_TIME)

        return {
            'Uploaded Company': company,
            'Website Domain': company_info['domain'],
            'Company Name': company_info['name'],
            'LinkedIn Company Name': linkedin_original['linkedin_name'],
            'Company LinkedIn URL': linkedin_original['linkedin_url'],
            'LinkedIn URL (Site Company)': linkedin_site_company['linkedin_url'],
            'LinkedIn URL (Site Domain)': linkedin_site_domain['linkedin_url']
        }
    except Exception as e:
        return {'Uploaded Company': company, 'error': str(e)}

def process_batch(companies, progress_bar):
    drivers = [create_driver() for _ in range(MAX_WORKERS)]
    results = []
    total = len(companies)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_company, company, drivers[i % MAX_WORKERS]): company 
                  for i, company in enumerate(companies)}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            st.session_state.processed = len(results)
            progress_bar.progress(len(results) / total)
            
    for driver in drivers:
        driver.quit()
    return results

def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False)
    writer.close()
    processed_data = output.getvalue()
    return processed_data

def main():
    st.title("Company Research Automation")
    st.write("Upload a CSV or text file with company names (one per line/column)")

    if 'processed' not in st.session_state:
        st.session_state.processed = 0
    if 'results' not in st.session_state:
        st.session_state.results = None

    uploaded_file = st.file_uploader("Choose a file", type=['csv', 'txt'])
    
    if uploaded_file and st.button("Start Processing"):
        try:
            if uploaded_file.name.endswith('.csv'):
                companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
            else:
                companies = [line.decode().strip() for line in uploaded_file.readlines()]
            
            st.session_state.total = len(companies)
            progress_bar = st.progress(0)
            
            with st.spinner('Processing companies...'):
                results = process_batch(companies, progress_bar)
                df = pd.DataFrame(results)
                
                # Retry logic
                for attempt in range(RETRY_ATTEMPTS):
                    failed_mask = df.apply(lambda x: x.str.contains('Not found').any(), axis=1)
                    failed_companies = df[failed_mask]['Uploaded Company'].tolist()
                    if not failed_companies:
                        break
                    
                    with st.spinner(f"Retry attempt {attempt+1} for {len(failed_companies)} companies..."):
                        retry_results = process_batch(failed_companies, progress_bar)
                        df = df[~failed_mask]
                        df = pd.concat([df, pd.DataFrame(retry_results)], ignore_index=True)

                st.session_state.results = df
                st.success("Processing completed!")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

    if st.session_state.results is not None:
        st.write("Results preview:")
        st.dataframe(st.session_state.results.head())
        
        excel_file = to_excel(st.session_state.results)
        b64 = base64.b64encode(excel_file).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="results.xlsx">Download Excel File</a>'
        st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
