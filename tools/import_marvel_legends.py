#!/usr/bin/env python3
"""THE VAULT: import publicly permitted Marvel Legends checklist pages.

Usage:
  python tools/import_marvel_legends.py --input saved-checklist.html --output marvel-legends.json
  python tools/import_marvel_legends.py --url https://legendsverse.com/checklist/marvel-legends/figures --output marvel-legends.json

Requires: pip install beautifulsoup4 requests
The importer does not bypass access controls, log in, or download images.
Review generated records before publishing. Re-run with further saved pages
and merge by source URL to build out the complete catalog.
"""
import argparse, json, re, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = "https://legendsverse.com"
def parse(html, page_url):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    results = {}
    # Prefer structured product data when the page exposes it.
    for script in soup.select('script[type="application/ld+json"]'):
        try: data = json.loads(script.string or script.get_text())
        except (ValueError, TypeError): continue
        queue = data if isinstance(data, list) else [data]
        while queue:
            node = queue.pop()
            if isinstance(node, list): queue.extend(node); continue
            if not isinstance(node, dict): continue
            queue.extend(v for v in node.values() if isinstance(v, (dict, list)))
            typ = node.get("@type", [])
            if isinstance(typ, str): typ = [typ]
            if "Product" not in typ: continue
            name = str(node.get("name") or "").strip()
            url = urljoin(page_url, str(node.get("url") or ""))
            if not name or not url.startswith(BASE): continue
            img = node.get("image") or ""
            if isinstance(img, list): img = img[0] if img else ""
            if isinstance(img, dict): img = img.get("url", "")
            results[url] = {"id": "ml-" + re.sub(r"[^a-z0-9]+","-",urlparse(url).path.lower()).strip("-"),
                "name": name, "category": "Action figures", "brand": "Marvel Legends",
                "image": urljoin(page_url, img) if img else "", "sourceUrl": url,
                "year": None, "marketValue": None}
    # Checklist cards: figure page anchors containing heading and optional photo/year.
    for a in soup.select('a[href]'):
        href = urljoin(page_url, a.get("href",""))
        path = urlparse(href).path
        if urlparse(href).hostname != "legendsverse.com" or not re.fullmatch(r"/checklist/marvel-legends/figures/[^/]+/?", path):
            continue
        name = a.get_text(" ", strip=True)
        if not name or len(name) > 180: continue
        heading = a.find_parent(re.compile("^h[2-6]$"))
        parent = heading.parent.parent if heading else a.parent
        img = a.find("img") or (parent.find("img") if parent else None)
        photo = ""
        if img:
            photo = img.get("data-src") or img.get("src") or ""
            if not photo:
                srcset = img.get("srcset") or ""
                photo = srcset.split(",")[0].strip().split(" ")[0] if srcset else ""
        context = parent.get_text(" ", strip=True) if parent else ""
        year = re.search(r"\b(19\d{2}|20\d{2})\b", context)
        results[href] = {"id":"ml-"+re.sub(r"[^a-z0-9]+","-",urlparse(href).path.lower()).strip("-"),
            "name":name,"category":"Action figures","brand":"Marvel Legends",
            "identifier":path.rstrip("/").rsplit("-", 1)[-1],
            "image":urljoin(page_url,photo) if photo else "", "sourceUrl":href,
            "year":int(year.group(1)) if year else None, "marketValue":None}
    return list(results.values())

def main():
    p=argparse.ArgumentParser()
    src=p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", nargs="+", type=Path)
    src.add_argument("--url")
    p.add_argument("--output", type=Path, default=Path("marvel-legends.json"))
    args=p.parse_args()
    pages=[]
    if args.input:
        pages=[(x.read_text(encoding="utf-8"), BASE+"/checklist/marvel-legends/figures") for x in args.input]
    else:
        from catalog_pages import listing_pages
        pages = listing_pages(args.url)
    from apply_marvel_legends_retail import apply_prices, collect_prices
    from urllib.parse import parse_qs
    merged={}
    pricing_pages=[]
    for html,url in pages:
        for item in parse(html,url): merged[item["sourceUrl"]]=item
        expected_page = int(parse_qs(urlparse(url).query).get("page", ["1"])[0]) if args.url else None
        pricing_pages.append((html, expected_page))
    if not merged:
        sys.exit("No figure records recognized. Site markup may require an importer update; no output written.")
    matched = apply_prices(merged.values(), collect_prices(pricing_pages))
    output={"schema":"vault-marvel-legends-v1","count":len(merged),"items":sorted(merged.values(),key=lambda x:x["name"].lower())}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Imported {len(merged)} records to {args.output}, including {matched} original retail prices; inspect names and images before deployment.")
if __name__=="__main__":main()
