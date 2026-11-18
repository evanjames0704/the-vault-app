"""Import public Big Toes Collectibles storefront product variants and USD prices."""
import argparse
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

ORIGIN = "https://bigtoescollectibles.com"


def category(title, product_type):
    text = f"{product_type} {title}".casefold()
    for terms, name in [
        (r"\bfunko pop\b", "Funko Pops"),
        (r"\bhot toys\b", "Hot Toys"),
        (r"\baction figures?\b|\bmarvel legends\b|\bdc multiverse\b", "Action figures"),
        (r"\blego\b", "LEGO"),
        (r"\btrading cards?\b|\b(?:pokemon|pokémon)\b.*\b(?:booster|card)\b", "Trading cards"),
        (r"\bstatue\b|\bpremium format\b", "Statues and premium collectibles"),
    ]:
        if re.search(terms, text):
            return name
    return "Other collectibles"


def records(products):
    for product in products:
        title = product["title"].strip()
        handle = product["handle"]
        if not title or not re.fullmatch(r"[a-z0-9-]+", handle):
            raise ValueError("Unexpected Big Toes product title or handle")
        images = {image["id"]: image.get("src", "") for image in product.get("images", [])}
        for variant in product["variants"]:
            identifier = f"bigtoes:{variant['id']}"
            edition = "" if variant["title"] == "Default Title" else variant["title"]
            try:
                price = float(variant["price"])
            except (ValueError, TypeError, KeyError):
                price = 0
            if not math.isfinite(price) or price <= 0 or re.search(
                r"\b(?:deposit|down payment|balance only|installment)\b", f"{title} {edition}", re.I
            ):
                price = None
            image = images.get((variant.get("featured_image") or {}).get("id")) or next(iter(images.values()), "")
            yield {
                "id": identifier, "identifier": identifier, "name": title,
                "variant": edition, "category": category(title, product.get("product_type", "")),
                "brand": product.get("vendor") or "", "retailPrice": price, "currency": "USD",
                "image": image if image.startswith("https://") else "",
                "available": variant.get("available") is True,
                "source": "Big Toes Collectibles",
                "sourceUrl": f"{ORIGIN}/products/{handle}?variant={variant['id']}",
            }


def public_pages():
    import requests

    with requests.Session() as session:
        session.headers["User-Agent"] = "TheVaultCatalogImporter/1.0"
        home = session.get(ORIGIN, timeout=15)
        home.raise_for_status()
        if not re.search(r'Shopify\.currency\s*=\s*\{\s*"active"\s*:\s*"USD"', home.text):
            raise ValueError("Could not verify Big Toes storefront currency")
        for page in range(1, 101):
            response = session.get(f"{ORIGIN}/products.json", params={"limit": 250, "page": page}, timeout=20)
            response.raise_for_status()
            products = response.json()["products"]
            yield products
            if len(products) < 250:
                return
            time.sleep(1)
    raise ValueError("Big Toes catalog exceeded the pagination limit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pages", type=Path, nargs="+", help="Previously fetched USD feed pages in order")
    args = parser.parse_args()
    pages = (json.loads(path.read_text())["products"] for path in args.pages) if args.pages else public_pages()
    items = {}
    for products in pages:
        batch = {row["id"]: row for row in records(products)}
        if products and not batch.keys() - items.keys():
            raise ValueError("Big Toes catalog pagination did not advance")
        items.update(batch)
        if len(products) < 250:
            break
    else:
        raise ValueError("Big Toes catalog pagination did not reach the final page")
    if not items:
        raise ValueError("Big Toes returned an empty catalog")
    output = {"schema": "vault-bigtoes-v1", "count": len(items),
              "checkedAt": datetime.now(timezone.utc).isoformat(), "items": list(items.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Imported {len(items)} Big Toes variants, {sum(row['retailPrice'] is not None for row in items.values())} priced")


if __name__ == "__main__":
    main()
