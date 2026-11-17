#!/usr/bin/env python3
"""Build defensible provisional values from observed collectible listings.

Requires supplied observations; never invents prices. Sold comps are preferred.
Active listings are discounted for an indicative estimate, not called sold values.
"""
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

def key(x):
 return "|".join(str(x.get(k,"")).strip().casefold() for k in ("name","identifier","variant","condition"))
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True,type=Path)
 p.add_argument("--output",required=True,type=Path)
 p.add_argument("--active-discount",type=float,default=.85)
 a=p.parse_args()
 if not 0<a.active_discount<=1:raise SystemExit("active discount must be in (0,1]")
 source=json.loads(a.input.read_text(encoding="utf-8"))
 grouped=defaultdict(lambda:{"sold":[],"active":[]})
 for x in source.get("items",[]):
  if x.get("currency")!="USD" or x.get("priceType") not in ("sold","active"):continue
  try:v=float(x.get("price"))
  except (TypeError,ValueError):continue
  if not 0<v<1000000:continue
  grouped[key(x)][x["priceType"]].append(v)
 out=[]
 for k,groups in grouped.items():
  sold=groups["sold"];active=groups["active"]
  if sold:
   value=round(statistics.median(sold),2);method="sold_median";confidence="high" if len(sold)>=5 else "medium" if len(sold)>=2 else "low";count=len(sold)
  elif active:
   value=round(statistics.median(active)*a.active_discount,2);method="active_listing_adjusted";confidence="low";count=len(active)
  else:continue
  out.append({"key":k,"estimatedValue":value,"currency":"USD","method":method,"confidence":confidence,"comparables":count,"observedAt":datetime.now(timezone.utc).isoformat(),"isEstimate":True})
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-estimates-v1","count":len(out),"estimates":out},ensure_ascii=False),encoding="utf-8")
 print("Created",len(out),"estimated values from observed listings")
if __name__=="__main__":main()
