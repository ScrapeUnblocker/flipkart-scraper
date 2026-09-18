"""Offline tests for the argparse CLI, with FlipkartScraper monkeypatched."""

from __future__ import annotations

import json

import pytest

from flipkart_scraper import Product, cli


class StubScraper:
    """Replaces FlipkartScraper; records the scrape() kwargs it was called with."""

    last_kwargs: dict = {}

    def __init__(self, *args, **kwargs):
        pass

    def scrape(self, queries, **kwargs):
        StubScraper.last_kwargs = {"queries": list(queries), **kwargs}
        return [
            Product(title="HRX Running Shoes", brand="HRX", price=859.0, currency="INR"),
            Product(title="HP 15 Laptop", price=58990.0, currency="INR", discount_percent=34),
        ]


@pytest.fixture(autouse=True)
def _patch_scraper(monkeypatch):
    monkeypatch.setattr(cli, "FlipkartScraper", StubScraper)


def test_parser_defaults():
    args = cli.build_parser().parse_args(["running shoes"])
    assert args.queries == ["running shoes"]
    assert args.country == "IN"
    assert args.pages == 1
    assert args.format == "json"


def test_parser_accepts_multiple_queries_and_flags():
    argv = ["laptop", "headphones", "-c", "IN", "-p", "2", "-n", "60"]
    args = cli.build_parser().parse_args(argv)
    assert args.queries == ["laptop", "headphones"]
    assert args.pages == 2
    assert args.limit == 60


def test_json_output_to_stdout(capsys):
    rc = cli.main(["running shoes"])
    assert rc == 0
    out = capsys.readouterr().out
    rows = json.loads(out)
    assert rows[0]["brand"] == "HRX"
    assert StubScraper.last_kwargs["proxy_country"] == "IN"


def test_json_output_to_file(tmp_path):
    out = tmp_path / "out.json"
    rc = cli.main(["laptop", "--output", str(out), "--pretty"])
    assert rc == 0
    rows = json.loads(out.read_text(encoding="utf-8"))
    assert len(rows) == 2


def test_csv_requires_output():
    rc = cli.main(["laptop", "--format", "csv"])
    assert rc == 2


def test_csv_output_to_file(tmp_path):
    out = tmp_path / "out.csv"
    rc = cli.main(["laptop", "--format", "csv", "--output", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "title,brand,price" in text.replace(" ", "")
    assert "HRX Running Shoes" in text
