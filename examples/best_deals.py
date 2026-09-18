"""Rank a Flipkart search by biggest discount.

Collects a couple of pages, keeps listings that show a struck-through price and
discount, and prints the best deals first — a quick demo of the clean core
fields (price, original_price, discount_percent, brand).

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here   # Windows: set SCRAPEUNBLOCKER_KEY=...
    python examples/best_deals.py
"""

from __future__ import annotations

from flipkart_scraper import FlipkartScraper


def main() -> None:
    scraper = FlipkartScraper()
    products = scraper.scrape(["running shoes"], proxy_country="IN", pages=2)

    deals = sorted(
        (p for p in products if p.discount_percent and p.original_price),
        key=lambda p: p.discount_percent or 0,
        reverse=True,
    )
    print(f"{len(products)} products, {len(deals)} on sale — best deals first\n")
    for p in deals[:10]:
        brand = f"{p.brand} — " if p.brand else ""
        print(f"[-{p.discount_percent}%] ₹{p.price} (was ₹{p.original_price})  {brand}{p.title}")


if __name__ == "__main__":
    main()
