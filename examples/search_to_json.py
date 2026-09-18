"""Search Flipkart and print the results as JSON.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here   # Windows: set SCRAPEUNBLOCKER_KEY=...
    python examples/search_to_json.py
"""

from __future__ import annotations

from flipkart_scraper import FlipkartScraper, to_json


def main() -> None:
    scraper = FlipkartScraper()  # reads SCRAPEUNBLOCKER_KEY from the environment
    products = scraper.scrape(["running shoes"], proxy_country="IN")

    print(f"Found {len(products)} products\n")
    print(to_json(products[:5]))


if __name__ == "__main__":
    main()
