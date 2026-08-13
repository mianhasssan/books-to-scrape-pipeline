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

def fetch_and_cache_page(url, cache_filename, run_stats):
    """Fetches a page politely with retries, or loads it from cache if it exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        run_stats["cache_hits"] += 1
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"FETCH: {url}")
    run_stats["pages_fetched"] += 1
    headers = {"User-Agent": USER_AGENT}
    
    for attempt in range(2): # Max 2 attempts (1 initial + 1 retry)
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200:
                html_content = response.text
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                time.sleep(DELAY_SECONDS)
                return html_content
            elif response.status_code in (403, 404):
                print(f"Failed to fetch {url} - Status Code: {response.status_code}. Not retrying.")
                return None
            else:
                print(f"Server error {response.status_code} for {url}. Retrying...")
                time.sleep(1) # Wait a moment before retrying
        except requests.RequestException as e:
            print(f"Request exception for {url}: {e}. Retrying...")
            time.sleep(1)
            
    return None

def extract_book_details(html, product_url, source_page):
    soup = BeautifulSoup(html, "html.parser")
    
    title_element = soup.select_one(".product_main h1")
    title = title_element.text if title_element else None
    
    price_element = soup.select_one(".product_main .price_color")
    price_text = price_element.text if price_element else None
    
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
    start_time = datetime.now(timezone.utc)
    run_stats = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": 0,
        "pages_fetched": 0,
        "cache_hits": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "failed_pages": 0
    }

    catalogue_pages_visited = 0
    discovered_urls = {}
    current_url = START_URL
    
    # Stage 2: Discover URLs
    while current_url and catalogue_pages_visited < 3:
        filename = current_url.split("/")[-1]
        html = fetch_and_cache_page(current_url, filename, run_stats)
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

    # Fake URL deliberately injected to test failure handling (Stage 5)
    discovered_urls["https://books.toscrape.com/catalogue/made-up-book-that-does-not-exist_9999/index.html"] = START_URL

    valid_records = {} 
    errors = []
    
    for book_url, source_catalogue_url in discovered_urls.items():
        parts = book_url.split("/")
        book_id = parts[-2] if len(parts) > 1 else parts[-1]
        filename = f"book-{book_id}.html"
        
        book_html = fetch_and_cache_page(book_url, filename, run_stats)
        
        if not book_html:
            run_stats["failed_pages"] += 1
            print(f"Skipping failed page: {book_url}")
            continue

        raw_record = extract_book_details(book_html, book_url, source_catalogue_url)
        
        try:
            validated_record = BookRecord(**raw_record)
            valid_records[str(validated_record.product_url)] = validated_record.model_dump(mode="json")
            run_stats["valid_records"] += 1
        except ValidationError as e:
            errors.append({
                "record": raw_record,
                "reason": e.errors()
            })
            run_stats["invalid_records"] += 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_DIR / "books.json", "w", encoding="utf-8") as f:
        json.dump(list(valid_records.values()), f, indent=2)
        
    with open(OUTPUT_DIR / "errors.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2)

    # Finalize run report
    end_time = datetime.now(timezone.utc)
    run_stats["duration_seconds"] = round((end_time - start_time).total_seconds(), 2)
    
    with open(OUTPUT_DIR / "run-report.json", "w", encoding="utf-8") as f:
        json.dump(run_stats, f, indent=2)

    # Checkpoint output
    with open(OUTPUT_DIR / "run-report.json", "r", encoding="utf-8") as f:
        report = json.load(f)
        
    print(f"\nrun-report.json shows failed_pages: {report['failed_pages']}")
    print(f"books.json still has {report['valid_records']} good records.")
    print(f"Run completed in {report['duration_seconds']} seconds.")

if __name__ == "__main__":
    main()
