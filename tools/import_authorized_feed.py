#!/usr/bin/env python3
"""Normalize permitted retailer catalog exports and eBay sold/active observations.

No fabricated market prices. No access-control circumvention. Provide an
authorized JSON export via --input; this utility never logs into eBay.
"""
import argparse,csv,json,statistics
from datetime import datetime,timezone
from pathlib import Path

def load(path):
 if path.suffix.lower()==".csv":
  with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
 data=json.loads(path.read_text(encoding="utf-8"))
 return data.get("items",data.get("results",[])) if isinstance(data,dict) else data

def money(v):
 try:
  if v is None or str(v).strip()=="":return None
  x=float(str(v).replace("$","").replace(",",""))
  return round(x,2) if 0<x<1000000 else None
 except (TypeError,ValueError):return None

def normalize(item,source):
 name=str(item.get("name") or item.get("title") or "").strip()
 if not name:return None
 kind=str(item.get("priceType") or item.get("listingType") or "retail").lower()
 if kind not in ("retail","active","sold"):kind="retail"
 return {"id":str(item.get("id") or item.get("sku") or item.get("upc") or name),
         "name":name,"brand":str(item.get("brand") or source),
         "category":str(item.get("category") or "Collectibles"),
         "franchise":str(item.get("franchise") or ""),
         "identifier":str(item.get("identifier") or item.get("upc") or item.get("sku") or ""),
         "variant":str(item.get("variant") or ""),
         "image":str(item.get("image") or item.get("imageUrl") or ""),
         "sourceUrl":str(item.get("sourceUrl") or item.get("url") or ""),
         "source":source,"currency":str(item.get("currency") or "USD"),
         "priceType":kind,"price":money(item.get("price") or item.get("soldPrice")),
         "condition":str(item.get("condition") or "unspecified"),
         "observedAt":str(item.get("observedAt") or datetime.now(timezone.utc).isoformat())}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True,choices=["ebay","funko","sideshow","bbts","hasbro","mcfarlane","legendsverse"])
 p.add_argument("--input",required=True,type=Path)
 p.add_argument("--output",required=True,type=Path)
 a=p.parse_args()
 items=[v for x in load(a.input) if isinstance(x,dict) if (v:=normalize(x,a.source))]
 if not items:raise SystemExit("No valid products or observations")
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-source-observations-v1","source":a.source,"count":len(items),"items":items},ensure_ascii=False),encoding="utf-8")
 print("Normalized",len(items),"records from",a.source)
if __name__=="__main__":main()
