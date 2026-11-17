#!/usr/bin/env python3
"""Import Pokémon TCG card records from the open pokemon-tcg-data project.

Dataset: https://github.com/PokemonTCG/pokemon-tcg-data
No prices are invented; card images use dataset-provided URLs.
"""
import argparse,json,time,subprocess,tempfile
from pathlib import Path
import requests
API="https://api.github.com/repos/PokemonTCG/pokemon-tcg-data/git/trees/master?recursive=1"
RAW="https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/"
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--max-files",type=int,default=0);a=p.parse_args()
 s=requests.Session();s.headers["User-Agent"]="TheVault-Pokemon-Importer/1.0"
 tmp=tempfile.TemporaryDirectory(prefix="vault-pokemon-")
 checkout=Path(tmp.name)/"data"
 subprocess.run(["git","clone","--depth","1","--filter=blob:none","https://github.com/PokemonTCG/pokemon-tcg-data.git",str(checkout)],check=True,timeout=240)
 paths=sorted(str(x.relative_to(checkout)) for x in (checkout/"cards"/"en").glob("*.json"))
 if a.max_files:paths=paths[:a.max_files]
 if not paths:raise SystemExit("No Pokémon card JSON files discovered")
 out=[]
 for i,path in enumerate(paths):
  for x in json.loads((checkout/path).read_text(encoding="utf-8")):
   if not isinstance(x,dict) or not x.get("name"):continue
   images=x.get("images") or {}
   card_id=str(x.get("id") or "")
   out.append({"id":"pokemon-tcg:"+card_id,"name":str(x["name"]),"brand":"Pokémon","category":"Trading Cards","franchise":"Pokémon","identifier":card_id,"number":str(x.get("number") or ""),"series":str(x.get("set",{}).get("name") or path.rsplit("/",1)[-1].removesuffix(".json")),"variant":str(x.get("rarity") or ""),"image":images.get("small") or images.get("large") or "","source":"PokemonTCG/pokemon-tcg-data","sourceUrl":f"https://github.com/PokemonTCG/pokemon-tcg-data/blob/master/{path}","retailPrice":None,"marketValue":None})
  if i%30==0:print("Processed sets:",i+1,flush=True)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({"schema":"vault-pokemon-tcg-v1","count":len(out),"items":out},ensure_ascii=False),encoding="utf-8")
 print("Pokémon cards:",len(out))
if __name__=="__main__":main()
