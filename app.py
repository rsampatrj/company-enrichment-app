import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO

def extract_domain(url):
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

def search_linkedin_url(company_name, domain):
    """Find the best LinkedIn URL using prioritized strategies"""
    queries = [
        f'"{company_name}" | LinkedIn',
        f'site:linkedin.com {company_name}',
        f'site:linkedin.com {domain}' if domain != 'Not found' else None
    ]
    
    with DDGS() as ddgs:
        for query in filter(None, queries):
            try:
                results = ddgs.text(query, max_results=5)
                for result in results:
                    url = result['href']
                    title = result['title'].split('|')[0].split('-')[0].strip()

                    # Preferred pattern
                    if any(x in url for x in ['/company/', '/school/', '/university/']):
                        return {
                            'linkedin_url': url,
                            'linkedin_name': title,
                            'confidence': 'High'
                        }

                # If no ideal match, take the first LinkedIn URL anyway
                for result in results:
                    url = result['href']
                    if "linkedin.com" in url:
                        title = result['title'].split('|')[0].split('-')[0].strip()
                        return {
                            'linkedin_url': url,
                            'linkedin_name': title,
                            'confidence': 'Medium'
                        }

            except Exception as e:
                st.warning(f"LinkedIn search failed for {query}: {e}")
    
    return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found', 'confidence': 'Low'}

def main():
    st.title("Company & LinkedIn Finder")
    st.write("Upload a CSV or TXT file (one company name per line).")

    uploaded_file = st.file_uploader("Choose a file", type=['csv', 'txt'])

    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
        else:
            companies = [line.decode('utf-8').strip() for line in uploaded_file.readlines()]

        if st.button("Start Search"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, company in enumerate(companies):
                status_text.text(f"Searching: {company}... ({i+1}/{len(companies)})")

                company_info = search_company_info(company)
                time.sleep(1)

                linkedin_info = search_linkedin_url(company, company_info['domain'])
                time.sleep(1)

                results.append({
                    'Uploaded Company Name': company,
                    'Domain': company_info['domain'],
                    'Detected Name': company_info['name'],
                    'LinkedIn Name': linkedin_info['linkedin_name'],
                    'LinkedIn URL': linkedin_info['linkedin_url'],
                    'Confidence': linkedin_info.get('confidence', 'Low')
                })

                progress_bar.progress((i+1) / len(companies))

            df = pd.DataFrame(results)
            st.subheader("Results")
            st.dataframe(df)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')
            excel_data = output.getvalue()

            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name='company_linkedin_results.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

if __name__ == "__main__":
    main()
