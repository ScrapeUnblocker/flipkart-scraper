"""Collect several Flipkart searches and export a de-duplicated CSV.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here   # Windows: set SCRAPEUNBLOCKER_KEY=...
    python examples/export_csv.py
"""

from __future__ import annotations

from flipkart_scraper import FlipkartScraper, to_csv

QUERIES = ["running shoes", "sports shoes", "sneakers"]
OUTPUT = "flipkart_shoes.csv"


def main() -> None:
    scraper = FlipkartScraper()
    products = scraper.scrape(QUERIES, proxy_country="IN", pages=2)
    to_csv(products, OUTPUT)
    print(f"Wrote {len(products)} unique products across {len(QUERIES)} queries to {OUTPUT}")


if __name__ == "__main__":
    main()
