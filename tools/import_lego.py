#!/usr/bin/env python3
"""Create the free LEGO set search index from Rebrickable's official bulk CSV.

No API key or commercial pricing data. The index is for catalog discovery only.
Data source: https://rebrickable.com/downloads/
"""
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://cdn.rebrickable.com/media/downloads/"

def load_csv(url, input_path=None):
    if input_path:
        data = Path(input_path).read_bytes()
    else:
        request = Request(url, headers={"User-Agent": "TheVaultCatalogBuilder/1.0"})
        with urlopen(request, timeout=60) as response:
            data = response.read(35_000_000 + 1)
        if len(data) > 35_000_000:
            raise RuntimeError("Unexpectedly large catalog download")
    if data[:2] == b"\\x1f\\x8b":
        data = gzip.decompress(data)
    return csv.DictReader(io.StringIO(data.decode("utf-8-sig")))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("lego-catalog.json"))
    p.add_argument("--sets", type=Path, help="Use locally saved sets.csv.gz for testing")
    p.add_argument("--themes", type=Path, help="Use locally saved themes.csv.gz for testing")
    a = p.parse_args()
    themes = {}
    for record in load_csv(BASE + "themes.csv.gz", a.themes):
        themes[record.get("id", "")] = record.get("name", "").strip()
    result = []
    seen = set()
    for row in load_csv(BASE + "sets.csv.gz", a.sets):
        number = (row.get("set_num") or "").strip()
        name = (row.get("name") or "").strip()
        if not number or not name or number in seen:
            continue
        seen.add(number)
        year = (row.get("year") or "").strip()
        theme = themes.get((row.get("theme_id") or "").strip(), "")
        image = (row.get("img_url") or row.get("set_img_url") or "").strip()
        if not image.startswith("https://"):
            image = ""
        result.append([number, name, year, theme, image])
    if len(result) < 10000:
        raise RuntimeError(f"Unexpectedly small LEGO set index: {len(result)}")
    result.sort(key=lambda item: (item[1].lower(), item[0]))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"Built {len(result)} LEGO sets with {sum(bool(r[4]) for r in result)} image URLs")

if __name__ == "__main__":
    main()
