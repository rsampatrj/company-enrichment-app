import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO
import concurrent.futures
import re

# Configuration
MAX_WORKERS = 3  # Reduced to avoid rate limiting
BATCH_SIZE = 10
REQUEST_DELAY = 2
MAX_RETRIES = 2

def extract_domain(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return "Not found"
        domain = parsed.netloc
        return re.sub(r'^www\.', '', domain).lower()
    except:
        return "Not found"

class EnhancedCompanySearcher:
    def __init__(self):
        self.ddgs = DDGS()
        self.search_cache = {}
        
    def search_with_retry(self, query, max_results=1):
        """Search with retry and cache mechanism"""
        if query in self.search_cache:
            return self.search_cache[query]
            
        for attempt in range(MAX_RETRIES + 1):
            try:
                results = self.ddgs.text(query, max_results=max_results)
                if results:
                    self.search_cache[query] = results
                    return results
                time.sleep(1 * attempt)  # Increasing delay
            except Exception as e:
                st.warning(f"Attempt {attempt+1} failed for '{query}': {str(e)}")
                time.sleep(2)
        return []

    def find_company_website(self, company):
        """Improved website search with multiple strategies"""
        strategies = [
            f'"{company}" official website',
            f'{company} contact',
            f'site:{company.replace(" ", "").lower()}.com'
        ]
        
        for query in strategies:
            results = self.search_with_retry(query)
            for result in results:
                if any(kw in result['title'].lower() for kw in ['home', 'official', 'website', 'company']):
                    return result
            time.sleep(0.5)
        return {}

    def find_linkedin_profile(self, company):
        """Improved LinkedIn search with multiple patterns"""
        patterns = [
            f'site:linkedin.com/company "{company}"',
            f'{company} linkedin',
            f'{company} | LinkedIn'
        ]
        
        for query in patterns:
            results = self.search_with_retry(query)
            for result in results:
                if 'linkedin.com/company' in result['href'].lower():
                    return result
            time.sleep(0.5)
        return {}

    def process_company(self, company):
        """Enhanced processing with fallback logic"""
        try:
            # Get website info
            website_result = self.find_company_website(company)
            domain = extract_domain(website_result.get('href', ''))
            website_name = website_result.get('title', 'Not found')
            
            # Get LinkedIn info
            linkedin_result = self.find_linkedin_profile(company)
            linkedin_url = linkedin_result.get('href', 'Not found')
            linkedin_name = linkedin_result.get('title', 'Not found').split('|')[0].strip()
            
            return {
                'company': company,
                'domain': domain,
                'website_name': website_name,
                'linkedin_url': linkedin_url,
                'linkedin_name': linkedin_name
            }
        except Exception as e:
            st.error(f"Critical error processing {company}: {str(e)}")
            return self.empty_result(company)

    def empty_result(self, company):
        return {
            'company': company,
            'domain': 'Not found',
            'website_name': 'Not found',
            'linkedin_url': 'Not found',
            'linkedin_name': 'Not found'
        }

def process_batch(searcher, batch):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(searcher.process_company, company): company for company in batch}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    time.sleep(REQUEST_DELAY)
    return results

def main():
    st.title("Enhanced Company Finder")
    st.write("Upload a CSV/text file with company names (max 100)")
    
    uploaded_file = st.file_uploader("Choose file", type=["csv", "txt"])
    
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()[:100]
        else:
            companies = [line.decode().strip() for line in uploaded_file.readlines()][:100]
        
        if st.button("Start Processing"):
            searcher = EnhancedCompanySearcher()
            results = []
            total = len(companies)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Process in batches with progress
            for batch_num, i in enumerate(range(0, total, BATCH_SIZE)):
                batch = companies[i:i+BATCH_SIZE]
                status_text.text(f"Processing batch {batch_num+1} ({len(batch)} companies)")
                results += process_batch(searcher, batch)
                progress_bar.progress((i+BATCH_SIZE)/total)
                time.sleep(REQUEST_DELAY)
            
            # Create and display dataframe
            df = pd.DataFrame(results).rename(columns={
                'company': 'Uploaded Company',
                'domain': 'Website Domain',
                'website_name': 'Company Name',
                'linkedin_name': 'LinkedIn Name',
                'linkedin_url': 'LinkedIn URL'
            })
            
            st.dataframe(df)
            
            # Export to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                "Download Results",
                data=output.getvalue(),
                file_name="enhanced_company_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
