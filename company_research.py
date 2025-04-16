from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
import argparse
 
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
            print(f"Error searching for {company_name}: {str(e)}")
        return {'domain': 'Not found', 'name': 'Not found'}
 
def search_linkedin(query):
    """Generic LinkedIn search using DuckDuckGo"""
    with DDGS() as ddgs:
        try:
            results = ddgs.text(query, max_results=1)
            if results:
                first_result = results[0]
                linkedin_url = first_result['href']
                linkedin_name = first_result['title'].split('|')[0].strip()
                return {'linkedin_url': linkedin_url, 'linkedin_name': linkedin_name}
        except Exception as e:
            print(f"Error searching LinkedIn for {query}: {str(e)}")
        return {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}
 
def process_company(company):
    """Process a single company and return all results"""
    company_info = search_company_info(company)
    time.sleep(1)
    # Original LinkedIn search
    linkedin_original = search_linkedin(f"{company} | LinkedIn")
    time.sleep(1)
    # Site Company search
    site_company_search = (f"{company_info['name']} | LinkedIn" 
                          if company_info['name'] != 'Not found' 
                          else "Invalid Company Name")
    linkedin_site_company = search_linkedin(site_company_search) if company_info['name'] != 'Not found' else {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}
    time.sleep(1)
    # Site Domain search
    site_domain_search = (f"site:linkedin.com/company {company_info['domain']}" 
                         if company_info['domain'] != 'Not found' 
                         else "Invalid Domain")
    linkedin_site_domain = search_linkedin(site_domain_search) if company_info['domain'] != 'Not found' else {'linkedin_url': 'Not found', 'linkedin_name': 'Not found'}
    time.sleep(1)
 
    return {
        'Uploaded Company': company,
        'Website Domain': company_info['domain'],
        'Company Name': company_info['name'],
        'LinkedIn Company Name': linkedin_original['linkedin_name'],
        'Company LinkedIn URL': linkedin_original['linkedin_url'],
        'LinkedIn URL (Site Company)': linkedin_site_company['linkedin_url'],
        'LinkedIn URL (Site Domain)': linkedin_site_domain['linkedin_url']
    }
 
def main(input_file, output_file):
    """Main processing function"""
    # Read input file
    if input_file.endswith('.csv'):
        companies = pd.read_csv(input_file).iloc[:, 0].tolist()
    else:
        with open(input_file, 'r') as f:
            companies = [line.strip() for line in f.readlines()]
 
    results = []
    # Initial processing
    print(f"Processing {len(companies)} companies...")
    for i, company in enumerate(companies, 1):
        print(f"Processing {i}/{len(companies)}: {company}")
        results.append(process_company(company))
    df = pd.DataFrame(results)
    # Retry logic
    max_retries = 2
    for retry in range(max_retries):
        columns_to_check = ['Website Domain', 'Company Name', 
                           'LinkedIn Company Name', 'Company LinkedIn URL',
                           'LinkedIn URL (Site Company)', 'LinkedIn URL (Site Domain)']
        mask = (df[columns_to_check] == 'Not found').all(axis=1)
        failed_companies = df.loc[mask, 'Uploaded Company'].tolist()
        if not failed_companies:
            break
        df = df[~mask]
        retry_results = []
        print(f"Retry {retry+1} for {len(failed_companies)} failed companies...")
        for i, company in enumerate(failed_companies, 1):
            print(f"Retrying {i}/{len(failed_companies)}: {company}")
            retry_results.append(process_company(company))
        if retry_results:
            new_df = pd.DataFrame(retry_results)
            df = pd.concat([df, new_df], ignore_index=True)
    # Save results
    df.to_excel(output_file, index=False)
    print(f"Results saved to {output_file}")
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Company and LinkedIn Information Finder')
    parser.add_argument('-i', '--input', required=True, help='Input file (CSV or text)')
    parser.add_argument('-o', '--output', default='results.xlsx', help='Output Excel file name')
    args = parser.parse_args()
    main(args.input, args.output)
