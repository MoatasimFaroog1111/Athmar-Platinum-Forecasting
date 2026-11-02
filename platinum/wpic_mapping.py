"""Map WPIC workbook cells to numeric measures only with explicit audited mappings.
Mapping JSON: [{file,sheet,cell,metric,period_end,unit,published_at,source_url}]
One cell equals one economic observation; no guesswork or implicit quarter labels.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

def extract_verified_mapping(directory,mapping):
    cfg=json.loads(Path(mapping).read_text(encoding="utf-8"))
    if not isinstance(cfg,list) or not cfg:raise ValueError("No audited WPIC mappings provided")
    rows=[]
    for item in cfg:
        needed={"file","sheet","cell","metric","period_end","unit","published_at","source_url"}
        if not needed.issubset(item):raise ValueError("WPIC mapping requires complete provenance")
        path=Path(directory)/item["file"]
        if not path.is_file():raise FileNotFoundError(path)
        book=load_workbook(path,data_only=True,read_only=True)
        if item["sheet"] not in book.sheetnames:raise ValueError("WPIC sheet not found")
        val=book[item["sheet"]][item["cell"]].value
        if isinstance(val,bool) or not isinstance(val,(int,float)):raise ValueError("WPIC mapped value must be numeric")
        released=pd.Timestamp(item["published_at"],tz="UTC") if "Z" not in str(item["published_at"]) and "+" not in str(item["published_at"]) else pd.Timestamp(item["published_at"]).tz_convert("UTC")
        period=pd.Timestamp(item["period_end"],tz="UTC")
        if released<period:raise ValueError("WPIC release predates measurement period")
        rows.append({"metric":item["metric"],"period_end":period.isoformat(),
                     "available_at":released.isoformat(),"value":float(val),"unit":item["unit"],
                     "source":item["source_url"],"sheet":item["sheet"],"cell":item["cell"]})
    return pd.DataFrame(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",required=True);p.add_argument("--mapping",required=True)
    p.add_argument("--out",default="outputs/verified_wpic.csv")
    a=p.parse_args()
    f=extract_verified_mapping(a.raw,a.mapping)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    f.to_csv(a.out,index=False)
    print(json.dumps({"verified_metrics":len(f),"output":a.out}))
if __name__=="__main__":main()
