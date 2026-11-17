#!/usr/bin/env python3
"""Import permitted Sideshow catalog listings into THE VAULT, without paid APIs.

pip install requests beautifulsoup4
python tools/import_sideshow.py --pages 5 --output sideshow-catalog.json

Defaults to Sideshow's all-collectibles listing (not only Sideshow-made
products). Requests are sequential and throttled. Does not bypass blocks,
download images, or invent prices. Validate exported records before release.
"""
import argparse, json, re, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

BASE="https://www.sideshow.com"
def parse(html, page):
 soup=BeautifulSoup(html,"html.parser")
 items={}
 def save(name,url,image="",price=None,sku="",maker="Sideshow marketplace"):
  if not name or len(name)<3:return
  url=urljoin(page,url)
  if urlparse(url).netloc not in ("sideshow.com","www.sideshow.com"):return
  if not urlparse(url).path.startswith("/collectibles/"):return
  key=urlparse(url).path.rstrip("/")
  image=urljoin(page,image) if image else ""
  items[key]={"id":"sideshow-"+re.sub(r"[^a-z0-9]+","-",key.lower()).strip("-"),
   "name":name.strip(),"category":"Collectibles","brand":maker,
   "identifier":sku,"image":image,"sourceUrl":url,
   "retailPrice":price,"currency":"USD","priceType":"listed_retail",
   "marketValue":None}
 # Prefer explicit structured product records where available.
 for tag in soup.select('script[type="application/ld+json"]'):
  try:root=json.loads(tag.string or tag.get_text())
  except (TypeError,ValueError):continue
  stack=[root]
  while stack:
   obj=stack.pop()
   if isinstance(obj,list):stack.extend(obj);continue
   if not isinstance(obj,dict):continue
   stack.extend(v for v in obj.values() if isinstance(v,(dict,list)))
   types=obj.get("@type",[])
   if isinstance(types,str):types=[types]
   if "Product" not in types:continue
   image=obj.get("image") or ""
   if isinstance(image,list):image=image[0] if image else ""
   if isinstance(image,dict):image=image.get("url","")
   offer=obj.get("offers") or {}
   if isinstance(offer,list):offer=offer[0] if offer else {}
   if not isinstance(offer,dict):offer={}
   raw=offer.get("price")
   try:price=round(float(raw),2) if raw is not None and offer.get("priceCurrency","USD")=="USD" else None
   except (ValueError,TypeError):price=None
   brand=obj.get("brand") or {}
   if isinstance(brand,dict):brand=brand.get("name","Sideshow marketplace")
   save(str(obj.get("name") or ""),str(obj.get("url") or ""),str(image),price,str(obj.get("sku") or ""),str(brand))
 # Listing card fallback; do not infer pricing from unrelated page text.
 for a in soup.select('a[href*="/collectibles/"]'):
  href=a.get("href","")
  if not re.search(r"/collectibles/[^/?#]+",href):continue
  img=a.find("img")
  heading=a.find(re.compile("^h[2-6]$"))
  name=(heading.get_text(" ",strip=True) if heading else
        (img.get("alt","").strip() if img else ""))
  if not name:continue
  photo=(img.get("data-src") or img.get("src") or "") if img else ""
  save(name,href,photo)
 return list(items.values())
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--pages",type=int,default=5)
 ap.add_argument("--input",nargs="*",type=Path)
 ap.add_argument("--output",type=Path,default=Path("sideshow-catalog.json"))
 args=ap.parse_args()
 if not 1<=args.pages<=267:ap.error("--pages must be between 1 and 267")
 pages=[]
 if args.input:
  pages=[(p.read_text(encoding="utf-8"),BASE+"/categories/collectibles?page=1") for p in args.input]
 else:
  session=requests.Session()
  session.headers.update({"User-Agent":"TheVaultCatalogImporter/1.0","Accept":"text/html"})
  for page in range(1,args.pages+1):
   url=BASE+"/categories/collectibles?page="+str(page)
   r=session.get(url,timeout=30);r.raise_for_status()
   pages.append((r.text,url))
   if page<args.pages:time.sleep(1.5)
 merged={}
 for html,url in pages:
  for item in parse(html,url):
   old=merged.get(item["id"])
   if old:
    for key,value in item.items():
     if value is not None and value!="":old[key]=value
   else:merged[item["id"]]=item
 if not merged:raise SystemExit("No product records found; site markup may require an importer update.")
 out={"schema":"vault-sideshow-v1","count":len(merged),"items":sorted(merged.values(),key=lambda x:x["name"].lower())}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 print(f"Exported {len(merged)} products from {len(pages)} pages. Review images/prices before deploying.")
if __name__=="__main__":main()
