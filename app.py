import streamlit as st
import asyncio
import random
from duckduckgo_search import AsyncDDGS

# Limit the number of concurrent asynchronous requests.
CONCURRENT_LIMIT = 5

async def search_company(company_name: str, proxies: str = None, semaphore: asyncio.Semaphore = None):
    """Search for a company's info using an asynchronous query with Tor proxy support."""
    if semaphore:
        async with semaphore:
            result = await _search_company(company_name, proxies)
    else:
        result = await _search_company(company_name, proxies)
    return result

async def _search_company(company_name: str, proxies: str = None):
    # Add a small random delay to spread out the requests.
    await asyncio.sleep(random.uniform(1, 3))
    
    try:
        # Use AsyncDDGS with the given proxies parameter.
        async with AsyncDDGS(proxies=proxies) as ddgs:
            # Get the first search result for the company.
            results = await ddgs.text(company_name, max_results=1)
            if results:
                return {"company": company_name, "result": results[0]}
            else:
                return {"company": company_name, "result": "No result found."}
    except Exception as e:
        return {"company": company_name, "result": f"Error: {e}"}

async def search_all_companies(companies: list, proxies: str = None):
    """Run asynchronous searches for all companies with a concurrency limit."""
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    tasks = [search_company(company, proxies=proxies, semaphore=semaphore) for company in companies]
    results = await asyncio.gather(*tasks)
    return results

def main():
    st.title("DuckDuckGo Search Using Tor Proxy")
    st.write(
        "This app uses DuckDuckGo to search for information about companies while routing requests via Tor to bypass rate limits. "
        "Make sure you have the Tor service running (for example, Tor Browser on port 9150)."
    )
    
    # File uploader: expects a CSV or TXT file containing company names (one per line)
    uploaded_file = st.file_uploader("Upload a CSV/TXT file with Company Names", type=["csv", "txt"])
    
    # Input field for the Tor proxy (if not provided, leave empty to use the default network IP).
    proxy_input = st.text_input("Enter Tor Proxy (e.g., socks5://localhost:9150)", value="socks5://localhost:9150")
    proxies = proxy_input.strip() if proxy_input.strip() != "" else None
    
    if uploaded_file:
        try:
            data = uploaded_file.getvalue().decode("utf-8")
            companies = [line.strip() for line in data.splitlines() if line.strip()]
            st.write("Companies loaded:", companies)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            companies = []
        
        if st.button("Search Companies"):
            if not companies:
                st.error("No companies found in the file.")
            else:
                st.info("Searching companies... This might take a while if there are many requests.")
                try:
                    # Run all company searches asynchronously using Tor as the proxy.
                    results = asyncio.run(search_all_companies(companies, proxies=proxies))
                    st.write("### Search Results")
                    for res in results:
                        st.markdown(f"**{res['company']}**: {res['result']}")
                except Exception as e:
                    st.error(f"An error occurred during searches: {e}")

if __name__ == '__main__':
    main()
