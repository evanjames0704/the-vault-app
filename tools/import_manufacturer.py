#!/usr/bin/env python3
"""Import authorized Hasbro Pulse or McFarlane Toys Store product metadata.

Uses structured Product JSON-LD only. Does not bypass restricted access.
"""
import argparse,json,re
from pathlib import Path
from catalog_pages import listing_pages
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup
SOURCES={
 "hasbro":("https://www.hasbropulse.com/collections/marvel-legends-series","hasbropulse.com","Hasbro"),
 "mcfarlane":("https://mcfarlanetoysstore.com/dc-multiverse/","mcfarlanetoysstore.com","McFarlane Toys"),
}
def parse(html,url,host,brand):
 soup=BeautifulSoup(html,"html.parser");items={}
 for script in soup.select('script[type="application/ld+json"]'):
  try:root=json.loads(script.string or script.get_text())
  except (ValueError,TypeError):continue
  stack=[root]
  while stack:
   node=stack.pop()
   if isinstance(node,list):stack.extend(node);continue
   if not isinstance(node,dict):continue
   stack.extend(v for v in node.values() if isinstance(v,(dict,list)))
   kinds=node.get("@type",[])
   if isinstance(kinds,str):kinds=[kinds]
   if "Product" not in kinds:continue
   name=str(node.get("name") or "").strip()
   link=urljoin(url,str(node.get("url") or ""))
   if not name or not urlparse(link).hostname or urlparse(link).hostname not in (host, "www."+host):continue
   img=node.get("image") or ""
   if isinstance(img,list):img=img[0] if img else ""
   if isinstance(img,dict):img=img.get("url","")
   offers=node.get("offers") or {}
   if isinstance(offers,list):offers=offers[0] if offers else {}
   if not isinstance(offers,dict):offers={}
   try:price=round(float(offers["price"]),2) if offers.get("priceCurrency","USD")=="USD" else None
   except (ValueError,TypeError,KeyError):price=None
   key=re.sub(r"[^a-z0-9]+","-",urlparse(link).path.lower()).strip("-")
   items[key]={"id":brand.lower().replace(" ","-")+"-"+key,"name":name,"category":"Action figures","brand":brand,"identifier":str(node.get("sku") or ""),"image":urljoin(url,str(img)) if img else "","sourceUrl":link,"retailPrice":price,"currency":"USD","priceType":"listed_retail","marketValue":None}
 if host=="mcfarlanetoysstore.com":
  for card in soup.select("article.card a.card-product-link[href]"):
   title=card.select_one(".card-title")
   body=card.select_one("[data-product-id]")
   if not title or not body:continue
   link=urljoin(url,card["href"])
   if urlparse(link).hostname != host:continue
   identifier=body["data-product-id"]
   name=title.get_text(" ",strip=True)
   image=card.select_one("img[src]")
   line=card.select_one(".card-brand-name")
   series=line.get_text(" ",strip=True) if line else ""
   items[identifier]={"id":"mcfarlane-"+identifier,"name":name,"category":"Action figures" if re.search(r"\bfigures?\b",name,re.I) else "Collectibles","brand":brand,"franchise":"DC" if urlparse(url).path.startswith("/dc-") else "","series":series,"identifier":identifier,"image":urljoin(url,image["src"]) if image else "","sourceUrl":link,"retailPrice":None,"marketValue":None}
 return list(items.values())
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True,choices=SOURCES)
 p.add_argument("--url")
 p.add_argument("--input",nargs="*",type=Path)
 p.add_argument("--output",required=True,type=Path)
 a=p.parse_args();default,host,brand=SOURCES[a.source];url=a.url or default
 if a.input:
  pages=((x.read_text(encoding="utf-8"),url) for x in a.input)
 elif a.source=="mcfarlane":
  sections=[url] if a.url else [urljoin(url,path) for path in ("/dc-multiverse/","/dc-movies/","/dc-gaming/","/dc-retro/","/movies/","/comics/","/gaming/","/sports/","/music/","/television/","/digital-available/","/exclusives/")]
  pages=(page for section in sections for page in listing_pages(section))
 else:
  r=requests.get(url,timeout=25,headers={"User-Agent":"TheVaultCatalogImporter/1.0"})
  r.raise_for_status()
  pages=[(r.text,r.url)]
 items={}
 for html,page_url in pages:
  for item in parse(html,page_url,host,brand):items[item["id"]]=item
 if not items:raise SystemExit("No accessible structured product records found for "+brand)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-"+a.source+"-v1","count":len(items),"items":list(items.values())},ensure_ascii=False),encoding="utf-8")
 print("Imported",len(items),brand,"products")
if __name__=="__main__":main()
