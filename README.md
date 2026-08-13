# The Polite Scraper

## Target Classification
* **Site:** Books to Scrape (books.toscrape.com)
* **Why:** It is a practice sandbox designed specifically for testing scraping tools without affecting real businesses.
* **Scope:** The first 3 catalogue pages.
* **Data Collected:** Book details including title, price, availability, rating, and description.
* **Robots.txt:** We checked for `https://books.toscrape.com/robots.txt` but no robots file was found (404 Not Found). A missing file is not explicit permission, it is just a missing file.
* **Ethics:** I will not reuse this code on another site without checking its rules and terms first.

## Installation and Execution (Python Lane)
To install the dependencies:
```bash
pip install -r requirements.txt
```

To run the scraper:
```bash
python src/main.py
```

## Record Schema
The data is validated using Pydantic before storage. The schema ensures data integrity and types:
```python
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
```

## Politeness Rules Followed
* **User-Agent:** We send an honest `FlyRankInternship-A9/1.0 (+link-to-repo)` header so the site owner knows who we are.
* **Delay:** We wait `0.5` seconds after every real network request.
* **Timeout:** We strictly enforce a `5` second timeout so we never hold the server hostage.
* **Cache:** All HTML is saved to a local `cache/` folder. Subsequent runs read from disk, meaning zero network load during development.

## Limitations
**One honest limitation:** The scraper is strictly synchronous and sequential. It processes one page at a time. While polite, this architecture would be incredibly slow if we needed to scale this to 1,000,000 pages.

## Run Report Evidence
Here is a real run report demonstrating the scraper's execution (including the handling of one deliberately injected broken URL):
```json
{
  "start_time": "2026-08-13T15:23:48Z",
  "duration_seconds": 4.62,
  "pages_fetched": 1,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```
**Why no browser?** This assignment needed no browser because all the necessary book data is already present in the raw HTML the server sends. Spinning up a headless browser (like Playwright or Puppeteer) would only add massive CPU and memory costs for absolutely no benefit.

## Ethics Note
Always use an official API when one exists. Never bypass logins, paywalls, or blocks. Collect only what you strictly need, and nothing more.
