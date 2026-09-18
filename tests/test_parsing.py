"""Offline tests for URL building and item normalization.

Samples are trimmed from real Flipkart parsed responses for two categories, to
lock in the category-varying behaviour: a clean fashion listing and a noisier
electronics listing where the parser occasionally files spec bullets under
price/rating keys.
"""

from __future__ import annotations

import json

from flipkart_scraper import build_search_url, normalize_item, to_json
from flipkart_scraper.scraper import (
    _discount_percent,
    _price_number,
    _product_id,
    _rating,
)

# Fashion listing: clean, fully-populated core fields.
SHOE_ITEM = {
    "brand": "HRX by Hrithik Roshan",
    "title": "Lightweight Training & Gym Shoes For Men",
    "price": {"value": 859, "currency": None},
    "original_price": {"value": 4999, "currency": None},
    "discount": "82% off",
    "offer": "Only few left",
    "url": "https://www.flipkart.com/hrx-shoes/p/itm123abc?pid=SHOABCD1234EFGH&marketplace=FLIPKART",
    "image": "https://rukminim2.flixcart.com/image/hrx.jpeg",
}

# Electronics listing: rich spec bullets, but the parser mislabels `mrp`
# (a display spec) and `rating` (a processor string) on some rows.
LAPTOP_ITEM = {
    "title": "HP 15 AMD Ryzen 5 - (8 GB/512 GB SSD/Windows 11)",
    "url": "https://www.flipkart.com/hp-15-laptop/p/itm044828973e180?pid=COMHH6Q4E6HYUUBW",
    "image": "https://rukminim2.flixcart.com/image/hp.jpeg",
    "price": {"value": 58990, "currency": None},
    "mrp": "39.62 cm (15.6 inch) Display",  # mislabeled spec bullet, not a price
    "discount": "34% off",
    "processor": "AMD Ryzen 5 Processor",
    "ram": "8 GB DDR4 RAM",
    "operating_system": "64 bit Windows 11 Operating System",
    "storage": "512 GB SSD",
    "display": "39.62 cm (15.6 inch) Display",
    "rating": "AMD Ryzen 5 Processor",  # mislabeled spec bullet, not a rating
}

# Electronics row where `mrp` really is a price (Indian grouping) and rating real.
LAPTOP_ITEM_REAL_MRP = {
    "title": "GIGABYTE A16 AMD Ryzen 7",
    "url": "https://www.flipkart.com/gigabyte-a16/p/itme0ecd838c7545?pid=COMHPQ7ZHBNU9UBW",
    "price": {"value": 134990, "currency": None},
    "mrp": "2,07,000",
    "discount": "34% off",
    "rating": "4.2",
}


def test_build_search_url_encodes_query():
    assert build_search_url("running shoes") == "https://www.flipkart.com/search?q=running+shoes"


def test_build_search_url_passes_through_full_url():
    url = "https://www.flipkart.com/search?q=laptop&page=2"
    assert build_search_url(url) == url
    assert build_search_url("  " + url + "  ") == url


def test_normalize_fashion_item():
    p = normalize_item(SHOE_ITEM)
    assert p.brand == "HRX by Hrithik Roshan"
    assert p.price == 859.0
    assert p.currency == "INR"  # parser leaves currency null; we stamp INR
    assert p.original_price == 4999.0
    assert p.discount_percent == 82
    assert p.offer == "Only few left"
    assert p.product_id == "SHOABCD1234EFGH"  # from the pid= param
    assert p.rating is None


def test_normalize_electronics_drops_mislabeled_fields():
    p = normalize_item(LAPTOP_ITEM)
    assert p.price == 58990.0
    assert p.discount_percent == 34
    # `mrp` here is a display spec, not a price -> rejected, not mis-parsed.
    assert p.original_price is None
    # `rating` here is a processor string -> dropped, not surfaced as a rating.
    assert p.rating is None
    # The key specs still live in the title, which we keep verbatim.
    assert p.title.startswith("HP 15 AMD Ryzen 5")


def test_normalize_electronics_real_mrp_and_rating():
    p = normalize_item(LAPTOP_ITEM_REAL_MRP)
    assert p.original_price == 207000.0  # "2,07,000" Indian grouping parses
    assert p.rating == 4.2
    assert p.product_id == "COMHPQ7ZHBNU9UBW"


def test_price_number_rejects_non_prices():
    assert _price_number({"value": 550}) == 550.0
    assert _price_number("2,07,000") == 207000.0
    assert _price_number("₹1,999") == 1999.0
    assert _price_number("39.62 cm (15.6 inch) Display") is None
    assert _price_number("1 Year Carry-in Warranty") is None
    assert _price_number("MyASUS") is None
    assert _price_number(None) is None


def test_discount_and_rating_helpers():
    assert _discount_percent("82% off") == 82
    assert _discount_percent("Hot Deal") is None
    assert _discount_percent(37) == 37
    assert _rating("4.2") == 4.2
    assert _rating("AMD Ryzen 5 Processor") is None
    assert _rating("9.9") is None  # out of the 0-5 star range


def test_product_id_prefers_pid_then_path():
    assert _product_id("https://www.flipkart.com/x/p/itmabc?pid=COMXYZ") == "COMXYZ"
    assert _product_id("https://www.flipkart.com/x/p/itmabc123def") == "itmabc123def"
    assert _product_id("https://www.flipkart.com/x") is None
    assert _product_id(None) is None


def test_to_json_is_valid_and_ordered():
    text = to_json([normalize_item(SHOE_ITEM)])
    rows = json.loads(text)
    assert rows[0]["brand"] == "HRX by Hrithik Roshan"
    assert rows[0]["price"] == 859.0
    assert rows[0]["product_id"] == "SHOABCD1234EFGH"
