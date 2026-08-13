import os
import re
import requests
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional, List, Dict

# Constants for the polite scraper
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/your-username/your-repo)"
TIMEOUT_SECONDS = 5
DELAY_SECONDS = 0.5
CACHE_DIR = Path("../cache")
OUTPUT_DIR = Path("../output")
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

# Pydantic Schema for a Book Record
class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: Optional[str]
    description: Optional[str]
    source_page: HttpUrl
    fetched_at: str

def fetch_and_cache_page(url, cache_filename):
    """Fetches a page politely or loads it from cache if it exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        if response.status_code != 200:
            print(f"Failed to fetch {url} - Status Code: {response.status_code}")
            return None
        html_content = response.text
        
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        time.sleep(DELAY_SECONDS)
        return html_content
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

def extract_book_details(html, product_url, source_page):
    """Extracts the fields from a book's detail page."""
    soup = BeautifulSoup(html, "html.parser")
    
    title_element = soup.select_one(".product_main h1")
    title = title_element.text if title_element else None
    
    price_element = soup.select_one(".product_main .price_color")
    price_text = price_element.text if price_element else None
    
    # Extract the numeric price from the text (e.g., "£51.77" -> 51.77)
    price_gbp = None
    if price_text:
        match = re.search(r"[\d.]+", price_text)
        if match:
            price_gbp = float(match.group())
            
    availability_element = soup.select_one(".product_main .instock.availability")
    availability_text = availability_element.text.strip() if availability_element else None
    
    rating_element = soup.select_one(".product_main .star-rating")
    rating_text = None
    if rating_element:
        classes = rating_element.get("class", [])
        if len(classes) > 1:
            rating_text = classes[1]
            
    description_element = soup.select_one("#product_description ~ p")
    description = description_element.text if description_element else None
    
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "price_gbp": price_gbp,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }

def main():
    catalogue_pages_visited = 0
    discovered_urls = {}
    current_url = START_URL
    
    # Stage 2: Discover URLs
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
            if absolute_url not in discovered_urls:
                discovered_urls[absolute_url] = current_url
            
        next_button = soup.select_one("li.next a")
        if next_button:
            next_relative_url = next_button.get("href")
            current_url = urljoin(current_url, next_relative_url)
        else:
            current_url = None

    # Stage 3: Extract and Stage 4: Validate
    valid_records = {} # Dict for idempotency (key: product_url)
    errors = []
    
    for book_url, source_catalogue_url in discovered_urls.items():
        parts = book_url.split("/")
        book_id = parts[-2] if len(parts) > 1 else parts[-1]
        filename = f"book-{book_id}.html"
        
        book_html = fetch_and_cache_page(book_url, filename)
        if book_html:
            raw_record = extract_book_details(book_html, book_url, source_catalogue_url)
            
            # Stage 4: Validate against Pydantic schema
            try:
                validated_record = BookRecord(**raw_record)
                # Store using product_url as canonical ID for idempotency
                valid_records[str(validated_record.product_url)] = validated_record.model_dump(mode="json")
            except ValidationError as e:
                # Store the failing record and the reason
                errors.append({
                    "record": raw_record,
                    "reason": e.errors()
                })

    # Stage 4: Output to JSON files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    books_file = OUTPUT_DIR / "books.json"
    with open(books_file, "w", encoding="utf-8") as f:
        json.dump(list(valid_records.values()), f, indent=2)
        
    errors_file = OUTPUT_DIR / "errors.json"
    with open(errors_file, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2)

    # Checkpoint output
    with open(books_file, "r", encoding="utf-8") as f:
        saved_books = json.load(f)
        
    print(f"books.json has {len(saved_books)} records.")
    
    if saved_books:
        first_book = saved_books[0]
        price_val = first_book.get("price_gbp")
        url_val = first_book.get("product_url")
        print(f"Is price_gbp a number? {isinstance(price_val, (int, float))} (Value: {price_val})")
        print(f"Does URL start with https://? {url_val.startswith('https://')} (Value: {url_val})")

if __name__ == "__main__":
    main()
