"""Offline tests for FlipkartScraper: de-dupe, pagination, retry — fake client."""

from __future__ import annotations

import pytest

from flipkart_scraper import FlipkartScraper, Product


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeClient:
    """Records calls and returns queued responses (or raises queued errors)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, str | None]] = []

    def get_parsed(self, url, proxy_country=None):
        self.calls.append((url, proxy_country))
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResult(item)


def _item(pid, title="Flipkart Item"):
    return {
        "title": title,
        "price": {"value": 999, "currency": None},
        "url": f"https://www.flipkart.com/x/p/itmabc?pid={pid}",
    }


class Transient(Exception):
    """Stand-in for a retryable SDK error (simple ctor, offline-safe)."""


def test_scrape_returns_products_and_passes_country():
    client = FakeClient([{"items": [_item("AA1"), _item("BB2")]}])
    scraper = FlipkartScraper(client=client)
    products = scraper.scrape(["running shoes"], proxy_country="IN")

    assert len(products) == 2
    assert all(isinstance(p, Product) for p in products)
    assert client.calls[0][0] == "https://www.flipkart.com/search?q=running+shoes"
    assert client.calls[0][1] == "IN"


def test_default_country_is_india():
    client = FakeClient([{"items": [_item("AA1")]}])
    FlipkartScraper(client=client).scrape(["x"])
    assert client.calls[0][1] == "IN"


def test_scrape_dedupes_across_queries_by_product_id():
    dupe = _item("AA1")
    client = FakeClient([{"items": [dupe]}, {"items": [dupe, _item("CC3")]}])
    scraper = FlipkartScraper(client=client)
    products = scraper.scrape(["one", "two"])
    assert len(products) == 2  # the shared pid is collapsed


def test_limit_stops_collection_early():
    items = [_item("AA1"), _item("BB2"), _item("CC3")]
    client = FakeClient([{"items": items}])
    scraper = FlipkartScraper(client=client)
    products = scraper.scrape(["x"], limit=2)
    assert len(products) == 2


def test_pagination_follows_next_page():
    client = FakeClient(
        [
            {"items": [_item("AA1")], "next_page": "https://www.flipkart.com/search?q=x&page=2"},
            {"items": [_item("BB2")], "next_page": None},
        ]
    )
    scraper = FlipkartScraper(client=client)
    products = scraper.scrape(["x"], pages=3)
    assert len(products) == 2
    assert client.calls[1][0].endswith("page=2")


def test_retries_transient_then_succeeds():
    sleeps: list[float] = []
    client = FakeClient([Transient(), Transient(), {"items": [_item("AA1")]}])
    scraper = FlipkartScraper(
        client=client,
        retries=2,
        backoff=0.5,
        transient_errors=(Transient,),
        sleep=sleeps.append,
    )
    products = scraper.scrape(["x"])
    assert len(products) == 1
    assert sleeps == [0.5, 1.0]  # linear backoff


def test_retries_exhausted_reraises():
    client = FakeClient([Transient(), Transient(), Transient()])
    scraper = FlipkartScraper(
        client=client, retries=1, transient_errors=(Transient,), sleep=lambda _s: None
    )
    with pytest.raises(Transient):
        scraper.scrape(["x"])


def test_non_transient_error_is_not_retried():
    client = FakeClient([ValueError("boom")])
    scraper = FlipkartScraper(client=client, transient_errors=(Transient,), sleep=lambda _s: None)
    with pytest.raises(ValueError):
        scraper.scrape(["x"])
    assert len(client.calls) == 1
