"""Daily cross-market research features with next-day availability to avoid same-close leakage."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd, requests

SYMBOLS={
 "gold":"GC=F",
 "palladium":"PA=F",
 "silver":"SI=F",
 "dollar_index":"DX-Y.NYB",
 "zar_usd":"ZAR=X",
 "us10y":"^TNX",
}
URL="https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

def fetch_one(name,symbol,session=requests):
    r=session.get(URL.format(symbol=symbol),params={"range":"5y","interval":"1d"},
        headers={"User-Agent":"Mozilla/5.0 (Athmar research)"},timeout=45)
    r.raise_for_status();payload=r.json()
    result=(payload.get("chart") or {}).get("result")
    if not result:raise ValueError(f"No chart for {symbol}")
    entry=result[0];ts=entry.get("timestamp") or []
    closes=((entry.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    rows=[]
    for t,v in zip(ts,closes):
        if v is None:continue
        dt=pd.Timestamp(int(t),unit="s",tz="UTC").normalize()
        rows.append({"period_end":dt.isoformat(),"available_at":(dt+pd.Timedelta(days=1)).isoformat(),
          "value":float(v),"source":f"YAHOO_{symbol}_RESEARCH","unit":"vendor_native"})
    f=pd.DataFrame(rows).drop_duplicates("period_end").sort_values("available_at")
    if len(f)<500:raise ValueError(f"{name}: insufficient rows")
    return f

def run(out):
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    mapping={}
    for name,symbol in SYMBOLS.items():
        f=fetch_one(name,symbol)
        path=root/f"{name}.csv";f.to_csv(path,index=False);mapping[name]=str(path)
    (root/"feature_paths_market.json").write_text(json.dumps(mapping,indent=2),encoding="utf-8")
    print(json.dumps({"features":mapping,"status":"RESEARCH_VENDOR_DATA_NEXT_DAY_AVAILABLE"},indent=2))
    return mapping
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",default="outputs/features/market");a=p.parse_args();run(a.out)
if __name__=="__main__":main()
