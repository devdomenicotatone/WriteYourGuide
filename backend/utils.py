# utils.py

import os
import requests
import logging
from bs4 import BeautifulSoup
from fastapi import HTTPException
from dotenv import load_dotenv
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

EXCLUDED_DOMAINS = [
    "tripadvisor.com",
    "reddit.com",
    "openstreetmap.org",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
]

def is_domain_excluded(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    for excluded in EXCLUDED_DOMAINS:
        if excluded in domain:
            return True
    return False

def perform_search(query: str):
    logger.debug(f"Performing Google search for query: {query}")
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise RuntimeError("GOOGLE_API_KEY o GOOGLE_CSE_ID non impostate.")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
    }

    logger.debug(f"Sending request to Google Custom Search API: {url} with params {params}")
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        logger.error(f"Google search failed with status {resp.status_code} and response {resp.text}")
        raise HTTPException(status_code=resp.status_code, detail="Errore nella ricerca")

    data = resp.json()
    logger.debug(f"Received search results: {data}")

    filtered_items = []
    for item in data.get("items", []):
        link = item.get("link")
        if link and not is_domain_excluded(link):
            filtered_items.append(item)
        else:
            logger.info(f"Escludendo il link: {link}")

    data["items"] = filtered_items
    return data

def scrape_article(url: str):
    logger.debug(f"Scraping article from URL: {url}")

    # Rimuovo due punti finali o spazi
    url = url.rstrip(":")

    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/58.0.3029.110 Safari/53.36")
    }

    try:
        r = requests.get(url, timeout=10, headers=headers)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return "", []

    soup = BeautifulSoup(r.text, 'html.parser')

    # Rimuoviamo script, style e noscript
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    # Estrazione del testo principale
    body = soup.find("body")
    if body:
        text = body.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)
    cleaned_text = " ".join(text.split())

    # Estrazione delle immagini
    immagini = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith("https://cdn.getyourguide.com/img/tour"):
            immagini.append(src)

    if not cleaned_text.strip():
        return "", immagini

    return cleaned_text, immagini
