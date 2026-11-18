#!/usr/bin/env python3
"""Import publicly permitted Funko product pages into THE VAULT.

pip install requests beautifulsoup4
python tools/import_funko.py --url https://funko.com/all-funko-products/ --output funko-catalog.json

This imports only product records exposed in publicly accessible HTML/JSON-LD.
Follows the public product grid continuation and reads visible listing cards.
No access-control bypass, no invented prices, and no downloading image binaries.
"""
import argparse, json, re, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
BASE="https://funko.com"
def parse(html,page):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(html,"html.parser")
 items={}
 for tag in soup.select('script[type="application/ld+json"]'):
  try: root=json.loads(tag.string or tag.get_text())
  except (ValueError,TypeError):continue
  queue=[root]
  while queue:
   obj=queue.pop()
   if isinstance(obj,list):queue.extend(obj);continue
   if not isinstance(obj,dict):continue
   queue.extend(v for v in obj.values() if isinstance(v,(dict,list)))
   kinds=obj.get("@type",[])
   if isinstance(kinds,str):kinds=[kinds]
   if "Product" not in kinds:continue
   name=str(obj.get("name") or "").strip()
   url=urljoin(page,str(obj.get("url") or ""))
   if not name or urlparse(url).netloc not in ("funko.com","www.funko.com"):continue
   image=obj.get("image") or ""
   if isinstance(image,list):image=image[0] if image else ""
   if isinstance(image,dict):image=image.get("url","")
   offers=obj.get("offers") or {}
   if isinstance(offers,list):offers=offers[0] if offers else {}
   if not isinstance(offers,dict):offers={}
   raw=offers.get("price")
   try:price=round(float(raw),2) if raw is not None else None
   except (ValueError,TypeError):price=None
   if price is not None and (price<0 or price>100000):price=None
   currency=offers.get("priceCurrency") or "USD"
   key=str(obj.get("sku") or urlparse(url).path)
   items[key]={"id":"funko-"+re.sub(r"[^a-z0-9]+","-",key.lower()).strip("-"),
    "name":name,"category":"Funko Pops","brand":"Funko","identifier":str(obj.get("sku") or ""),
    "image":urljoin(page,image) if image else "","sourceUrl":url,
    "retailPrice":price if currency=="USD" else None,"currency":"USD",
    "priceType":"manufacturer_retail","marketValue":None}
 for tile in soup.select(".product-tile[data-analytics-id]"):
  link=tile.select_one("a.product-name[href]")
  if not link:continue
  name=link.get_text(" ",strip=True)
  key=tile["data-analytics-id"]
  url=urljoin(page,link["href"])
  if not name or not key or urlparse(url).hostname not in ("funko.com","www.funko.com"):continue
  photo=tile.select_one("img.tile-main-image")
  image=(photo.get("data-src") or photo.get("src")) if photo else tile.get("data-analytics-image-url")
  try:price=round(float(tile.get("data-analytics-list-price")),2)
  except (TypeError,ValueError):price=None
  if price is not None and not 0<=price<=100000:price=None
  existing=items.get(key,{})
  item={"id":"funko-"+re.sub(r"[^a-z0-9]+","-",key.lower()).strip("-"),
   "name":name,"category":"Funko Pops" if "pop" in tile.get("data-analytics-product-type","").lower() else "Collectibles",
   "brand":"Funko","identifier":key,"image":urljoin(page,image) if image else "",
   "sourceUrl":url,"retailPrice":price,"currency":"USD","priceType":"manufacturer_retail","marketValue":None}
  item.update(existing)
  item.update({"category":"Funko Pops" if "pop" in tile.get("data-analytics-product-type","").lower() else "Collectibles",
   "franchise":tile.get("data-analytics-subcategory",""),"series":tile.get("data-analytics-subcategory2","")})
  items[key]=item
 return list(items.values())
def main():
 ap=argparse.ArgumentParser()
 src=ap.add_mutually_exclusive_group(required=True)
 src.add_argument("--url");src.add_argument("--input",nargs="+",type=Path)
 ap.add_argument("--output",type=Path,default=Path("funko-catalog.json"))
 args=ap.parse_args();pages=[]
 if args.url:
  from catalog_pages import listing_pages
  pages=listing_pages(args.url, 'button.btn-pagination.next[data-url]:not([disabled])', "data-url")
 else:pages=[(p.read_text(encoding="utf-8"),BASE+"/all-funko-products/") for p in args.input]
 items={}
 for html,url in pages:
  for item in parse(html,url):items[item["id"]]=item
 if not items:sys.exit("No product JSON-LD records found. Save rendered product HTML or update importer for site's markup.")
 output={"schema":"vault-funko-v1","count":len(items),"items":sorted(items.values(),key=lambda x:x["name"].lower())}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
 print(f"Imported {len(items)} products to {args.output}. Validate images and retail prices before publishing.")
if __name__=="__main__":main()
