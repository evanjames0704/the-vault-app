#!/usr/bin/env python3
"""Merge authorized collectible catalog exports into one searchable catalog.

Accepts arbitrary number of vault JSON catalogs. Deduplicates exact identifiers
within brand, preserving retailer offers and original source attribution.
"""
import argparse,json,re
from collections import defaultdict
from pathlib import Path
def clean(v):return re.sub(r"\s+"," ",str(v or "")).strip()
def main():
 p=argparse.ArgumentParser();p.add_argument("--input",nargs="+",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 merged={};source_counts=defaultdict(int)
 for path in a.input:
  obj=json.loads(path.read_text(encoding="utf-8"))
  records=obj.get("items",[]) if isinstance(obj,dict) else obj
  for raw in records:
   if not isinstance(raw,dict):continue
   name=clean(raw.get("name"));brand=clean(raw.get("brand"));variant=clean(raw.get("variant"));identifier=clean(raw.get("identifier") or raw.get("upc") or raw.get("number"))
   if not name:continue
   source=clean(raw.get("source") or obj.get("retailer") if isinstance(obj,dict) else "") or path.stem
   # An identifier is not unique across brands; otherwise use name+variant.
   key="|".join([brand.casefold(),identifier.casefold() if identifier else name.casefold(),variant.casefold()])
   record=merged.get(key)
   offer={"source":source,"url":clean(raw.get("sourceUrl")),"retailPrice":raw.get("retailPrice")}
   if record is None:
    record={"id":key,"name":name,"brand":brand,"category":clean(raw.get("category")),"franchise":clean(raw.get("franchise")),"identifier":identifier,"variant":variant,"image":clean(raw.get("image")),"offers":[]}
    merged[key]=record
   if not record["image"] and raw.get("image"):record["image"]=clean(raw["image"])
   if offer not in record["offers"]:record["offers"].append(offer)
   source_counts[source]+=1
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-unified-catalog-v1","count":len(merged),"sourceCounts":dict(source_counts),"items":list(merged.values())},ensure_ascii=False),encoding="utf-8")
 print(json.dumps({"uniqueRecords":len(merged),"sourceCounts":dict(source_counts)}))
if __name__=="__main__":main()
