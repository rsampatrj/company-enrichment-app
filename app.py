import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO

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
    """Search for LinkedIn profile using DuckDuckGo with site operator"""
    with DDGS() as ddgs:
        try:
            # Modified search query with site operator
            results = ddgs.text(f"site:linkedin.com {company_name}", max_results=1)
            if results:
                first_result = results[0]
                linkedin_url = first_result['href']
                # Clean LinkedIn name from title (modified splitting logic)
                linkedin_name = first_result['title'].split('|')[0].split(' - ')[0].strip()
                return {
                    'linkedin_url': linkedin_url,
                    'linkedin_name': linkedin_name
                }
        except Exception as e:
            st.error(f"Error searching LinkedIn for {company_name}: {str(e)}")
        return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}

def main():
    st.title("Company & LinkedIn Finder")
    st.write("Upload a CSV/text file with company names (one per line)")

    uploaded_file = st.file_uploader("Choose a file", type=['csv', 'txt'])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
        else:
            companies = [line.decode().strip() for line in uploaded_file.readlines()]

        if st.button("Start Search"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, company in enumerate(companies):
                status_text.text(f"Searching {company}... ({i+1}/{len(companies)})")
                
                # Get company website info
                company_info = search_company_info(company)
                time.sleep(1)
                
                # Get LinkedIn info
                linkedin_info = search_linkedin_info(company)
                time.sleep(1)
                
                results.append({
                    'Uploaded Company': company,
                    'Website Domain': company_info['domain'],
                    'Company Name': company_info['name'],
                    'LinkedIn Company Name': linkedin_info['linkedin_name'],
                    'Company LinkedIn URL': linkedin_info['linkedin_url']
                })
                progress_bar.progress((i+1)/len(companies))

            df = pd.DataFrame(results)
            st.subheader("Results")
            st.dataframe(df)

            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')
            excel_data = output.getvalue()

            st.download_button(
                label="Download results as Excel",
                data=excel_data,
                file_name='company_info.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

if __name__ == "__main__":
    main()
