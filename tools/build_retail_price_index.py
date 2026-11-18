"""Build the exact-edition USD retail index from the Pages release catalogs."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

SOURCES = (
    ("replay-catalog", "Replay Toys", ""),
    ("toyco-catalog", "Toyco", ""),
    ("galactic-catalog", "Galactic Toys", ""),
    ("toydojo-catalog", "Toy Dojo", ""),
    ("big-toes-catalog", "Big Toes Collectibles", ""),
    ("marvel-legends", "Legendsverse original retail", "Marvel Legends"),
    ("funko-catalog", "Official Funko product catalog", "Funko"),
    ("bbts-catalog", "BigBadToyStore catalog", "BigBadToyStore"),
    ("hot-toys-catalog", "BigBadToyStore Hot Toys catalog", "Hot Toys"),
    ("mcfarlane-catalog", "McFarlane Toys catalog", "McFarlane Toys"),
    ("cardcollector2-catalog", "CardCollector2", ""),
    ("soosoo-catalog", "Soosoo Toys shop", ""),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pages_dir", type=Path)
    directory = parser.parse_args().pages_dir
    offers = defaultdict(list)
    for filename, source, brand in SOURCES:
        source_path = directory / (filename + ".json")
        if not source_path.is_file():
            continue
        catalog = json.loads(source_path.read_text(encoding="utf-8"))
        for item in catalog["items"]:
            price = item.get("retailPrice")
            identifier = item.get("identifier")
            if not identifier or not isinstance(price, (float, int)) or price <= 0:
                continue
            if item.get("currency", "USD") != "USD":
                continue
            variant = item.get("variant") or ""
            if filename in ("funko-catalog", "mcfarlane-catalog"):
                variant = variant or item.get("series") or ""
            if filename == "marvel-legends":
                variant = str(item.get("wave") or variant or item.get("year") or "")
            category = item["category"]
            if category == "Collectibles":
                category = "Action figures"
            key = (category, str(identifier), item.get("brand") or brand, item["name"], variant)
            offers[key].append([price, item.get("priceSource") or source, item.get("sourceUrl", "")])
    rows = [
        [*key, *quotes[0]]
        for key, quotes in sorted(offers.items())
        if len({quote[0] for quote in quotes}) == 1
    ]
    (directory / "retail-prices.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(rows)} exact-edition retail prices")


if __name__ == "__main__":
    main()
