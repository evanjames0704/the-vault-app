"""Import CardCollector2's public singles catalog."""
import argparse
import json
import math
import re
import time
from pathlib import Path

import requests

ORIGIN = "https://www.cardcollector2.com"


def rows(products):
    for product in products:
        title = product.get("title", "").strip()
        handle = product.get("handle", "")
        if not title or not re.fullmatch(r"[a-z0-9-]+", handle):
            continue
        sport = product.get("product_type") or ""
        number = re.search(r"#([^\s]+)", title)
        images = {image["id"]: image.get("src", "") for image in product.get("images", [])}
        for variant in product.get("variants", []):
            try:
                price = float(variant["price"])
            except (KeyError, TypeError, ValueError):
                price = None
            image = images.get((variant.get("featured_image") or {}).get("id")) or next(iter(images.values()), "")
            printing = variant.get("title", "")
            yield {
                "id": f"cc2-{variant['id']}", "name": title, "sport": sport,
                "category": "Trading cards" if "pokémon" in sport.casefold() or "pokemon" in sport.casefold() else "Sports cards",
                "identifier": number.group(1) if number else "",
                "variant": "" if printing == "Default Title" else printing,
                "image": image if image.startswith("https://") else "",
                "retailPrice": price if price and math.isfinite(price) and price > 0 else None,
                "available": variant.get("available") is True,
                "sourceUrl": f"{ORIGIN}/products/{handle}",
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    items = {}
    page = 1
    with requests.Session() as session:
        session.headers["User-Agent"] = "TheVaultCatalogImporter/1.0"
        while True:
            response = session.get(f"{ORIGIN}/collections/single-cards/products.json",
                                   params={"limit": 250, "page": page}, timeout=20)
            response.raise_for_status()
            products = response.json()["products"]
            imported = {row["id"]: row for row in rows(products)}
            if products and not (imported.keys() - items.keys()):
                raise ValueError(f"Catalog pagination did not advance at page {page}")
            items.update(imported)
            if len(products) < 250:
                break
            page += 1
            time.sleep(1)
    if not items:
        raise ValueError("CardCollector2 returned no singles")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema": "vault-cardcollector2-v1", "count": len(items),
                                       "items": list(items.values())}, ensure_ascii=False), encoding="utf-8")
    print(f"Imported {len(items)} CardCollector2 singles")


if __name__ == "__main__":
    main()
