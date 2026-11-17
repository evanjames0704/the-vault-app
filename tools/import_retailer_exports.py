#!/usr/bin/env python3
"""Import authorized retailer CSV/JSON exports into THE VAULT.

No credentials, scraping bypass, invented catalog records or invented prices.
Supported retailers: Walmart, Target, Amazon, Best Buy.
"""
import argparse,csv,json,re
from pathlib import Path
RETAILERS={"walmart","target","amazon","bestbuy"}
CATEGORIES=("funko","lego","action figure","marvel legends","statue","collectible","trading card","comic","video game","memorabilia","hot toys","neca","mcfarlane","hasbro","model kit","prop replica")
def rows(path):
 if path.suffix.lower()==".csv":
  with path.open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
 obj=json.loads(path.read_text(encoding="utf-8"))
 return obj if isinstance(obj,list) else obj.get("items",obj.get("products",[]))
def get(x,*keys):
 for k in keys:
  if x.get(k) not in (None,""):return x[k]
 return ""
def price(x):
 try:
  p=float(str(get(x,"retailPrice","price","salePrice","currentPrice")).replace("$","").replace(",",""))
  return round(p,2) if 0<p<1000000 else None
 except (TypeError,ValueError):return None
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--retailer",choices=sorted(RETAILERS),required=True)
 p.add_argument("--input",type=Path,required=True)
 p.add_argument("--output",type=Path,required=True)
 p.add_argument("--include-all",action="store_true",help="Do not restrict to collectible categories")
 a=p.parse_args();out=[];seen=set()
 for x in rows(a.input):
  if not isinstance(x,dict):continue
  name=str(get(x,"name","title","productName")).strip()
  category=str(get(x,"category","productType","department")).strip()
  if not name:continue
  searchable=(name+" "+category+" "+str(get(x,"brand","manufacturer"))).casefold()
  if not a.include_all and not any(c in searchable for c in CATEGORIES):continue
  sku=str(get(x,"upc","gtin","ean","asin","sku","id","productId")).strip()
  variant=str(get(x,"variant","edition","color")).strip()
  unique=(a.retailer,sku or name.casefold(),variant.casefold())
  if unique in seen:continue
  seen.add(unique)
  out.append({"id":a.retailer+":"+str(sku or len(out)+1),"name":name,"category":category or "Collectibles","brand":str(get(x,"brand","manufacturer")),"franchise":str(get(x,"franchise","license")),"identifier":sku,"variant":variant,"image":str(get(x,"image","imageUrl","image_url","thumbnail")),"retailPrice":price(x),"source":a.retailer,"sourceUrl":str(get(x,"url","productUrl","link"))})
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-retailer-v1","retailer":a.retailer,"count":len(out),"items":out},ensure_ascii=False),encoding="utf-8")
 print(a.retailer,len(out),"collectible products")
if __name__=="__main__":main()
