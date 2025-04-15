import streamlit as st
import asyncio
import random
from duckduckgo_search import AsyncDDGS  # Make sure version >= 8.0.0 is installed

# Limit number of concurrent asynchronous requests.
CONCURRENT_LIMIT = 5

async def search_company(company_name: str, proxies: str = None, semaphore: asyncio.Semaphore = None):
    """Asynchronously search for a company using AsyncDDGS with an optional proxy and concurrency limit."""
    if semaphore:
        async with semaphore:
            return await _search_company(company_name, proxies)
    else:
        return await _search_company(company_name, proxies)

async def _search_company(company_name: str, proxies: str = None):
    # Introduce a random delay (1-3 seconds) to help avoid rate limits.
    await asyncio.sleep(random.uniform(1, 3))
    try:
        async with AsyncDDGS(proxies=proxies) as ddgs:
            results = await ddgs.text(company_name, max_results=1)
            if results:
                return {"company": company_name, "result": results[0]}
            else:
                return {"company": company_name, "result": "No result found."}
    except Exception as e:
        return {"company": company_name, "result": f"Error: {e}"}

async def search_all_companies(companies: list, proxies: str = None):
    """Create tasks for searching all companies concurrently, respecting the semaphore limit."""
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    tasks = [search_company(company, proxies=proxies, semaphore=semaphore) for company in companies]
    return await asyncio.gather(*tasks)

def main():
    st.title("DuckDuckGo Company Search Using Tor")
    st.write(
        "This app queries DuckDuckGo for company information using the Tor network to bypass rate limits. "
        "Ensure Tor (or Tor Browser) is running and that the proxy setting is correct."
    )
    
    uploaded_file = st.file_uploader("Upload a CSV/TXT file with Company Names", type=["csv", "txt"])
    proxy_input = st.text_input("Enter Tor Proxy (e.g., socks5://localhost:9150)", value="socks5://localhost:9150")
    proxies = proxy_input.strip() if proxy_input.strip() != "" else None

    if uploaded_file:
        try:
            file_data = uploaded_file.getvalue().decode("utf-8")
            companies = [line.strip() for line in file_data.splitlines() if line.strip()]
            st.write("Companies loaded:", companies)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            companies = []
        
        if st.button("Search Companies"):
            if not companies:
                st.error("No companies found in the file.")
            else:
                st.info("Searching companies... Please wait.")
                try:
                    results = asyncio.run(search_all_companies(companies, proxies=proxies))
                    st.write("### Search Results")
                    for res in results:
                        st.markdown(f"**{res['company']}**: {res['result']}")
                except Exception as e:
                    st.error(f"An error occurred during search: {e}")

if __name__ == '__main__':
    main()
