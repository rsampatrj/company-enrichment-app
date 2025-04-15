import streamlit as st
from duckduckgo_search import DDGS, exceptions as ddg_exceptions
import pandas as pd
from urllib.parse import urlparse
import time
import argparse
import os
import random

# Constants
CHECKPOINT_FILE = "checkpoint.xlsx"
MAX_RETRIES = 3
BASE_DELAY = 5
RATE_LIMIT_DELAY = 60  # Wait 1 minute if rate limited
REQUESTS_PER_BATCH = 20
BATCH_DELAY = 60  # Wait 1 minute after each batch

def extract_domain(url):
    """Extract domain from URL"""
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def search_with_retry(query_func, *args, **kwargs):
    """Generic retry wrapper with exponential backoff"""
    for attempt in range(MAX_RETRIES):
        try:
            return query_func(*args, **kwargs)
        except ddg_exceptions.DuckDuckGoSearchException as e:
            if 'Ratelimit' in str(e):
                sleep_time = BASE_DELAY * (2 ** attempt) + random.uniform(0, 2)
                print(f"Rate limited. Attempt {attempt+1}/{MAX_RETRIES}. Waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)
                continue
            raise
        except Exception as e:
            print(f"Error: {str(e)}")
            break
    return None

def search_company_info(company_name, ddgs):
    """Search for company website and name using DuckDuckGo"""
    try:
        results = search_with_retry(ddgs.text, company_name, max_results=1)
        if results:
            first_result = results[0]
            return {
                'domain': extract_domain(first_result['href']),
                'name': first_result['title']
            }
    except Exception as e:
        print(f"Error searching for {company_name}: {str(e)}")
    return {'domain': 'Not found', 'name': 'Not found'}

def search_linkedin(query, ddgs):
    """Generic LinkedIn search using DuckDuckGo"""
    try:
        results = search_with_retry(ddgs.text, query, max_results=1)
        if results:
            first_result = results[0]
            linkedin_url = first_result['href']
            linkedin_name = first_result['title'].split('|')[0].strip()
            return {'linkedin_url': linkedin_url, 'linkedin_name': linkedin_name}
    except Exception as e:
        print(f"Error searching LinkedIn for {query}: {str(e)}")
    return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}

def process_company(company, ddgs):
    """Process a single company and return all results"""
    company_info = search_company_info(company, ddgs)
    time.sleep(random.uniform(1, 3))  # Randomized delay

    # Original LinkedIn search
    linkedin_original = search_linkedin(f"{company} | LinkedIn", ddgs)
    time.sleep(random.uniform(1, 3))

    # Site Company search
    site_company_search = (f"{company_info['name']} | LinkedIn" 
                          if company_info['name'] != 'Not found' 
                          else "Invalid Company Name")
    linkedin_site_company = search_linkedin(site_company_search, ddgs) if company_info['name'] != 'Not found' else {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}
    time.sleep(random.uniform(1, 3))

    # Site Domain search
    site_domain_search = (f"site:linkedin.com/company {company_info['domain']}" 
                         if company_info['domain'] != 'Not found' 
                         else "Invalid Domain")
    linkedin_site_domain = search_linkedin(site_domain_search, ddgs) if company_info['domain'] != 'Not found' else {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}
    time.sleep(random.uniform(1, 3))

    return {
        'Uploaded Company': company,
        'Website Domain': company_info['domain'],
        'Company Name': company_info['name'],
        'LinkedIn Company Name': linkedin_original['linkedin_name'],
        'Company LinkedIn URL': linkedin_original['linkedin_url'],
        'LinkedIn URL (Site Company)': linkedin_site_company['linkedin_url'],
        'LinkedIn URL (Site Domain)': linkedin_site_domain['linkedin_url']
    }

def load_checkpoint():
    """Load existing checkpoint if available"""
    if os.path.exists(CHECKPOINT_FILE):
        return pd.read_excel(CHECKPOINT_FILE).to_dict('records')
    return []

def save_checkpoint(results):
    """Save current progress to checkpoint file"""
    df = pd.DataFrame(results)
    df.to_excel(CHECKPOINT_FILE, index=False)

def main(input_file, output_file):
    """Main processing function with checkpointing and rate limit handling"""
    # Load checkpoint or initialize
    results = load_checkpoint()
    processed_companies = set(r['Uploaded Company'] for r in results)
    
    # Read input file
    if input_file.endswith('.csv'):
        companies = pd.read_csv(input_file).iloc[:, 0].tolist()
    else:
        with open(input_file, 'r') as f:
            companies = [line.strip() for line in f.readlines()]

    # Filter already processed companies
    remaining_companies = [c for c in companies if c not in processed_companies]
    
    # Initialize progress
    total_companies = len(remaining_companies)
    start_idx = len(results)
    
    with DDGS() as ddgs:
        for idx, company in enumerate(remaining_companies, start=1):
            try:
                print(f"Processing {start_idx + idx}/{len(companies)}: {company}")
                result = process_company(company, ddgs)
                results.append(result)
                
                # Save checkpoint every 10 companies
                if idx % 10 == 0:
                    save_checkpoint(results)
                    
                # Batch delay
                if idx % REQUESTS_PER_BATCH == 0:
                    print(f"Completed {idx} requests. Waiting {BATCH_DELAY}s...")
                    time.sleep(BATCH_DELAY)
                    
            except Exception as e:
                print(f"Critical error processing {company}: {str(e)}")
                save_checkpoint(results)
                raise

    # Final save
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    print(f"Results saved to {output_file}")

# Streamlit UI
if __name__ == "__main__":
    st.title("Company Information Search")
    
    uploaded_file = st.file_uploader("Upload CSV/TXT file", type=["csv", "txt"])
    
    if uploaded_file:
        if st.button("Start Processing"):
            try:
                # Save uploaded file
                with open("input_file", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Run main process
                main("input_file", "results.xlsx")
                
                # Show completion
                st.success("Processing completed!")
                st.download_button(
                    label="Download Results",
                    data=open("results.xlsx", "rb").read(),
                    file_name="results.xlsx",
                    mime="application/vnd.ms-excel"
                )
                
            except Exception as e:
                st.error(f"Processing failed: {str(e)}")
                if os.path.exists(CHECKPOINT_FILE):
                    st.warning("Partial results available:")
                    st.download_button(
                        label="Download Partial Results",
                        data=open(CHECKPOINT_FILE, "rb").read(),
                        file_name="partial_results.xlsx",
                        mime="application/vnd.ms-excel"
                    )
