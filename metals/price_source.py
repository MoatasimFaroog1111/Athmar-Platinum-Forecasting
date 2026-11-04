"""Research-only generic Yahoo futures acquisition for Athmar precious metals."""
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd, requests
from .config import METALS

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

def parse_chart(payload):
    chart=payload.get("chart") or {}
    if chart.get("error"): raise ValueError(f"Vendor error: {chart['error']}")
    result=chart.get("result")
    if not result or len(result)!=1: raise ValueError("No unique Yahoo chart")
    entry=result[0]; meta=entry.get("meta") or {}
    if meta.get("currency")!="USD": raise ValueError(f"Expected USD, got {meta.get('currency')!r}")
    quote=(entry.get("indicators") or {}).get("quote") or []
    ts=entry.get("timestamp") or []
    closes=(quote[0].get("close") or []) if len(quote)==1 else []
    if len(ts)!=len(closes): raise ValueError("Malformed chart")
    rows=[]
    for t,c in zip(ts,closes):
        if c is None: continue
        v=float(c)
        if not (0<v<1_000_000): raise ValueError("Invalid close")
        rows.append((datetime.fromtimestamp(int(t),tz=timezone.utc).date().isoformat(),v))
    f=pd.DataFrame(rows,columns=["Date","Close"])
    if len(f)<280 or f.Date.duplicated().any() or not f.Date.is_monotonic_increasing:
        raise ValueError("Insufficient, duplicate or unordered daily bars")
    return f

def fetch_metal(metal,out,session=requests):
    if metal not in METALS: raise KeyError(metal)
    cfg=METALS[metal]
    r=session.get(URL.format(symbol=cfg["symbol"]),params={"range":"5y","interval":"1d"},
        headers={"User-Agent":"Mozilla/5.0 (Athmar Precious Metals Research/1.0)"},timeout=45)
    r.raise_for_status(); raw=r.content; frame=parse_chart(r.json())
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    raw_path=root/f"{metal}_vendor_response.json"; raw_path.write_bytes(raw)
    csv_path=root/f"{metal}_daily_futures.csv";frame.to_csv(csv_path,index=False)
    manifest={"metal":metal,"instrument":f"Yahoo Finance {cfg['symbol']} futures indicative chart",
      "symbol":cfg["symbol"],"price_unit":"USD/troy_oz","target_price_unit":"USD/kg",
      "source":URL.format(symbol=cfg["symbol"]),"query":"range=5y&interval=1d",
      "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"raw_sha256":hashlib.sha256(raw).hexdigest(),
      "row_count":len(frame),"first_date":frame.Date.iloc[0],"last_date":frame.Date.iloc[-1],
      "status":"research_only_unlicensed_unverified_roll",
      "warning":"Futures chart, not licensed spot. Confirm vendor terms and contract roll before production use."}
    (root/f"{metal}_provenance.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return {"csv":str(csv_path),"manifest":manifest}

def main():
    p=argparse.ArgumentParser();p.add_argument("--metal",choices=METALS,required=True);p.add_argument("--out",default="outputs/metals/prices")
    a=p.parse_args();print(json.dumps(fetch_metal(a.metal,a.out),indent=2))
if __name__=="__main__":main()
