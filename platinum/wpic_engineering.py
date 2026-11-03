"""Engineer WPIC vintage-aware point-in-time features from the uploaded vintage table.

Only exact publication dates and integrity-accepted vintages are used. No values are
corrected or interpolated. Because the supplied extraction has a publication DATE but
no time, every feature becomes available on the next UTC day.
"""
import argparse,hashlib,json,re
from pathlib import Path
import pandas as pd

EXPECTED={"Above Ground Stocks","Automotive","Balance","Industrial","Investment",
          "Jewellery","Recycling","Total Demand","Total Mining Supply","Total Supply"}

def _load(source):
    src=Path(source);df=pd.read_csv(src)
    df["pub_date_exact"]=df["pub_date_exact"].astype(str).str.lower().map({"true":True,"false":False})
    if df["pub_date_exact"].isna().any():raise ValueError("Invalid pub_date_exact")
    df["pub_dt"]=pd.to_datetime(df["pub_date"],dayfirst=True,utc=True,errors="raise")
    exact=df[df["pub_date_exact"]].copy()
    cur=exact[exact["year"]==exact["vintage_year"]].copy()
    complete=cur.groupby("vintage")["metric"].agg(lambda x:set(x))
    bad={v for v,m in complete.items() if m!=EXPECTED}
    wide=cur.pivot(index=["vintage","vintage_year","vintage_quarter","pub_dt"],
                   columns="metric",values="value_koz").reset_index()
    wide["supply_resid"]=wide["Total Supply"]-(wide["Total Mining Supply"]+wide["Recycling"])
    wide["demand_resid"]=wide["Total Demand"]-(wide["Automotive"]+wide["Jewellery"]+wide["Industrial"]+wide["Investment"])
    wide["balance_resid"]=wide["Balance"]-(wide["Total Supply"]-wide["Total Demand"])
    invalid=(wide["Total Mining Supply"]<1000)|(wide["Recycling"]<500)|(wide["Total Supply"]<1000)|(wide["Total Demand"]<1000)|\
            (wide["supply_resid"].abs()>50)|(wide["demand_resid"].abs()>100)|(wide["balance_resid"].abs()>100)
    bad |= set(wide.loc[invalid,"vintage"])
    exact=exact[~exact["vintage"].isin(bad)].copy()
    cur=cur[~cur["vintage"].isin(bad)].copy()
    return src,exact,cur,sorted(bad)

def _row(year,pub_dt,is_forecast,value):
    return {"period_end":f"{int(year)}-12-31T00:00:00+00:00",
            "available_at":(pub_dt+pd.Timedelta(days=1)).isoformat(),
            "value":float(value),
            "source":"USER_EXTRACTED_WPIC_ENGINEERED_PIT_EXACT_DATE_NEXT_DAY",
            "unit":"ratio","is_forecast":bool(is_forecast)}

def _write(root,name,rows):
    frame=pd.DataFrame(rows).sort_values("available_at").drop_duplicates("available_at",keep="last")
    if len(frame)<12:raise ValueError(f"{name}: only {len(frame)} valid releases")
    path=root/f"{name}.csv";frame.to_csv(path,index=False)
    return str(path),len(frame)

def engineer(source,out):
    src,exact,cur,bad=_load(source)
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    meta=cur[["vintage","vintage_year","vintage_quarter","pub_dt","is_forecast"]].drop_duplicates("vintage")
    current=cur.pivot(index="vintage",columns="metric",values="value_koz").join(meta.set_index("vintage")).reset_index()
    prev=exact[exact["year"]==exact["vintage_year"]-1].pivot(index="vintage",columns="metric",values="value_koz")
    current=current.set_index("vintage").join(prev[["Total Supply","Total Demand"]].rename(columns={
        "Total Supply":"prev_year_total_supply","Total Demand":"prev_year_total_demand"})).reset_index().sort_values("pub_dt")

    rows={k:[] for k in (
      "wpic_balance_to_demand_ratio","wpic_total_supply_yoy_growth","wpic_total_demand_yoy_growth",
      "wpic_total_supply_revision_pct","wpic_total_demand_revision_pct","wpic_balance_revision_to_demand")}

    for _,r in current.iterrows():
        year,pub,flag=int(r["vintage_year"]),r["pub_dt"],bool(r["is_forecast"])
        demand=float(r["Total Demand"])
        if demand!=0:rows["wpic_balance_to_demand_ratio"].append(_row(year,pub,flag,float(r["Balance"])/demand))
        ps=r.get("prev_year_total_supply");pdemand=r.get("prev_year_total_demand")
        if pd.notna(ps) and float(ps)!=0:rows["wpic_total_supply_yoy_growth"].append(_row(year,pub,flag,float(r["Total Supply"])/float(ps)-1))
        if pd.notna(pdemand) and float(pdemand)!=0:rows["wpic_total_demand_yoy_growth"].append(_row(year,pub,flag,demand/float(pdemand)-1))

    for year,g in current.groupby("vintage_year",sort=True):
        previous=None
        for _,r in g.sort_values("pub_dt").iterrows():
            if previous is not None:
                pub,flag=r["pub_dt"],bool(r["is_forecast"])
                for metric,name in (("Total Supply","wpic_total_supply_revision_pct"),("Total Demand","wpic_total_demand_revision_pct")):
                    denominator=float(previous[metric])
                    if denominator!=0:rows[name].append(_row(year,pub,flag,float(r[metric])/denominator-1))
                demand=float(r["Total Demand"])
                if demand!=0:rows["wpic_balance_revision_to_demand"].append(_row(year,pub,flag,(float(r["Balance"])-float(previous["Balance"]))/demand))
            previous=r

    mapping={};counts={}
    for name,data in rows.items():mapping[name],counts[name]=_write(root,name,data)
    manifest={"source_path":str(src),"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
      "excluded_vintages":bad,"value_corrections_made":False,
      "availability_rule":"exact pub_date only; next UTC day availability",
      "same_target_year_revision_only":True,"previous_year_growth_uses_same_vintage_values":True,
      "feature_paths":mapping,"feature_counts":counts}
    (root/"feature_paths_engineered.json").write_text(json.dumps(mapping,indent=2),encoding="utf-8")
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2));return manifest

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--out",default="outputs/features/wpic_engineered")
    a=p.parse_args();engineer(a.input,a.out)
if __name__=="__main__":main()
