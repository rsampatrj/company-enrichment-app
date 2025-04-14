import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time

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

def main():
    st.title("Company Domain Finder")
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
                status_text.text(f"Searching for {company}... ({i+1}/{len(companies)})")
                result = search_company_info(company)
                results.append({
                    'Uploaded Company': company,
                    'Website Domain': result['domain'],
                    'Company Name': result['name']
                })
                progress_bar.progress((i+1)/len(companies))
                time.sleep(1)  # Add delay to avoid rate limiting

            df = pd.DataFrame(results)
            st.subheader("Results")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download results as CSV",
                data=csv,
                file_name='company_domains.csv',
                mime='text/csv'
            )

if __name__ == "__main__":
    main()
