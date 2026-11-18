"""Import approved Shopify storefront product variants and USD prices."""
import argparse
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

STORES = {
    "bigtoes": ("Big Toes Collectibles", "https://bigtoescollectibles.com"),
    "replay": ("Replay Toys", "https://replaytoys.com"),
    "toyco": ("Toyco", "https://www.toyco.store"),
    "galactic": ("Galactic Toys", "https://galactictoys.com"),
    "toydojo": ("Toy Dojo", "https://toydojo.com"),
}


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


def records(products, store):
    source, origin = STORES[store]
    for product in products:
        title = product["title"].strip()
        if title.casefold() in {"additional fees", "convenience fee", "convienence fee"}:
            continue
        handle = product["handle"]
        if not title or not handle or re.search(r"[\s/\\?#]", handle) or handle in {".", ".."}:
            raise ValueError("Unexpected storefront product title or handle")
        images = {image["id"]: image.get("src", "") for image in product.get("images", [])}
        for variant in product["variants"]:
            prefix = store if store == "bigtoes" else f"{store}-variant"
            identifier = f"{prefix}:{variant['id']}"
            edition = "" if variant["title"] == "Default Title" else variant["title"]
            if re.search(r"\b(?:deposit|down payment|balance only|installment)\b", f"{title} {edition}", re.I):
                continue
            if re.fullmatch(r"full price(?:\s*-\s*\$[\d,.]+)?", edition, re.I):
                edition = ""
            try:
                price = float(variant["price"])
            except (ValueError, TypeError, KeyError):
                price = 0
            if not math.isfinite(price) or price <= 0:
                price = None
            image = images.get((variant.get("featured_image") or {}).get("id")) or next(iter(images.values()), "")
            barcode = str(variant.get("barcode") or "").strip()
            if not re.fullmatch(r"\d{8}|\d{12,14}", barcode) or not any(c != "0" for c in barcode):
                barcode = ""
            elif (sum(int(digit) * (3 if i % 2 else 1) for i, digit in enumerate(reversed(barcode))) % 10):
                barcode = ""
            yield {
                "id": identifier, "identifier": identifier, "name": title,
                "variant": edition, "gtin": barcode, "category": category(title, product.get("product_type", "")),
                "brand": product.get("vendor") or "", "retailPrice": price, "currency": "USD",
                "image": image if image.startswith("https://") else "",
                "available": variant.get("available") is True,
                "source": source,
                "sourceUrl": f"{origin}/products/{quote(handle, safe='-._~')}?variant={variant['id']}",
            }


def public_pages(origin):
    import requests

    with requests.Session() as session:
        session.headers["User-Agent"] = "TheVaultCatalogImporter/1.0"
        home = session.get(origin, timeout=15)
        home.raise_for_status()
        if not re.search(r'Shopify\.currency\s*=\s*\{\s*"active"\s*:\s*"USD"', home.text):
            raise ValueError("Could not verify storefront currency")
        for page in range(1, 101):
            response = session.get(f"{origin}/products.json", params={"limit": 250, "page": page}, timeout=20)
            response.raise_for_status()
            products = response.json()["products"]
            yield products
            if len(products) < 250:
                return
            time.sleep(1)
    raise ValueError("Storefront catalog exceeded the pagination limit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", choices=STORES, default="bigtoes")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pages", type=Path, nargs="+", help="Previously fetched USD feed pages in order")
    args = parser.parse_args()
    pages = (json.loads(path.read_text())["products"] for path in args.pages) if args.pages else public_pages(STORES[args.store][1])
    items = {}
    for products in pages:
        batch = {row["id"]: row for row in records(products, args.store)}
        if products and batch and not batch.keys() - items.keys():
            raise ValueError("Storefront pagination did not advance")
        items.update(batch)
        if len(products) < 250:
            break
    else:
        raise ValueError("Storefront pagination did not reach the final page")
    if not items:
        raise ValueError("Storefront returned an empty catalog")
    output = {"schema": "vault-bigtoes-v1" if args.store == "bigtoes" else "vault-storefront-catalog-v1", "count": len(items),
              "checkedAt": datetime.now(timezone.utc).isoformat(), "items": list(items.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Imported {len(items)} {STORES[args.store][0]} variants, {sum(row['retailPrice'] is not None for row in items.values())} priced")


if __name__ == "__main__":
    main()
