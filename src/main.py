import os
import requests
import time
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Constants for the polite scraper
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/your-username/your-repo)"
TIMEOUT_SECONDS = 5
DELAY_SECONDS = 0.5
CACHE_DIR = Path("../cache")
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

def fetch_and_cache_page(url, cache_filename):
    """Fetches a page politely or loads it from cache if it exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    # If we already have the file, load from cache
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    # Otherwise, fetch it politely from the internet
    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        
        if response.status_code != 200:
            print(f"Failed to fetch {url} - Status Code: {response.status_code}")
            return None
            
        html_content = response.text
        
        # Save to cache
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        # Polite delay ONLY after making a real network request
        time.sleep(DELAY_SECONDS)
            
        return html_content
        
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

def main():
    catalogue_pages_visited = 0
    discovered_urls = []
    
    current_url = START_URL
    
    # Loop up to 3 times to get the first three catalogue pages
    while current_url and catalogue_pages_visited < 3:
        # Create a safe filename from the URL, e.g. "page-1.html"
        filename = current_url.split("/")[-1]
        
        html = fetch_and_cache_page(current_url, filename)
        if not html:
            break
            
        catalogue_pages_visited += 1
        
        # Parse the page with Beautiful Soup
        soup = BeautifulSoup(html, "html.parser")
        
        # Collect book links (they are inside <article class="product_pod"> -> <h3> -> <a>)
        book_links = soup.select("article.product_pod h3 a")
        for link in book_links:
            relative_url = link.get("href")
            # Turn relative URL into absolute URL using urljoin
            absolute_url = urljoin(current_url, relative_url)
            discovered_urls.append(absolute_url)
            
        # Find the "next" page link to continue crawling
        next_button = soup.select_one("li.next a")
        if next_button:
            next_relative_url = next_button.get("href")
            current_url = urljoin(current_url, next_relative_url)
        else:
            current_url = None
            
    # Remove duplicates before the next stage
    unique_urls = list(set(discovered_urls))
    
    # Stage 2 Checkpoint output
    print(f"catalogue_pages={catalogue_pages_visited}")
    print(f"discovered={len(discovered_urls)}")
    print(f"unique_urls={len(unique_urls)}")

if __name__ == "__main__":
    main()
