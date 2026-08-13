import os
import requests
from pathlib import Path

# Constants for the polite scraper
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/mianhasssan/books-to-scrape-pipeline)"
TIMEOUT_SECONDS = 5
CACHE_DIR = Path("../cache")
CATALOGUE_PAGE_1_URL = "https://books.toscrape.com/catalogue/page-1.html"

def fetch_and_cache_page(url, cache_filename):
    """Fetches a page politely or loads it from cache if it exists."""
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    # If we already have the file, load from cache
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        print("CACHE HIT")
        print(f"Response size: {len(html_content)} bytes")
        return html_content

    # Otherwise, fetch it politely from the internet
    print("FETCH")
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        
        # Check status code. Only 200 means "here is your page"
        if response.status_code != 200:
            print(f"Failed to fetch {url} - Status Code: {response.status_code}")
            return None
            
        html_content = response.text
        
        # Save to cache
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"Response size: {len(html_content)} bytes")
        return html_content
        
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

def main():
    # Stage 1 Checkpoint
    html = fetch_and_cache_page(CATALOGUE_PAGE_1_URL, "catalogue-page-1.html")

if __name__ == "__main__":
    main()
