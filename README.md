# flipkart-scraper

[![CI](https://github.com/ScrapeUnblocker/flipkart-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/ScrapeUnblocker/flipkart-scraper/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Scrape Flipkart search results into clean, typed JSON or CSV — no HTML selectors, no blocks.**

Give it a search term (or a full Flipkart URL) and get back a tidy list of
products: title, brand, price and currency, struck-through price, discount,
star rating, offer, product id, URL and image.

> **Powered by [ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos).**
> Flipkart is rendered in a real browser and returned as AI-parsed structured
> data through the [`getPageSource` parsed-data API](https://docs.scrapeunblocker.com/guides/parsed-data?utm_source=github&utm_medium=integration&utm_campaign=example-repos),
> so this library never scrapes raw HTML or maintains brittle CSS selectors.

## Features

- 🔎 **Search or browse** — pass a free-text query (`"running shoes"`) or a full
  Flipkart search/category URL.
- 🧱 **Clean, typed output** — a `Product` dataclass with consistent core fields;
  export to JSON or CSV in one call.
- 🧩 **Category-aware & validated** — Flipkart returns a different field set per
  category (fashion vs. electronics). The scraper normalizes the stable core that
  is reliable everywhere and validates every value, so a stray electronics spec
  bullet can never leak in as a fake price or rating. Key specs stay in the
  `title` (e.g. `"… (16 GB/512 GB SSD/Windows 11)"`).
- 📄 **Clean pagination** — follows Flipkart's `&page=N` links with `--pages`.
- ♻️ **Multi-query + de-dupe** — merge several searches and drop duplicate
  products by Flipkart product id.
- 🔁 **Resilient** — automatic retries with backoff on transient upstream errors.
- 🖥️ **CLI + library** — use `flipkart-scraper` from the shell or import it in Python.

## Install

```bash
pip install .
# or, for development:
pip install -e ".[dev]"
```

Set your ScrapeUnblocker API key (grab one from your
[dashboard](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)):

```bash
cp .env.example .env          # then edit it, or just export the variable:
export SCRAPEUNBLOCKER_KEY=your_key_here
```

## CLI usage

```bash
# Search and print JSON to stdout
flipkart-scraper "running shoes"

# Merge multiple queries, follow 2 pages each, cap at 60 products
flipkart-scraper "laptop" "headphones" --pages 2 --limit 60

# Export to CSV
flipkart-scraper "sarees" --format csv --output sarees.csv

# Scrape a full search URL, pretty-printed
flipkart-scraper "https://www.flipkart.com/search?q=coffee+maker" --pretty
```

```
usage: flipkart-scraper [-h] [-c ISO] [-p PAGES] [-n LIMIT] [-f {json,csv}]
                        [-o PATH] [--pretty] [--version]
                        QUERY [QUERY ...]
```

Flipkart is an India-only storefront, so requests default to routing through
India (`--country IN`).

## Library usage

```python
from flipkart_scraper import FlipkartScraper, to_csv

scraper = FlipkartScraper()  # reads SCRAPEUNBLOCKER_KEY
products = scraper.scrape(
    ["running shoes", "sneakers"],  # queries and/or full Flipkart URLs
    proxy_country="IN",
    pages=2,
    limit=60,
)

for p in products:
    print(p.brand, p.title, p.price, p.discount_percent)

to_csv(products, "flipkart.csv")
```

## Example output

```json
[
  {
    "title": "HRX by Hrithik Roshan RC-21E Running Shoes For Men",
    "brand": "HRX by Hrithik Roshan",
    "price": 859.0,
    "currency": "INR",
    "original_price": 4999.0,
    "discount_percent": 82,
    "rating": null,
    "offer": "Only few left",
    "product_id": "SHOHZJZ8QHMERFXF",
    "url": "https://www.flipkart.com/hrx-.../p/itm...?pid=SHOHZJZ8QHMERFXF",
    "image": "https://rukminim2.flixcart.com/image/.../...jpeg"
  }
]
```

Every field is validated. On electronics listings — where Flipkart's parsed
layout occasionally files a spec bullet under a price or rating key — those
values are rejected rather than surfaced as fake data (the specs remain in the
`title`, e.g. `"HP 15 AMD Ryzen 5 - (8 GB/512 GB SSD/Windows 11)"`).

## Project layout

```
src/flipkart_scraper/
  __init__.py      package exports + version
  scraper.py       Product model, FlipkartScraper, normalization, JSON/CSV export
  cli.py           argparse command-line interface
examples/          runnable scripts (search → JSON, CSV export, best deals)
tests/             offline unit tests (SDK mocked — no API credit spent)
```

## Development

```bash
make install       # editable install with dev deps
make lint          # ruff check
make format        # ruff format
make test          # pytest (offline; the SDK is mocked)
make run           # run the search → JSON example (needs SCRAPEUNBLOCKER_KEY)
```

The test suite mocks the ScrapeUnblocker client, so `make test` runs fully
offline and spends no API credits.

## Links

- 🌐 [ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
- 📚 [Documentation](https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
- 🧠 [Parsed-data guide](https://docs.scrapeunblocker.com/guides/parsed-data?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
- 🐍 [Python SDK](https://docs.scrapeunblocker.com/sdks/python?utm_source=github&utm_medium=integration&utm_campaign=example-repos)

## Legal

For research and educational use. Respect Flipkart's Terms of Service and
`robots.txt`, and applicable laws, when scraping. This project is not affiliated
with or endorsed by Flipkart Internet Private Limited.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 ScrapeUnblocker.
