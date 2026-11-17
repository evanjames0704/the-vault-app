#!/usr/bin/env python3
"""Import BBTS product listing data when publicly accessible.
No bot-block bypass. Supports saved authorized HTML via --input.
"""
import argparse,json,re,time
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup
BASE="https://www.bigbadtoystore.com"
def parse(html,url):
 soup=BeautifulSoup(html,"html.parser");records={}
 def add(name,link,image="",price=None,sku=""):
  link=urljoin(url,link)
  if urlparse(link).hostname not in ("bigbadtoystore.com","www.bigbadtoystore.com"):return
  if not name or not link:return
  key=urlparse(link).path.rstrip("/")
  if key in ("","/"):return
  identifier=re.sub(r"[^a-z0-9]+","-",key.lower()).strip("-")
  records[key]={"id":"bbts-"+identifier,"name":name.strip(),"category":"Action figures","brand":"BigBadToyStore","identifier":sku,"image":urljoin(url,image) if image else "","sourceUrl":link,"retailPrice":price,"currency":"USD","priceType":"listed_retail","marketValue":None}
 for script in soup.select('script[type="application/ld+json"]'):
  try:root=json.loads(script.string or script.get_text())
  except (ValueError,TypeError):continue
  stack=[root]
  while stack:
   node=stack.pop()
   if isinstance(node,list):stack.extend(node);continue
   if not isinstance(node,dict):continue
   stack.extend(v for v in node.values() if isinstance(v,(dict,list)))
   types=node.get("@type",[])
   if isinstance(types,str):types=[types]
   if "Product" not in types:continue
   img=node.get("image") or ""
   if isinstance(img,list):img=img[0] if img else ""
   if isinstance(img,dict):img=img.get("url","")
   offers=node.get("offers") or {}
   if isinstance(offers,list):offers=offers[0] if offers else {}
   if not isinstance(offers,dict):offers={}
   try:price=float(offers["price"]) if offers.get("priceCurrency","USD")=="USD" else None
   except (ValueError,TypeError,KeyError):price=None
   add(str(node.get("name") or ""),str(node.get("url") or ""),str(img),price,str(node.get("sku") or ""))
 for a in soup.select("a[href]"):
  href=a.get("href","")
  if not ("/Product/" in href or "/product/" in href):continue
  img=a.find("img")
  name=(img.get("alt","") if img else "") or a.get("title","")
  if name:add(name,href,(img.get("data-src") or img.get("src") or "") if img else "")
 return list(records.values())
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--url",default=BASE+"/Search?SearchText=Marvel+Legends")
 p.add_argument("--input",nargs="*",type=Path)
 p.add_argument("--output",type=Path,default=Path("bbts-catalog.json"))
 a=p.parse_args()
 if a.input:pages=[(f.read_text(encoding="utf-8"),a.url) for f in a.input]
 else:
  r=requests.get(a.url,timeout=30,headers={"User-Agent":"TheVaultCatalogImporter/1.0"})
  r.raise_for_status();pages=[(r.text,a.url)]
 items={}
 for html,url in pages:
  for item in parse(html,url):items[item["id"]]=item
 if not items:raise SystemExit("BBTS did not expose recognizable product records; supply authorized HTML or feed.")
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-bbts-v1","count":len(items),"items":list(items.values())},ensure_ascii=False),encoding="utf-8")
 print("Imported",len(items),"BBTS products")
if __name__=="__main__":main()
