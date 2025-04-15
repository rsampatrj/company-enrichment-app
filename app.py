import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO
import zipfile

def extract_domain(url):
    """Extract domain from URL"""
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def search_company_info(company_name):
    """Search for company website and name using DuckDuckGo"""
    with DDGS() as ddgs:
        try:
            results = ddgs.text(company_name, max_results=1)
            if results:
                first_result = results[0]
                return {
                    'domain': extract_domain(first_result['href']),
                    'name': first_result['title']
                }
        except Exception as e:
            st.error(f"Error searching for {company_name}: {str(e)}")
        return {'domain': 'Not found', 'name': 'Not found'}

def search_linkedin_info(company_name):
    """Search for LinkedIn profile using DuckDuckGo"""
    with DDGS() as ddgs:
        try:
            results = ddgs.text(f"{company_name} | LinkedIn", max_results=1)
            if results:
                first_result = results[0]
                linkedin_url = first_result['href']
                linkedin_name = first_result['title'].split('|')[0].strip()
                return {
                    'linkedin_url': linkedin_url,
                    'linkedin_name': linkedin_name
                }
        except Exception as e:
            st.error(f"Error searching LinkedIn for {company_name}: {str(e)}")
        return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}

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
            
            # Store both batch name and company name
            all_entries.extend([(file.name, company) for company in companies])

        st.success(f"Total companies to process: {len(all_entries)} across {len(uploaded_files)} batches")

        if st.button("Start Bulk Search"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_companies = len(all_entries)

            for i, (batch_name, company) in enumerate(all_entries, 1):
                status_text.text(f"Processing: {i}/{total_companies} | Batch: {batch_name} | Company: {company}")
                
                company_info = search_company_info(company)
                time.sleep(1)
                
                linkedin_info = search_linkedin_info(company)
                time.sleep(1)
                
                results.append({
                    'Batch Name': batch_name,
                    'Original Name': company,
                    'Website Domain': company_info['domain'],
                    'Found Company Name': company_info['name'],
                    'LinkedIn Name': linkedin_info['linkedin_name'],
                    'LinkedIn URL': linkedin_info['linkedin_url']
                })
                progress_bar.progress(i/total_companies)

            df = pd.DataFrame(results)
            st.subheader("Processing Results")
            st.dataframe(df)

            # Create in-memory containers
            consolidated_output = BytesIO()
            batch_zip_buffer = BytesIO()

            # Consolidated Excel
            with pd.ExcelWriter(consolidated_output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Consolidated')
            consolidated_data = consolidated_output.getvalue()

            # Batch-wise ZIP
            with zipfile.ZipFile(batch_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for batch_name, group in df.groupby('Batch Name'):
                    batch_output = BytesIO()
                    with pd.ExcelWriter(batch_output, engine='openpyxl') as writer:
                        group.to_excel(writer, index=False, sheet_name=batch_name[:30])
                    zip_file.writestr(
                        f"{batch_name}.xlsx", 
                        batch_output.getvalue()
                    )
            batch_zip_buffer.seek(0)

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download Consolidated Results",
                    data=consolidated_data,
                    file_name='consolidated_results.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            with col2:
                st.download_button(
                    label="Download Batch Results (ZIP)",
                    data=batch_zip_buffer,
                    file_name='batch_results.zip',
                    mime='application/zip'
                )

if __name__ == "__main__":
    main()
