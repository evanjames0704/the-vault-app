#!/usr/bin/env python3
"""Import product pages from a retailer's public sitemap and schema.org Product data.

Only public pages, rate-limited, no login/captcha bypass. Website-specific terms
and written permission remain the operator's responsibility.
"""
import argparse,json,time,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
def products(obj):
 if isinstance(obj,list):
  for v in obj:yield from products(v)
 elif isinstance(obj,dict):
  types=obj.get("@type",[])
  if isinstance(types,str):types=[types]
  if "Product" in types:yield obj
  for k in ("@graph","mainEntity","itemListElement"):
   if k in obj:yield from products(obj[k])
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--sitemap",required=True)
 p.add_argument("--source",required=True)
 p.add_argument("--output",required=True,type=Path)
 p.add_argument("--max-pages",type=int,default=100)
 p.add_argument("--delay",type=float,default=1.5)
 a=p.parse_args()
 if not 1<=a.max_pages<=10000 or a.delay<1:raise SystemExit("max-pages 1..10000, delay >= 1 second")
 host=urlparse(a.sitemap).hostname
 if not host or urlparse(a.sitemap).scheme!="https":raise SystemExit("HTTPS sitemap required")
 session=requests.Session();session.headers.update({"User-Agent":"TheVaultCatalogImporter/1.0 (authorized public product catalog)"})
 def fetch(url):
  if urlparse(url).hostname!=host or urlparse(url).scheme!="https":return None
  r=session.get(url,timeout=25);r.raise_for_status();time.sleep(a.delay);return r
 sitemap=fetch(a.sitemap)
 if sitemap is None:raise SystemExit("Invalid sitemap")
 root=ET.fromstring(sitemap.content)
 urls=[node.text for node in root.iter() if node.tag.endswith("loc") and node.text and urlparse(node.text).hostname==host]
 out=[];seen=set()
 for url in urls[:a.max_pages]:
  try:
   r=fetch(url)
   if r is None:continue
   soup=BeautifulSoup(r.text,"html.parser")
   for tag in soup.select('script[type="application/ld+json"]'):
    try:obj=json.loads(tag.string or tag.get_text())
    except (ValueError,TypeError):continue
    for x in products(obj):
     name=x.get("name")
     if not isinstance(name,str) or not name.strip():continue
     sku=str(x.get("sku") or x.get("gtin13") or x.get("gtin12") or x.get("mpn") or "")
     key=(sku or url,name.casefold())
     if key in seen:continue
     seen.add(key)
     brand=x.get("brand") or ""
     if isinstance(brand,dict):brand=brand.get("name","")
     images=x.get("image") or []
     if isinstance(images,str):images=[images]
     if isinstance(images,dict):images=[images.get("url","")]
     offers=x.get("offers") or {}
     if isinstance(offers,list):offers=offers[0] if offers else {}
     if not isinstance(offers,dict):offers={}
     try:price=round(float(offers.get("price")),2)
     except (TypeError,ValueError):price=None
     out.append({"id":a.source+":"+str(sku or len(out)+1),"name":name.strip(),"brand":str(brand),"category":str(x.get("category") or "Collectibles"),"identifier":sku,"image":str(images[0]) if images else "","retailPrice":price,"source":a.source,"sourceUrl":url})
  except (requests.RequestException,ValueError):continue
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-retailer-v1","retailer":a.source,"count":len(out),"items":out},ensure_ascii=False),encoding="utf-8")
 print("Pages inspected:",min(len(urls),a.max_pages),"Products:",len(out))
if __name__=="__main__":main()
