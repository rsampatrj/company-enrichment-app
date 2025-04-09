# enrich_tool_pro.py

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import whois
import sqlite3
import tldextract
from fuzzywuzzy import fuzz
from concurrent.futures import ThreadPoolExecutor, as_completed
from geopy.geocoders import Nominatim
from openpyxl import Workbook
from io import BytesIO

DB_PATH = "cache.db"
TABLE_NAME = "company_cache"
CLEARBIT_LOGO_API = "https://logo.clearbit.com/"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            company TEXT PRIMARY KEY,
            domain TEXT,
            website TEXT,
            confidence INTEGER,
            linkedin_url TEXT,
            linkedin_description TEXT,
            whois_created TEXT,
            whois_expires TEXT,
            whois_registrar TEXT,
            logo TEXT,
            country TEXT,
            open_corp_info TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_to_cache(result):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"""
        INSERT OR REPLACE INTO {TABLE_NAME} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["Input Company Name"],
        result["Matched Domain"],
        result["Website URL"],
        result["Confidence Score"],
        result["LinkedIn URL"],
        result["LinkedIn Description"],
        result["WHOIS Created"],
        result["WHOIS Expiry"],
        result["WHOIS Registrar"],
        result["Logo URL"],
        result["Country"],
        result["OpenCorporates Info"]
    ))
    conn.commit()
    conn.close()

def get_from_cache(company):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT * FROM {TABLE_NAME} WHERE company = ?", (company,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "Input Company Name": row[0],
            "Matched Domain": row[1],
            "Website URL": row[2],
            "Confidence Score": row[3],
            "LinkedIn URL": row[4],
            "LinkedIn Description": row[5],
            "WHOIS Created": row[6],
            "WHOIS Expiry": row[7],
            "WHOIS Registrar": row[8],
            "Logo URL": row[9],
            "Country": row[10],
            "OpenCorporates Info": row[11]
        }
    return None

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

def get_cached_url(company, keyword=""):
    search_terms = company.strip().split()
    if keyword:
        search_terms += keyword.strip().split()
    search_query = "+".join(search_terms)
    search_url = f"https://www.google.com/search?q={search_query}"
    return f"https://webcache.googleusercontent.com/search?q=cache:{search_url}"

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        st.error(f"Error fetching {url}: {str(e)}")
        return None

def extract_website_info(soup):
    if not soup:
        return None, 0
    for div in soup.find_all('div', class_='g'):
        a = div.find('a', href=True)
        if a:
            href = a['href']
            if href.startswith('/url?q='):
                url = href.split('/url?q=')[1].split('&')[0]
                url = requests.utils.unquote(url)
                if 'google.com' not in url:
                    return url, 100
    return None, 0

def extract_linkedin_info(soup):
    linkedin_url = None
    description = None
    if not soup:
        return None, None
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'linkedin.com/company' in href or 'linkedin.com/in' in href:
            linkedin_url = href
            break
    meta = soup.find('meta', attrs={'name': 'description'})
    description = meta.get('content') if meta else None
    return linkedin_url, description

def extract_domain(url):
    if not url:
        return ""
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}" if ext.domain and ext.suffix else ""

def fetch_whois_data(domain):
    try:
        data = whois.whois(domain)
        created = data.creation_date[0] if isinstance(data.creation_date, list) else data.creation_date
        expires = data.expiration_date[0] if isinstance(data.expiration_date, list) else data.expiration_date
        registrar = data.registrar if data.registrar else ""
        return (
            str(created) if created else "",
            str(expires) if expires else "",
            registrar
        )
    except Exception as e:
        return "", "", ""

def geolocate_domain(domain):
    try:
        geolocator = Nominatim(user_agent="company_enrichment_tool")
        location = geolocator.geocode(domain.split('.')[-1])
        return location.address if location else ""
    except:
        return ""

def fetch_logo(domain):
    return f"{CLEARBIT_LOGO_API}{domain}" if domain else ""

def open_corporates_scrape(company):
    try:
        url = f"https://opencorporates.com/companies?q={company.replace(' ', '+')}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        result = soup.find('div', class_='search-results')
        return result.find('a').text.strip() if result else ""
    except:
        return ""

def fuzzy_match(company_name, extracted_domain):
    return fuzz.partial_ratio(company_name.lower(), extracted_domain.lower())

def enrich(company):
    cached = get_from_cache(company)
    if cached:
        return cached

    # Get company website
    soup_main = fetch_html(get_cached_url(company))
    website_url, confidence = extract_website_info(soup_main)
    domain = extract_domain(website_url) if website_url else ""
    fuzzy_score = fuzzy_match(company, domain) if domain else 0

    # Get LinkedIn info
    soup_linkedin = fetch_html(get_cached_url(company, "Linkedin"))
    linkedin_url, linkedin_desc = extract_linkedin_info(soup_linkedin)

    # Get WHOIS data
    whois_created, whois_expires, registrar = fetch_whois_data(domain) if domain else ("", "", "")

    # Additional data
    logo_url = fetch_logo(domain)
    country = geolocate_domain(domain)
    open_corp_info = open_corporates_scrape(company)

    result = {
        "Input Company Name": company,
        "Matched Domain": domain,
        "Website URL": website_url or "",
        "Confidence Score": fuzzy_score,
        "LinkedIn URL": linkedin_url or "",
        "LinkedIn Description": linkedin_desc or "",
        "WHOIS Created": whois_created,
        "WHOIS Expiry": whois_expires,
        "WHOIS Registrar": registrar,
        "Logo URL": logo_url,
        "Country": country,
        "OpenCorporates Info": open_corp_info
    }

    save_to_cache(result)
    return result

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

init_db()
st.set_page_config("Company Enrichment Pro", layout="wide")
st.title("🧠 Company Enrichment Tool (Pro Edition)")
st.markdown("Upload a CSV with `Company Name` column to begin.")

uploaded_file = st.file_uploader("📁 Upload CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if "Company Name" not in df.columns:
        st.error("CSV must contain a 'Company Name' column.")
    else:
        if st.button("🚀 Start Enrichment"):
            companies = df["Company Name"].dropna().unique().tolist()
            results = []
            progress = st.progress(0)
            status = st.empty()

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(enrich, company): company for company in companies}
                for i, future in enumerate(as_completed(futures)):
                    company = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        st.error(f"Error processing {company}: {str(e)}")
                    progress.progress((i+1)/len(companies))
                    status.write(f"Processed {i+1}/{len(companies)}: {company}")

            df_out = pd.DataFrame(results)
            st.success("✅ Enrichment Complete!")

            # Convert logo URLs to HTML images
            df_out['Logo URL'] = df_out['Logo URL'].apply(lambda x: f'<img src="{x}" width="50">' if x else "")
            
            st.markdown(df_out.to_html(escape=False, index=False), unsafe_allow_html=True)
            
            excel_data = to_excel(df_out)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name="enriched_companies.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )