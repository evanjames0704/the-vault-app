#!/usr/bin/env python3
"""Mirror permitted catalog images into the website for reliable cross-origin display.

Images are fetched only from approved source hosts. A failed image is left with
its original URL so it can still be displayed if the browser allows it.
"""
import argparse, json, mimetypes, re, time
from pathlib import Path
from urllib.parse import urlparse
import requests

ALLOWED={"funko.com","www.funko.com","sideshow.com","www.sideshow.com","legendsverse.com","www.legendsverse.com"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",type=Path,default=Path("website"))
 p.add_argument("--max-images",type=int,default=1500)
 args=p.parse_args()
 root=args.root
 dest=root/"catalog-images"
 dest.mkdir(parents=True,exist_ok=True)
 session=requests.Session()
 session.headers.update({"User-Agent":"TheVaultCatalogImageImporter/1.0","Accept":"image/avif,image/webp,image/png,image/jpeg,image/*"})
 totals={}
 for filename in ("funko-catalog.json","marvel-legends.json","sideshow-catalog.json"):
  path=root/filename
  if not path.exists():continue
  data=json.loads(path.read_text(encoding="utf-8"))
  successes=0
  for item in data.get("items",[]):
   if successes>=args.max_images:break
   image=item.get("image","")
   parsed=urlparse(image)
   if parsed.scheme!="https" or parsed.hostname not in ALLOWED:continue
   try:
    response=session.get(image,timeout=14,allow_redirects=True)
    response.raise_for_status()
    ctype=response.headers.get("Content-Type","").split(";")[0].lower()
    if not ctype.startswith("image/") or len(response.content)>4_000_000 or len(response.content)<100:continue
    ext={ "image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/avif":".avif" }.get(ctype)
    if not ext:continue
    stem=re.sub(r"[^a-z0-9_-]","-",str(item.get("id","item")).lower())[:100]
    output=dest/(stem+ext)
    output.write_bytes(response.content)
    item["image"]="catalog-images/"+output.name
    successes+=1
   except requests.RequestException:
    continue
  data["localImageCount"]=successes
  path.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
  totals[filename]=successes
 print("Mirrored catalog photos:",totals)
if __name__=="__main__":main()
