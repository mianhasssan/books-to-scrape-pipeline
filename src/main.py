import os
import requests
import time
import json
from datetime import datetime, timezone
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

def extract_book_details(html, product_url, source_page):
    """Extracts the 8 required fields from a book's detail page."""
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. title
    title_element = soup.select_one(".product_main h1")
    title = title_element.text if title_element else None
    
    # 2. product_url (passed in)
    
    # 3. price_text
    price_element = soup.select_one(".product_main .price_color")
    price_text = price_element.text if price_element else None
    
    # 4. availability_text
    availability_element = soup.select_one(".product_main .instock.availability")
    availability_text = availability_element.text.strip() if availability_element else None
    
    # 5. rating_text
    rating_element = soup.select_one(".product_main .star-rating")
    rating_text = None
    if rating_element:
        # The classes are usually like ["star-rating", "Three"]
        classes = rating_element.get("class", [])
        if len(classes) > 1:
            rating_text = classes[1]
            
    # 6. description
    description_element = soup.select_one("#product_description ~ p")
    description = description_element.text if description_element else None
    
    # 7. source_page (passed in)
    
    # 8. fetched_at (ISO format, UTC)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }

def main():
    catalogue_pages_visited = 0
    # Dictionary to map absolute_url -> source_catalogue_url
    discovered_urls = {}
    
    current_url = START_URL
    
    # Stage 2: Find all three pages
    while current_url and catalogue_pages_visited < 3:
        filename = current_url.split("/")[-1]
        html = fetch_and_cache_page(current_url, filename)
        if not html:
            break
            
        catalogue_pages_visited += 1
        soup = BeautifulSoup(html, "html.parser")
        
        book_links = soup.select("article.product_pod h3 a")
        for link in book_links:
            relative_url = link.get("href")
            absolute_url = urljoin(current_url, relative_url)
            
            # Save the url and where we found it (deduplicates automatically)
            if absolute_url not in discovered_urls:
                discovered_urls[absolute_url] = current_url
            
        next_button = soup.select_one("li.next a")
        if next_button:
            next_relative_url = next_button.get("href")
            current_url = urljoin(current_url, next_relative_url)
        else:
            current_url = None

    # Stage 3: Extract the raw records
    raw_records = []
    
    for book_url, source_catalogue_url in discovered_urls.items():
        # Create a safe filename for cache using the book's unique ID/folder name
        # URL format: https://books.toscrape.com/catalogue/book-title_1000/index.html
        parts = book_url.split("/")
        book_id = parts[-2] if len(parts) > 1 else parts[-1]
        filename = f"book-{book_id}.html"
        
        book_html = fetch_and_cache_page(book_url, filename)
        if book_html:
            record = extract_book_details(book_html, book_url, source_catalogue_url)
            raw_records.append(record)

    # Checkpoint output
    if raw_records:
        print(json.dumps(raw_records[0], indent=2))
    
    print(f"\ndetail_pages={len(raw_records)}")

if __name__ == "__main__":
    main()
