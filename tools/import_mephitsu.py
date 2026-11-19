#!/usr/bin/env python3
"""Import Marvel Legends checklist records from Mephitsu's permitted public pages.

Supports downloaded HTML via --input. Uses only visible table rows; no access
restriction bypass and no fabricated prices.
"""
import argparse,json,re
from pathlib import Path
from urllib.parse import urljoin
from catalog_pages import listing_pages
from bs4 import BeautifulSoup

URL="https://www.mephitsu.co.uk/marvel-legends"
def extract(html):
 soup=BeautifulSoup(html,"html.parser")
 result={}
 for table in soup.select("table"):
  headings=[x.get_text(" ",strip=True).lower() for x in table.select("th")]
  if not ("title" in headings and "year" in headings):continue
  for tr in table.select("tr"):
   cells=tr.find_all(["td"],recursive=False)
   if not cells:continue
   data={headings[i]:cells[i] for i in range(min(len(headings),len(cells)))}
   title=data.get("title")
   if not title:continue
   name=title.get_text(" ",strip=True)
   if not name:continue
   a=title.find("a",href=True)
   link=urljoin(URL,a["href"]) if a else URL
   image=tr.find("img")
   photo=urljoin(URL,(image.get("data-src") or image.get("src") or "")) if image else ""
   def field(k):return data[k].get_text(" ",strip=True) if k in data else ""
   year=field("year")
   key=re.sub(r"[^a-z0-9]+","-",f"{name}-{year}-{field('wave')}-{field('release type')}".lower()).strip("-")
   result[key]={"id":"mephitsu-"+key,"name":name,"brand":"Hasbro","category":"Marvel Legends","franchise":"Marvel","year":year,"variant":field("release type"),"series":field("wave"),"source":field("source"),"movieOrSeries":field("movie or series"),"sourceUrl":link,"image":photo,"retailPrice":None,"marketValue":None}
 return list(result.values())
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",type=Path)
 p.add_argument("--output",type=Path,default=Path("mephitsu-catalog.json"))
 a=p.parse_args()
 pages=[(a.input.read_text(encoding="utf-8"), URL)] if a.input else listing_pages(URL)
 indexed={}
 for html, _ in pages:
  for item in extract(html):
   indexed[item["id"]]=item
 items=list(indexed.values())
 if not items:raise SystemExit("Mephitsu table not available in returned HTML; provide authorized export")
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-mephitsu-v1","count":len(items),"items":items},ensure_ascii=False),encoding="utf-8")
 print("Imported",len(items),"Mephitsu Marvel Legends records")
if __name__=="__main__":main()
