import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO
import concurrent.futures

# Configuration
MAX_WORKERS = 5
BATCH_SIZE = 20
REQUEST_DELAY = 1

def extract_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        return domain.replace("www.", "") if domain.startswith("www.") else domain
    except:
        return "Not found"

class BulkCompanySearcher:
    def __init__(self):
        self.ddgs = DDGS()
        
    def search_company(self, company):
        try:
            # Website search
            website_result = self.ddgs.text(company, max_results=1)
            website = website_result[0] if website_result else {}
            
            # LinkedIn search
            linkedin_result = self.ddgs.text(f"{company} site:linkedin.com/company", max_results=1)
            linkedin = linkedin_result[0] if linkedin_result else {}
            
            return {
                'company': company,
                'domain': extract_domain(website.get('href', 'Not found')),
                'website_name': website.get('title', 'Not found'),
                'linkedin_url': linkedin.get('href', 'Not found'),
                'linkedin_name': linkedin.get('title', 'Not found').split('|')[0].strip()
            }
        except Exception as e:
            st.error(f"Error processing {company}: {str(e)}")
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
        futures = [executor.submit(searcher.search_company, company) for company in batch]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    time.sleep(REQUEST_DELAY)
    return results

def main():
    st.title("Bulk Company Information Finder")
    st.write("Upload a CSV/text file with company names (max 100)")
    
    uploaded_file = st.file_uploader("Choose file", type=["csv", "txt"])
    
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()[:100]
        else:
            companies = [line.decode().strip() for line in uploaded_file.readlines()][:100]
        
        if st.button("Start Processing"):
            searcher = BulkCompanySearcher()
            results = []
            total = len(companies)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Process in batches
            for i in range(0, total, BATCH_SIZE):
                batch = companies[i:i+BATCH_SIZE]
                status_text.text(f"Processing {i+1}-{min(i+BATCH_SIZE, total)} of {total} companies")
                results += process_batch(searcher, batch)
                progress_bar.progress(min((i+BATCH_SIZE)/total, 1.0))
            
            # Create dataframe
            df = pd.DataFrame(results).rename(columns={
                'company': 'Uploaded Company',
                'domain': 'Website Domain',
                'website_name': 'Company Name',
                'linkedin_name': 'LinkedIn Name',
                'linkedin_url': 'LinkedIn URL'
            })
            
            # Show results
            st.dataframe(df)
            
            # Export to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                "Download Results",
                data=output.getvalue(),
                file_name="company_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
