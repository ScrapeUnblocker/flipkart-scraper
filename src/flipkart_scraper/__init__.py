"""flipkart-scraper — clean Flipkart product data via the ScrapeUnblocker API.

Scrape Flipkart search results into clean, typed JSON: title, brand, price and
currency, struck-through price, discount, star rating, offer, product id, URL and
image. Powered by the ScrapeUnblocker ``getPageSource`` parsed-data API, which
renders the page in a real browser and returns AI-parsed structured data — so
you never touch HTML selectors.

Example:
    >>> from flipkart_scraper import FlipkartScraper
    >>> scraper = FlipkartScraper()                  # reads SCRAPEUNBLOCKER_KEY
    >>> products = scraper.scrape(["running shoes"])  # doctest: +SKIP
    >>> products[0].brand                             # doctest: +SKIP
    'HRX by Hrithik Roshan'
"""

from __future__ import annotations

from .scraper import (
    FlipkartScraper,
    Product,
    build_search_url,
    normalize_item,
    products_to_dicts,
    to_csv,
    to_json,
)

__all__ = [
    "FlipkartScraper",
    "Product",
    "build_search_url",
    "normalize_item",
    "products_to_dicts",
    "to_csv",
    "to_json",
]

__version__ = "0.1.0"
