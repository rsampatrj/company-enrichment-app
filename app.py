import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# Previous helper functions remain the same (extract_domain, search_company_info, search_linkedin_info)

def process_company(batch_name, company):
    """Wrapper function for processing individual companies"""
    company_info = search_company_info(company)
    time.sleep(1)  # Maintain search interval
    linkedin_info = search_linkedin_info(company)
    time.sleep(1)
    
    return {
        'Batch Name': batch_name,
        'Original Name': company,
        'Website Domain': company_info['domain'],
        'Found Company Name': company_info['name'],
        'LinkedIn Name': linkedin_info['linkedin_name'],
        'LinkedIn URL': linkedin_info['linkedin_url']
    }

def main():
    st.title("Company & LinkedIn Finder")
    st.write("Upload multiple CSV/text files (max 20) with company names (max 1000 per file)")

    uploaded_files = st.file_uploader("Choose files", 
                                    type=['csv', 'txt'], 
                                    accept_multiple_files=True)
    
    if uploaded_files:
        if len(uploaded_files) > 20:
            st.error("Maximum 20 batches allowed")
            return

        all_entries = []
        for file in uploaded_files:
            if file.name.endswith('.csv'):
                companies = pd.read_csv(file).iloc[:, 0].tolist()
            else:
                companies = [line.decode().strip() for line in file.readlines()]
            
            if len(companies) > 1000:
                st.error(f"Batch {file.name} contains {len(companies)} entries. Max 1000 per batch.")
                return
            
            all_entries.extend([(file.name, company) for company in companies])

        st.success(f"Total companies to process: {len(all_entries)} across {len(uploaded_files)} batches")

        if st.button("Start Parallel Processing"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_companies = len(all_entries)
            
            # Configure parallel processing
            max_workers = st.slider("Select parallel workers (2-5 recommended)", 1, 10, 3)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(process_company, bn, c): (bn, c)
                    for bn, c in all_entries
                }
                
                completed = 0
                for future in as_completed(futures):
                    batch_name, company = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        completed += 1
                        progress = completed / total_companies
                        progress_bar.progress(progress)
                        status_text.text(
                            f"Processed {completed}/{total_companies} | "
                            f"Batch: {batch_name} | "
                            f"Current: {company}"
                        )
                    except Exception as e:
                        st.error(f"Error processing {company}: {str(e)}")

            # Rest of the code for displaying results and downloads remains same
            # ...
