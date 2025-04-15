import streamlit as st
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
from io import BytesIO

MAX_RETRIES = 2  # Reduced retries to prevent API blocks
REQUEST_DELAY = 2  # Increased delay between requests
DOMAIN_BLACKLIST = {'linkedin.com'}  # Sites to exclude from domain results

def extract_domain(url):
    """Extract clean domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        domain = domain.replace('www.', '') if domain.startswith('www.') else domain
        return domain.split(':')[0]  # Remove port numbers
    except:
        return 'Not found'

def search_company_info(company_name):
    """Search for company website with improved query"""
    with DDGS() as ddgs:
        try:
            results = ddgs.text(f'"{company_name}" official website', max_results=3)
            for result in results:
                domain = extract_domain(result['href'])
                if domain not in DOMAIN_BLACKLIST and '.' in domain:
                    return {
                        'domain': domain,
                        'name': result['title'].split('|')[0].split('-')[0].strip()
                    }
        except Exception as e:
            st.error(f"Search error for {company_name}: {str(e)}")
        return {'domain': 'Not found', 'name': 'Not found'}

def linkedin_search(query):
    """Universal LinkedIn search with validation"""
    with DDGS() as ddgs:
        try:
            results = ddgs.text(f'"{query}" site:linkedin.com', max_results=3)
            for result in results:
                if 'linkedin.com/company/' in result['href']:
                    return {
                        'url': result['href'].split('?')[0],
                        'name': result['title'].split('|')[0].split('-')[0].strip()
                    }
        except Exception as e:
            st.error(f"LinkedIn search error: {str(e)}")
        return {'url': 'Not found', 'name': 'Not found'}

def main():
    st.title("Enhanced Company & LinkedIn Finder")
    
    uploaded_file = st.file_uploader("Upload company list (CSV/txt)", type=['csv', 'txt'])
    
    if uploaded_file and st.button("Start Search"):
        # File processing
        if uploaded_file.name.endswith('.csv'):
            companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
        else:
            companies = [line.decode().strip() for line in uploaded_file.readlines()]
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, company in enumerate(companies):
            status_text.text(f"Processing {company} ({idx+1}/{len(companies)})")
            
            # Company website search
            company_info = search_company_info(company)
            time.sleep(REQUEST_DELAY)
            
            # LinkedIn searches
            linkedin_base = linkedin_search(company)
            time.sleep(REQUEST_DELAY)
            
            linkedin_domain = linkedin_search(company_info['domain']) if company_info['domain'] != 'Not found' else {'url': 'Not found', 'name': 'Not found'}
            time.sleep(REQUEST_DELAY)
            
            results.append({
                'Original Name': company,
                'Website Domain': company_info['domain'],
                'Company Name': company_info['name'],
                'LinkedIn (Name Search)': linkedin_base['url'],
                'LinkedIn Name': linkedin_base['name'],
                'LinkedIn (Domain Search)': linkedin_domain['url']
            })
            
            progress_bar.progress((idx+1)/len(companies))
        
        # Create dataframe and filter results
        df = pd.DataFrame(results)
        df = df[~df[['Website Domain', 'Company Name', 'LinkedIn (Name Search)']].apply(
            lambda x: x.str.contains('Not found').all(), axis=1)]
        
        # Display results
        st.subheader(f"Found {len(df)} valid results")
        st.dataframe(df)
        
        # Excel export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="Download Results",
            data=output.getvalue(),
            file_name='company_research.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

if __name__ == "__main__":
    main()
