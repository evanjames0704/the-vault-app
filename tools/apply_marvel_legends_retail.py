"""Attach original retail prices from public checklist HTML to existing editions."""
import argparse
import html
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

RETAIL_SOURCE = "Legendsverse original retail"


def collect_prices(pages):
    candidates = {}
    for contents, expected_page in pages:
        match = re.search(r':initial-packagings="([^"]+)"', contents)
        if not match:
            continue
        data = json.loads(html.unescape(match[1]))
        if expected_page is not None and expected_page != data["current_page"]:
            raise ValueError(f"Expected checklist page {expected_page}")
        for row in data["data"]:
            try:
                amount = Decimal(str(row["retail_price"]))
            except InvalidOperation:
                continue
            if row["line_slug"] != "marvel-legends" or not amount.is_finite() or not 0 < amount <= 10000:
                continue
            key = (str(row["id"]), row["name"], str(row["release_year"]), row["slug"])
            candidates.setdefault(key, set()).add(float(amount))
    return {key: next(iter(prices)) for key, prices in candidates.items() if len(prices) == 1}


def apply_prices(items, prices):
    matched = 0
    for item in items:
        slug = item["sourceUrl"].rstrip("/").rsplit("/", 1)[-1]
        key = (str(item.get("identifier", "")), item["name"], str(item["year"]), slug)
        if key in prices:
            item.update(retailPrice=prices[key], currency="USD", priceSource=RETAIL_SOURCE)
            matched += 1
    return matched


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("pages", nargs="+", type=Path)
    args = parser.parse_args()
    pages = ((page.read_text(encoding="utf-8"), int(page.stem) if page.stem.isdecimal() else None)
             for page in args.pages)
    prices = collect_prices(pages)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    matched = apply_prices(catalog["items"], prices)
    args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{matched} of {len(catalog['items'])} catalog editions matched on ID, name, year and URL")


if __name__ == "__main__":
    main()
