#!/usr/bin/env python3
"""Import authorized Hasbro Pulse or McFarlane Toys Store product metadata.

Uses structured Product JSON-LD only. Does not bypass restricted access.
"""
import argparse,json,re
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup
SOURCES={
 "hasbro":("https://www.hasbropulse.com/collections/marvel-legends","hasbropulse.com","Hasbro"),
 "mcfarlane":("https://mcfarlanetoysstore.com/collections/all","mcfarlanetoysstore.com","McFarlane Toys"),
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
   if not name or not urlparse(link).hostname or not urlparse(link).hostname.endswith(host):continue
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
 return list(items.values())
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True,choices=SOURCES)
 p.add_argument("--url")
 p.add_argument("--input",nargs="*",type=Path)
 p.add_argument("--output",required=True,type=Path)
 a=p.parse_args();default,host,brand=SOURCES[a.source];url=a.url or default
 if a.input:pages=[x.read_text(encoding="utf-8") for x in a.input]
 else:
  r=requests.get(url,timeout=25,headers={"User-Agent":"TheVaultCatalogImporter/1.0"})
  r.raise_for_status();pages=[r.text]
 items={}
 for html in pages:
  for item in parse(html,url,host,brand):items[item["id"]]=item
 if not items:raise SystemExit("No accessible structured product records found for "+brand)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-"+a.source+"-v1","count":len(items),"items":list(items.values())},ensure_ascii=False),encoding="utf-8")
 print("Imported",len(items),brand,"products")
if __name__=="__main__":main()
