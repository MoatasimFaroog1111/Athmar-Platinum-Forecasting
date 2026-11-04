"""Cross-market point-in-time feature acquisition for each target metal.

Target metal is excluded from its own explanatory feature set. All same-day closes
become available to the model on the next UTC day to avoid same-close leakage.
"""
import argparse,json
from pathlib import Path
from platinum.market_features import fetch_one
from .config import METALS

EXTRA={"dollar_index":"DX-Y.NYB","zar_usd":"ZAR=X","us10y":"^TNX"}
METAL_FEATURES={k:v["symbol"] for k,v in METALS.items()}

def run(target,out):
    if target not in METALS: raise KeyError(target)
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    symbols={**{k:v for k,v in METAL_FEATURES.items() if k!=target},**EXTRA}
    mapping={}
    for name,symbol in symbols.items():
        f=fetch_one(name,symbol)
        path=root/f"{name}.csv";f.to_csv(path,index=False);mapping[name]=str(path)
    (root/"feature_paths.json").write_text(json.dumps(mapping,indent=2),encoding="utf-8")
    return mapping

def main():
    p=argparse.ArgumentParser();p.add_argument("--target",choices=METALS,required=True);p.add_argument("--out",required=True)
    a=p.parse_args();print(json.dumps({"target":a.target,"features":run(a.target,a.out)},indent=2))
if __name__=="__main__":main()
