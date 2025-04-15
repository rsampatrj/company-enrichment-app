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

def search_linkedin_url(query):
    """Search for LinkedIn URL using a custom query"""
    with DDGS() as ddgs:
        try:
            results = ddgs.text(query, max_results=1)
            return results[0]['href'] if results else 'Not found'
        except Exception as e:
            st.error(f"Error searching LinkedIn with query '{query}': {str(e)}")
            return 'Not found'

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
                
                # Get original LinkedIn info
                linkedin_info = search_linkedin_info(company)
                time.sleep(1)

                # Get LinkedIn URL using site:linkedin.com + company name
                linkedin_url_site_company = search_linkedin_url(f'site:linkedin.com {company}')
                time.sleep(1)

                # Get LinkedIn URL using site:linkedin.com + fetched domain
                domain = company_info['domain']
                linkedin_url_site_domain = search_linkedin_url(f'site:linkedin.com {domain}') if domain != 'Not found' else 'Not found'
                time.sleep(1)
                
                results.append({
                    'Uploaded Company': company,
                    'Website Domain': company_info['domain'],
                    'Company Name': company_info['name'],
                    'LinkedIn Company Name': linkedin_info['linkedin_name'],
                    'Company LinkedIn URL': linkedin_info['linkedin_url'],
                    'LinkedIn URL (Site Company)': linkedin_url_site_company,
                    'LinkedIn URL (Site Domain)': linkedin_url_site_domain
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
