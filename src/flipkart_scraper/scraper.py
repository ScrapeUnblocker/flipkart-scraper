"""Core scraping logic for flipkart-scraper.

The heavy lifting is done by the ScrapeUnblocker ``get_parsed`` endpoint, which
loads a Flipkart page in a real browser and returns AI-parsed structured data.
This module normalizes that data into a clean, stable :class:`Product` shape,
handles multi-page collection with de-duplication, retries transient upstream
errors, and exports to JSON/CSV.

Flipkart returns a *different* field set per product category (a fashion listing
carries ``brand``/``original_price``/``offer``; an electronics listing carries
spec bullets such as ``processor``/``ram``/``storage``). Rather than trust that
volatile, per-row-inconsistent spec layout, we normalize the stable core that is
reliable across every category — title, brand, price, currency, struck-through
price, discount, rating, offer, product id, URL and image — and validate each
value so a stray spec bullet can never leak in as a fake price or rating. The
key electronics specs are already embedded in the ``title`` (e.g.
``"... (16 GB/512 GB SSD/Windows 11)"``).
"""

from __future__ import annotations

import csv
import json
import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Callable
from urllib.parse import parse_qs, quote_plus, urlparse

FLIPKART_SEARCH_URL = "https://www.flipkart.com/search?q={query}"

# Flipkart is an India-only marketplace; prices are quoted in INR and the parser
# leaves the per-item currency null, so we stamp it ourselves.
DEFAULT_CURRENCY = "INR"


def _transient_errors() -> tuple[type[BaseException], ...]:
    """Best-effort tuple of ScrapeUnblocker exceptions worth retrying.

    Imported lazily so the package is usable (and unit-testable) even when the
    ``scrapeunblocker`` SDK is not installed.
    """
    try:
        from scrapeunblocker import (  # type: ignore
            BrowserTimeoutError,
            RateLimitError,
            ScrapeTimeoutError,
            ServerError,
            UpstreamOutageError,
        )
        from scrapeunblocker import (
            ConnectionError as SUConnectionError,
        )
    except Exception:  # pragma: no cover - depends on SDK availability
        return ()
    return (
        UpstreamOutageError,
        RateLimitError,
        ScrapeTimeoutError,
        BrowserTimeoutError,
        ServerError,
        SUConnectionError,
    )


@dataclass
class Product:
    """A single Flipkart product listing.

    ``title``, ``price``, ``currency``, ``url`` and ``image`` are populated for
    every category. ``brand``, ``original_price``, ``discount_percent``,
    ``rating`` and ``offer`` are populated when Flipkart exposes them for that
    category, and are ``None`` otherwise.
    """

    title: str | None = None
    brand: str | None = None
    price: float | None = None
    currency: str | None = None
    original_price: float | None = None
    discount_percent: int | None = None
    rating: float | None = None
    offer: str | None = None
    product_id: str | None = None
    url: str | None = None
    image: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Column order used for CSV export and dict serialization.
FIELDNAMES: tuple[str, ...] = (
    "title",
    "brand",
    "price",
    "currency",
    "original_price",
    "discount_percent",
    "rating",
    "offer",
    "product_id",
    "url",
    "image",
)


def build_search_url(query: str) -> str:
    """Return a Flipkart URL for ``query``.

    A value that already looks like an ``http(s)`` URL is returned unchanged, so
    callers can pass a hand-built search or category URL. Anything else is
    treated as a free-text search term.
    """
    q = query.strip()
    if q.lower().startswith(("http://", "https://")):
        return q
    return FLIPKART_SEARCH_URL.format(query=quote_plus(q))


def _price_number(obj: Any) -> float | None:
    """Coerce a Flipkart price value into a float, or ``None``.

    Accepts a ``{"value": .., "currency": ..}`` dict, a plain number, or a
    numeric string with Indian/Western thousands grouping (``"2,07,000"``).
    Strings that are *not* a bare number (e.g. a spec bullet that the parser
    occasionally files under a price key on electronics listings, like
    ``"39.62 cm (15.6 inch) Display"``) are rejected rather than mis-parsed.
    """
    if isinstance(obj, dict):
        obj = obj.get("value")
    if obj is None or isinstance(obj, bool):
        return None
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, str):
        cleaned = obj.replace(",", "").replace("₹", "").strip()
        if re.fullmatch(r"\d+(\.\d+)?", cleaned):
            return float(cleaned)
    return None


def _currency_of(obj: Any) -> str | None:
    if isinstance(obj, dict):
        cur = obj.get("currency")
        return cur or None
    return None


