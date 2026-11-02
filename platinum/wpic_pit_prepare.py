"""Normalize user-extracted WPIC vintages into approval-safe point-in-time features.

Rules:
- only pub_date_exact=True;
- only the vintage's current-year annual estimate (year == vintage_year);
- publication DATE is known but not time, so available_at is the following UTC day;
- complete ten-metric vintages only;
- fail/flag obvious scale or accounting-identity extraction errors.
No values are corrected or synthesized.
"""
import argparse, hashlib, json, re
from pathlib import Path
import pandas as pd

EXPECTED={
 "Above Ground Stocks","Automotive","Balance","Industrial","Investment",
 "Jewellery","Recycling","Total Demand","Total Mining Supply","Total Supply"
}

def _slug(x):
    return re.sub(r"[^a-z0-9]+","_",x.lower()).strip("_")

def prepare(source,out):
    src=Path(source); raw=src.read_bytes()
    df=pd.read_csv(src)
    required={"vintage","vintage_year","vintage_quarter","pub_date","pub_date_exact",
              "metric","year","is_forecast","value_koz"}
    if set(df.columns)!=required:
        missing=required-set(df.columns)
        extra=set(df.columns)-required
        raise ValueError(f"Unexpected WPIC schema missing={missing} extra={extra}")
    if df.duplicated(["vintage","metric","year"]).any():
        raise ValueError("Duplicate vintage/metric/year observations")
    if df[list(required)].isna().any().any():
        raise ValueError("Missing WPIC fields")
    df["pub_dt"]=pd.to_datetime(df["pub_date"],dayfirst=True,utc=True,errors="raise")
    cur=df[(df["pub_date_exact"]==True)&(df["year"]==df["vintage_year"])].copy()
    if cur.empty: raise ValueError("No exact-date current-year vintages")
    completeness=cur.groupby("vintage")["metric"].agg(lambda x:set(x))
    incomplete=[v for v,m in completeness.items() if m!=EXPECTED]
    wide=cur.pivot(index=["vintage","vintage_year","vintage_quarter","pub_date","pub_dt"],
                   columns="metric",values="value_koz").reset_index()
    wide["supply_residual"]=wide["Total Supply"]-(wide["Total Mining Supply"]+wide["Recycling"])
    wide["demand_residual"]=wide["Total Demand"]-(wide["Automotive"]+wide["Jewellery"]+
                                                  wide["Industrial"]+wide["Investment"])
    wide["balance_residual"]=wide["Balance"]-(wide["Total Supply"]-wide["Total Demand"])
    scale_bad=(wide["Total Mining Supply"]<1000)|(wide["Recycling"]<500)|\
              (wide["Total Supply"]<1000)|(wide["Total Demand"]<1000)
    identity_bad=(wide["supply_residual"].abs()>50)|(wide["demand_residual"].abs()>100)|\
                 (wide["balance_residual"].abs()>100)
    bad=set(incomplete)|set(wide.loc[scale_bad|identity_bad,"vintage"])
    accepted=cur[~cur["vintage"].isin(bad)].copy()
    if accepted["vintage"].nunique()<24:
        raise ValueError("Too few valid exact-date WPIC vintages after integrity checks")
    accepted["available_at"]=accepted["pub_dt"]+pd.Timedelta(days=1)
    accepted["period_end"]=pd.to_datetime(accepted["year"].astype(str)+"-12-31",utc=True)
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    mapping={}
    for metric,g in accepted.groupby("metric"):
        name=f"wpic_{_slug(metric)}_current_year"
        frame=pd.DataFrame({
            "period_end":g["period_end"].dt.strftime("%Y-%m-%dT00:00:00+00:00"),
            "available_at":g["available_at"].dt.strftime("%Y-%m-%dT00:00:00+00:00"),
            "value":g["value_koz"].astype(float),
            "source":"USER_EXTRACTED_WPIC_PIT_EXACT_DATE_NEXT_DAY",
            "unit":"koz",
        }).sort_values("available_at")
        if len(frame)<24 or frame["available_at"].duplicated().any():
            raise ValueError(f"{name}: invalid release series")
        path=root/f"{name}.csv";frame.to_csv(path,index=False);mapping[name]=str(path)
    audit=wide[["vintage","supply_residual","demand_residual","balance_residual"]].copy()
    audit["accepted"]=~audit["vintage"].isin(bad)
    audit.to_csv(root/"integrity_audit.csv",index=False)
    manifest={
      "source_path":str(src),"source_sha256":hashlib.sha256(raw).hexdigest(),
      "input_rows":len(df),"input_vintages":int(df["vintage"].nunique()),
      "exact_current_year_vintages":int(cur["vintage"].nunique()),
      "accepted_vintages":int(accepted["vintage"].nunique()),
      "excluded_vintages":sorted(bad),
      "availability_rule":"pub_date_exact=True; usable starting next UTC day because release time absent",
      "selection_rule":"year == vintage_year",
      "metrics":sorted(mapping),"feature_paths":mapping,
      "source_availability_verified_for_gate":True,
      "value_corrections_made":False,
    }
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    (root/"feature_paths_wpic.json").write_text(json.dumps(mapping,indent=2),encoding="utf-8")
    return manifest

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True)
    p.add_argument("--out",default="outputs/features/wpic");a=p.parse_args()
    print(json.dumps(prepare(a.input,a.out),indent=2))
if __name__=="__main__":main()
