"""Engineer WPIC vintage-aware point-in-time features from the uploaded vintage table.

Uses only exact publication dates and the same integrity exclusions as wpic_pit_prepare.
No value correction or interpolation. All availability is next UTC day because release
time is absent from the supplied extraction.

Features:
- balance / total demand
- total supply YoY growth
- total demand YoY growth
- total supply forecast/estimate revision vs previous accepted vintage of same target year
- total demand revision vs previous accepted vintage of same target year
- balance revision scaled by current total demand
"""
import argparse,json,hashlib,re
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED={
 "Above Ground Stocks","Automotive","Balance","Industrial","Investment",
 "Jewellery","Recycling","Total Demand","Total Mining Supply","Total Supply"
}
KEYS=["Total Supply","Total Demand","Balance"]

def _slug(s): return re.sub(r"[^a-z0-9]+","_",s.lower()).strip("_")

def _load_accepted(source):
    p=Path(source);df=pd.read_csv(p)
    df["pub_date_exact"]=df["pub_date_exact"].astype(str).str.lower().map({"true":True,"false":False}).fillna(df["pub_date_exact"].astype(bool))
    df["pub_dt"]=pd.to_datetime(df["pub_date"],dayfirst=True,utc=True,errors="raise")
    exact=df[df["pub_date_exact"]==True].copy()
    cur=exact[exact["year"]==exact["vintage_year"]].copy()
    complete=cur.groupby("vintage")["metric"].agg(lambda x:set(x))
    incomplete={v for v,m in complete.items() if m!=EXPECTED}
    wide=cur.pivot(index=["vintage","vintage_year","vintage_quarter","pub_dt"],
                   columns="metric",values="value_koz").reset_index()
    wide["supply_resid"]=wide["Total Supply"]-(wide["Total Mining Supply"]+wide["Recycling"])
    wide["demand_resid"]=wide["Total Demand"]-(wide["Automotive"]+wide["Jewellery"]+wide["Industrial"]+wide["Investment"])
    wide["balance_resid"]=wide["Balance"]-(wide["Total Supply"]-wide["Total Demand"])
    scale=(wide["Total Mining Supply"]<1000)|(wide["Recycling"]<500)|(wide["Total Supply"]<1000)|(wide["Total Demand"]<1000)
    identity=(wide["supply_resid"].abs()>50)|(wide["demand_resid"].abs()>100)|(wide["balance_resid"].abs()>100)
    bad=incomplete|set(wide.loc[scale|identity,"vintage"])
    cur=cur[~cur["vintage"].isin(bad)].copy()
    exact=exact[~exact["vintage"].isin(bad)].copy()
    return p,df,exact,cur,sorted(bad)

def _emit(rows,name,root):
    f=pd.DataFrame(rows).sort_values("available_at").drop_duplicates("available_at",keep="last")
    if len(f)<12: raise ValueError(f"{name}: only {len(f)} releases")
    path=root/f"{name}.csv";f.to_csv(path,index=False)
    return str(path),len(f)

def engineer(source,out):
    src,raw,exact,cur,bad=_load_accepted(source)
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    pub=cur[["vintage","vintage_year","vintage_quarter","pub_dt","is_forecast"]].drop_duplicates("vintage")
    current=cur.pivot(index="vintage",columns="metric",values="value_koz").join(pub.set_index("vintage")).reset_index()
    current=current.sort_values("pub_dt")
    # Previous-year values as they appeared in the SAME vintage: point-in-time safe.
    prev=exact[exact["year"]==exact["vintage_year"]-1].pivot(index="vintage",columns="metric",values="value_koz")
    current=current.set_index("vintage").join(prev[["Total Supply","Total Demand"]].rename(columns={
        "Total Supply":"prev_year_total_supply","Total Demand":"prev_year_total_demand"})).reset_index()

    specs={}
    def base(r,val):
        return {"period_end":f"{int(r.vintage_year)}-12-31T00:00:00+00:00",
          "available_at":(r.pub_dt+pd.Timedelta(days=1)).isoformat(),
          "value":float(val),"source":"USER_EXTRACTED_WPIC_ENGINEERED_PIT_EXACT_DATE_NEXT_DAY",
          "unit":"ratio","is_forecast":bool(r.is_forecast)}

    # Structural ratios / growth
    rows={"wpic_balance_to_demand_ratio":[],
          "wpic_total_supply_yoy_growth":[],
          "wpic_total_demand_yoy_growth":[],
          "wpic_total_supply_revision_pct":[],
          "wpic_total_demand_revision_pct":[],
          "wpic_balance_revision_to_demand":[]}
    for r in current.itertuples(index=False):
        if r._asdict()["Total Demand"]!=0:
            rows["wpic_balance_to_demand_ratio"].append(base(r,r.Balance/r._asdict()["Total Demand"]))
        ps=r.prev_year_total_supply;pdemand=r.prev_year_total_demand
        if pd.notna(ps) and ps!=0:
            rows["wpic_total_supply_yoy_growth"].append(base(r,r._asdict()["Total Supply"]/ps-1))
        if pd.notna(pdemand) and pdemand!=0:
            rows["wpic_total_demand_yoy_growth"].append(base(r,r._asdict()["Total Demand"]/pdemand-1))

    # Vintage revisions only compare accepted vintages for the SAME target year.
    for year,g in current.groupby("vintage_year",sort=True):
        g=g.sort_values("pub_dt")
        previous=None
        for _,r in g.iterrows():
            if previous is not None:
                for metric,name in [("Total Supply","wpic_total_supply_revision_pct"),("Total Demand","wpic_total_demand_revision_pct")]:
                    den=float(previous[metric])
                    if den!=0:
                        obj=type("R",(),r.to_dict())()
                        rows[name].append(base(obj,float(r[metric])/den-1))
                demand=float(r["Total Demand"])
                if demand!=0:
                    obj=type("R",(),r.to_dict())()
                    rows["wpic_balance_revision_to_demand"].append(base(obj,(float(r["Balance"])-float(previous["Balance"]))/demand))
            previous=r

    mapping={};counts={}
    for name,data in rows.items():
        mapping[name],counts[name]=_emit(data,name,root)
    manifest={
      "source_path":str(src),"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
      "excluded_vintages":bad,"value_corrections_made":False,
      "availability_rule":"exact pub_date only; next UTC day availability",
      "same_target_year_revision_only":True,
      "previous_year_growth_uses_same_vintage_values":True,
      "feature_paths":mapping,"feature_counts":counts
    }
    (root/"feature_paths_engineered.json").write_text(json.dumps(mapping,indent=2),encoding="utf-8")
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2))
    return manifest

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--out",default="outputs/features/wpic_engineered")
    a=p.parse_args();engineer(a.input,a.out)
if __name__=="__main__":main()
