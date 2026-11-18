"""Follow continuation links published by a catalog listing."""
import time
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup


def listing_pages(url, next_selector='[rel="next"][href]', next_attribute="href"):
    host = urlsplit(url).hostname
    visited = set()
    with requests.Session() as session:
        session.headers["User-Agent"] = "TheVaultCatalogImporter/1.0"
        while url:
            if url in visited or urlsplit(url).scheme != "https" or urlsplit(url).hostname != host:
                raise ValueError("Unexpected catalog continuation")
            visited.add(url)
            response = session.get(url, timeout=25)
            response.raise_for_status()
            if urlsplit(response.url).hostname != host:
                raise ValueError("Catalog redirected to a different host")
            yield response.text, response.url
            soup = BeautifulSoup(response.text, "html.parser")
            next_link = soup.select_one(next_selector)
            target = next_link.get(next_attribute) if next_link else None
            url = urljoin(response.url, target) if target else None
            if url:
                time.sleep(1)
