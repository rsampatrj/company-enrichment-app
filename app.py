import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# Rate limiting configuration
MAX_CONCURRENT_WORKERS = 10  # Reduced from 20 to be more conservative
BASE_DELAY = 1.5  # Increased base delay between requests
RETRY_LIMIT = 3  # Number of retry attempts for rate limits

def extract_domain(url):
    """Extract domain from URL"""
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def safe_ddgs_search(query, max_retries=RETRY_LIMIT):
    """Wrapper with retry logic for DDGS searches"""
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=1)
                if results:
                    return results
                return None
        except Exception as e:
            if "429" in str(e) or "202" in str(e) or "Ratelimit" in str(e):
                wait_time = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            raise
    return None

def search_company_info(company_name):
    """Search for company website and name with rate limit handling"""
    try:
        results = safe_ddgs_search(company_name)
        if results:
            first_result = results[0]
            return {
                'domain': extract_domain(first_result['href']),
                'name': first_result['title'],
                'error': None
            }
        return {'domain': 'Not found', 'name': 'Not found', 'error': None}
    except Exception as e:
        return {'domain': 'Error', 'name': 'Error', 
                'error': f"Company search error: {str(e)}"}

def search_linkedin_info(company_name):
    """Search for LinkedIn profile with enhanced error handling"""
    try:
        results = safe_ddgs_search(f"{company_name} | LinkedIn")
        if results:
            first_result = results[0]
            linkedin_url = first_result['href']
            linkedin_name = first_result['title'].split('|')[0].strip()
            return {
                'linkedin_url': linkedin_url,
                'linkedin_name': linkedin_name,
                'error': None
            }
        return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found', 
                'error': None}
    except Exception as e:
        return {'linkedin_url': 'Error', 'linkedin_name': 'Error', 
                'error': f"LinkedIn search error: {str(e)}"}

def process_company(company):
    """Process a single company with enhanced rate limiting"""
    company_info = search_company_info(company)
    time.sleep(BASE_DELAY + random.uniform(0, 0.5))  # Add jitter
    
    linkedin_info = search_linkedin_info(company)
    time.sleep(BASE_DELAY + random.uniform(0, 0.5))
    
    errors = []
    if company_info.get('error'):
        errors.append(company_info['error'])
    if linkedin_info.get('error'):
        errors.append(linkedin_info['error'])
    
    return {
        'Uploaded Company': company,
        'Website Domain': company_info['domain'],
        'Company Name': company_info['name'],
        'LinkedIn Company Name': linkedin_info['linkedin_name'],
        'Company LinkedIn URL': linkedin_info['linkedin_url'],
        'Errors': ' | '.join(errors) if errors else None
    }

def main():
    st.title("Bulk Company & LinkedIn Finder")
    st.write("Upload a CSV/text file with company names (one per line/column)")

    uploaded_file = st.file_uploader("Choose a file", type=['csv', 'txt'])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
        else:
            companies = [line.decode().strip() for line in uploaded_file.readlines()]

        if st.button(f"Start Bulk Search ({MAX_CONCURRENT_WORKERS} concurrent)"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_companies = len(companies)
            
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
                futures = {executor.submit(process_company, company): i 
                          for i, company in enumerate(companies)}
                
                results = [None] * len(companies)
                completed = 0
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        index = futures[future]
                        results[index] = result
                        completed += 1
                        progress = completed / total_companies
                        progress_bar.progress(progress)
                        status_text.text(
                            f"Processed {completed}/{total_companies} companies "
                            f"({progress:.1%}) - {MAX_CONCURRENT_WORKERS} concurrent workers"
                        )
                    except Exception as e:
                        st.error(f"Critical error processing company: {str(e)}")

            # Remove any None results in case of errors
            results = [r for r in results if r is not None]
            
            df = pd.DataFrame(results)
            st.subheader("Results")
            st.dataframe(df)

            # Show errors in expander
            if 'Errors' in df.columns and df['Errors'].notnull().any():
                with st.expander("View Errors", expanded=False):
                    error_df = df[df['Errors'].notnull()][['Uploaded Company', 'Errors']]
                    st.dataframe(error_df)

            # Download results
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')
            excel_data = output.getvalue()

            st.download_button(
                label="Download Full Results as Excel",
                data=excel_data,
                file_name='bulk_company_info.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

if __name__ == "__main__":
    main()
