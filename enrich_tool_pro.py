from urllib.parse import quote

@st.cache_data(show_spinner=True)
def search_brave(query):
    # Wrap in curly braces and URL encode
    encoded_query = quote(f'{{"{query}"}}')
    url = f"https://search.brave.com/search?q={encoded_query}&source=web"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        result_link = soup.select_one("a.result-header")
        return result_link['href'] if result_link else ""
    except:
        return ""