def _discount_percent(value: Any) -> int | None:
    """Parse ``"34% off"`` -> ``34``."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        n = int(value)
        return n if 0 <= n <= 100 else None
    if isinstance(value, str):
        m = re.search(r"(\d+)\s*%", value)
        if m:
            n = int(m.group(1))
            return n if 0 <= n <= 100 else None
    return None


def _rating(value: Any) -> float | None:
    """Keep a rating only if it is a plausible 0-5 star value.

    On electronics listings the parser sometimes files a spec bullet under the
    ``rating`` key (e.g. ``"AMD Ryzen 7 Processor"``); those fail the numeric /
    range check and are dropped instead of surfaced as a fake rating.
    """
    try:
        r = float(value)
    except (TypeError, ValueError):
        return None
    return r if 0.0 <= r <= 5.0 else None


def _product_id(url: str | None) -> str | None:
    """Return Flipkart's canonical product id from a listing URL.

    Prefers the ``pid`` query parameter (e.g. ``COMHPQ7ZHBNU9UBW``); falls back
    to the ``/p/itm<id>`` path segment.
    """
    if not url:
        return None
    pid = parse_qs(urlparse(url).query).get("pid")
    if pid and pid[0]:
        return pid[0]
    m = re.search(r"/p/(itm[0-9a-z]+)", url)
    return m.group(1) if m else None


def normalize_item(raw: dict[str, Any]) -> Product:
    """Normalize one parsed Flipkart item into a :class:`Product`.

    Reads defensively because the field set varies by category. The sale price
    comes from ``price``; the struck-through price from ``original_price`` (or
    ``mrp`` on some categories). Each numeric value is validated, so a stray
    spec bullet the parser may file under a price/rating key on electronics
    listings is rejected rather than surfaced as fake data.
    """
    price = _price_number(raw.get("price"))
    currency = _currency_of(raw.get("price")) or (raw.get("currency") or None) or DEFAULT_CURRENCY

    original_price = _price_number(raw.get("original_price"))
    if original_price is None:
        original_price = _price_number(raw.get("mrp"))

    url = raw.get("url")

    return Product(
        title=raw.get("title") or None,
        brand=raw.get("brand") or None,
        price=price,
        currency=currency if price is not None else None,
        original_price=original_price,
        discount_percent=_discount_percent(raw.get("discount")),
        rating=_rating(raw.get("rating")),
        offer=(raw.get("offer") or None),
        product_id=_product_id(url),
        url=url,
        image=raw.get("image") or None,
    )


class FlipkartScraper:
    """Scrape Flipkart product listings via ScrapeUnblocker.

    Args:
        api_key: ScrapeUnblocker key. If omitted, the SDK reads
            ``SCRAPEUNBLOCKER_KEY`` from the environment.
        client: A pre-built client (or any object exposing
            ``get_parsed(url, proxy_country=...)``). Mainly for testing.
        retries: Extra attempts on transient upstream errors.
        backoff: Base seconds for linear backoff between retries.
        timeout: Per-request timeout passed to the SDK client.
        transient_errors: Exception classes treated as retryable. Defaults to
            the ScrapeUnblocker transient set.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        retries: int = 2,
        backoff: float = 1.0,
        timeout: float = 180.0,
        transient_errors: Sequence[type[BaseException]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if client is None:
            from scrapeunblocker import Client  # local import: optional dep

            client = Client(api_key=api_key, timeout=timeout)
        self._client = client
        self.retries = max(0, int(retries))
        self.backoff = float(backoff)
        self._transient = (
            tuple(transient_errors) if transient_errors is not None else _transient_errors()
        )
        self._sleep = sleep

    def _fetch(self, url: str, proxy_country: str | None) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                result = self._client.get_parsed(url, proxy_country=proxy_country)
                data = getattr(result, "data", None)
                return data if isinstance(data, dict) else {}
            except self._transient:
                if attempt >= self.retries:
                    raise
                attempt += 1
                self._sleep(self.backoff * attempt)

    def scrape(
        self,
        queries: Iterable[str],
        *,
        proxy_country: str | None = "IN",
        pages: int = 1,
        limit: int | None = None,
    ) -> list[Product]:
        """Scrape one or more queries and return de-duplicated products.

        Args:
            queries: Free-text search terms and/or full Flipkart URLs.
            proxy_country: ISO-3166 country to route through. Flipkart is an
                India-only storefront, so this defaults to ``"IN"``.
            pages: Max pages to follow per query via the parser's ``next_page``
                link (Flipkart paginates cleanly with ``&page=N``).
            limit: Stop once this many unique products are collected.

        Returns:
            A list of :class:`Product`, de-duplicated by product id / URL.
        """
        seen: set[Any] = set()
        products: list[Product] = []

        for query in queries:
            url: str | None = build_search_url(query)
            page = 0
            while url and page < max(1, pages):
                data = self._fetch(url, proxy_country)
                for raw in data.get("items") or []:
                    if not isinstance(raw, dict):
                        continue
                    product = normalize_item(raw)
                    key = product.product_id or product.url or product.title
                    if key is None or key in seen:
                        continue
                    seen.add(key)
                    products.append(product)
                    if limit is not None and len(products) >= limit:
                        return products
                url = data.get("next_page")
                page += 1
        return products


def products_to_dicts(products: Sequence[Product]) -> list[dict[str, Any]]:
    return [p.to_dict() for p in products]


def to_json(products: Sequence[Product], *, indent: int | None = 2) -> str:
    return json.dumps(products_to_dicts(products), indent=indent, ensure_ascii=False)


def to_csv(products: Sequence[Product], path: str) -> None:
    """Write ``products`` to a CSV file at ``path``."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(FIELDNAMES))
        writer.writeheader()
        for product in products:
            writer.writerow(product.to_dict())
