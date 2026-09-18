"""Command-line interface for flipkart-scraper.

Examples:
    flipkart-scraper "running shoes"
    flipkart-scraper "laptop" "headphones" --pages 2 --limit 60
    flipkart-scraper "sarees" --format csv --output sarees.csv
    flipkart-scraper "https://www.flipkart.com/search?q=coffee+maker" --pretty
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from .scraper import FlipkartScraper, to_csv, to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flipkart-scraper",
        description="Scrape Flipkart product listings into clean JSON or CSV "
        "via the ScrapeUnblocker parsed-data API.",
    )
    parser.add_argument(
        "queries",
        nargs="+",
        metavar="QUERY",
        help="Search term(s) or full Flipkart URL(s). Multiple values are merged and deduplicated.",
    )
    parser.add_argument(
        "-c",
        "--country",
        default="IN",
        metavar="ISO",
        help="Proxy country to route through (default: IN — Flipkart is India-only).",
    )
    parser.add_argument(
        "-p",
        "--pages",
        type=int,
        default=1,
        help="Max pages to follow per query (default: 1).",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="Stop after this many unique products.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="Write to this file instead of stdout.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON (indented).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _write_output(text: str, output: str | None) -> None:
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        # Flipkart titles/offers contain non-ASCII (₹, brand glyphs); force UTF-8
        # so piping on a legacy Windows console does not raise.
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
        print(text)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    scraper = FlipkartScraper()
    products = scraper.scrape(
        args.queries,
        proxy_country=args.country,
        pages=args.pages,
        limit=args.limit,
    )

    if args.format == "csv":
        if not args.output:
            print("error: --format csv requires --output PATH", file=sys.stderr)
            return 2
        to_csv(products, args.output)
        print(f"Wrote {len(products)} products to {args.output}", file=sys.stderr)
        return 0

    text = to_json(products, indent=2 if args.pretty else None)
    _write_output(text, args.output)
    if args.output:
        print(f"Wrote {len(products)} products to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
