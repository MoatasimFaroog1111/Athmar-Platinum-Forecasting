"""Create actual CFTC-managed-money observations with explicitly conservative *assumed* availability.

This is not a verified release calendar. Dates never represent confirmed releases.
Require 10-day embargo from Tuesday observation to avoid default Friday peeking.
Data remain tagged as ASSUMED and must not claim verified point-in-time quality.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from .fundamentals import cftc_extract

def export(raw,out):
    files=sorted(Path(raw).glob("cftc_*.zip"))
    if not files:raise ValueError("No original CFTC archives")
    rows=[]
    for file in files:
        for market,report_date,unused,position in cftc_extract(file):
            release=pd.Timestamp(report_date,tz="UTC")+pd.Timedelta(days=10)
            rows.append({"market":market,"period_end":report_date,"available_at":release.isoformat(),
                "value":position,"source":"CFTC_ARCHIVE_ASSUMED_10_DAY_EMBARGO",
                "unit":"net_futures_contracts","source_file":file.name})
    frame=pd.DataFrame(rows).drop_duplicates(subset=["market","period_end"])
    if len(frame)<100:raise ValueError("Insufficient historical CFTC observations")
    selected=frame.sort_values(["period_end","market"]).drop_duplicates("period_end",keep="first")
    if selected.period_end.duplicated().any():raise ValueError("Ambiguous CFTC markets")
    dest=Path(out);dest.parent.mkdir(parents=True,exist_ok=True)
    selected.sort_values("available_at").to_csv(dest,index=False)
    return {"rows":len(selected),"first_report":selected.period_end.min(),
      "last_report":selected.period_end.max(),"publication_status":"ASSUMED_EMBARGO_NOT_VERIFIED",
      "out":str(dest)}

def main():
    p=argparse.ArgumentParser();p.add_argument("--raw",default="raw/acquired")
    p.add_argument("--out",default="outputs/features/cftc_managed_money_assumed.csv")
    a=p.parse_args()
    print(json.dumps(export(a.raw,a.out),indent=2))
if __name__=="__main__":main()
