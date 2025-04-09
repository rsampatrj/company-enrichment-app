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
import urllib.parse

DB_PATH = "cache.db"
TABLE_NAME = "company_cache"
CLEARBIT_LOGO_API = "https://logo.clearbit.com/"
GOOGLE_SEARCH_URL = "https://www.google.com/search?q="

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

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

def google_search(company):
    try:
        query = urllib.parse.quote_plus(company)
        url = f"{GOOGLE_SEARCH_URL}{query}"
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.error(f"Google search failed: {str(e)}")
        return None

def extract_website_url(html):
    soup = BeautifulSoup(html, 'html.parser')
    main_div = soup.find("div", id="main")
    
    # Find organic results
    for div in main_div.find_all('div', class_='MjjYud'):
        link = div.find('a', href=True)
        if link and 'google.com' not in link['href']:
            href = link['href']
            if href.startswith('/url?q='):
                url = href.split('/url?q=')[1].split('&')[0]
                return urllib.parse.unquote(url)
    return None

def get_company_website(company):
    try:
        html = google_search(company)
        if not html:
            return None, 0
            
        website_url = extract_website_url(html)
        if not website_url:
            return None, 0
            
        return website_url, 100
    except Exception as e:
        st.error(f"Website detection failed: {str(e)}")
        return None, 0

def fetch_cached_page(url):
    try:
        cached_url = f"https://webcache.googleusercontent.com/search?q=cache:{urllib.parse.quote(url)}"
        response = requests.get(cached_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except:
        return None

def extract_linkedin_info(soup):
    if not soup:
        return None, None
        
    linkedin_url = None
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if 'linkedin.com/company' in href or 'linkedin.com/in' in href:
            linkedin_url = a['href']
            break
            
    description = soup.find('meta', attrs={'name': 'description'})
    return linkedin_url, description.get('content') if description else None

# Rest of the functions remain similar with improved error handling...

def enrich(company):
    cached = get_from_cache(company)
    if cached:
        return cached

    # Get company website
    website_url, confidence = get_company_website(company)
    domain = extract_domain(website_url) if website_url else ""
    fuzzy_score = fuzzy_match(company, domain) if domain else 0

    # Get LinkedIn info
    linkedin_url, linkedin_desc = None, None
    if website_url:
        soup = fetch_cached_page(website_url)
        linkedin_url, linkedin_desc = extract_linkedin_info(soup)

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

# Rest of the Streamlit code remains the same...
