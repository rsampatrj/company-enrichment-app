mport streamlit as st
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
    """Search for LinkedIn profile using specific Japanese pattern"""
    with DDGS() as ddgs:
        try:
            # Exact pattern match for Japanese company names
            results = ddgs.text(f'site:linkedin.com {company_name} Employees', max_results=1)
            if results:
                first_result = results[0]
                linkedin_url = first_result['href']
                
                # Enhanced cleaning for Japanese company names
                linkedin_name = first_result['title'].split('|')[0].split('-')[0].replace('Employees', '').strip()
                return {
                    'linkedin_url': linkedin_url,
                    'linkedin_name': linkedin_name
                }
        except Exception as e:
            st.error(f"Error searching LinkedIn for {company_name}: {str(e)}")
        return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}

def main():
    st.title("企業検索ツール - Company & LinkedIn Finder")
    st.write("CSVまたはテキストファイルをアップロードしてください (会社名を1行ずつ)")

    uploaded_file = st.file_uploader("ファイルを選択", type=['csv', 'txt'])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            companies = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
        else:
            companies = [line.decode().utf-8().strip() for line in uploaded_file.readlines()]

        if st.button("検索開始"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, company in enumerate(companies):
                status_text.text(f"検索中: {company}... ({i+1}/{len(companies)})")
                
                # Get company website info
                company_info = search_company_info(company)
                time.sleep(1)
                
                # Get LinkedIn info
                linkedin_info = search_linkedin_info(company)
                time.sleep(1)
                
                results.append({
                    'アップロード企業名': company,
                    '企業ドメイン': company_info['domain'],
                    '企業名': company_info['name'],
                    'LinkedIn企業名': linkedin_info['linkedin_name'],
                    'LinkedInURL': linkedin_info['linkedin_url']
                })
                progress_bar.progress((i+1)/len(companies))

            df = pd.DataFrame(results)
            st.subheader("検索結果")
            st.dataframe(df)

            # Create Excel file with Japanese encoding
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='結果')
            excel_data = output.getvalue()

            st.download_button(
                label="Excelで結果をダウンロード",
                data=excel_data,
                file_name='企業検索結果.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

if __name__ == "__main__":
    main()
