"""Build a read-only dashboard snapshot from the current research/shadow engine.

This module never scores the prospective holdout and never mutates model/protocol files.
Missing live/shadow outputs are represented explicitly as unavailable instead of synthesized.
"""
import argparse,json
from pathlib import Path
import pandas as pd
from .daily import OZ_PER_KG,load_daily

def _read_json(path,default=None):
    p=Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default

def _latest_wpic(path):
    p=Path(path)
    if not p.is_file(): return {"status":"unavailable","vintage":None,"published_at":None,"metrics":{}}
    df=pd.read_csv(p)
    exact=df[df["pub_date_exact"].astype(str).str.lower()=="true"].copy()
    if exact.empty:return {"status":"unavailable","vintage":None,"published_at":None,"metrics":{}}
    exact["pub_dt"]=pd.to_datetime(exact["pub_date"],dayfirst=True,utc=True,errors="coerce")
    latest=exact.loc[exact["pub_dt"].idxmax()]
    vintage=latest["vintage"];year=int(latest["vintage_year"])
    rows=exact[(exact["vintage"]==vintage)&(exact["year"]==year)]
    metrics={r.metric:float(r.value_koz) for r in rows.itertuples(index=False)}
    return {"status":"available","vintage":vintage,"published_at":latest["pub_dt"].isoformat(),
            "year":year,"unit":"koz","metrics":metrics}

def _journal(path):
    p=Path(path)
    if not p.is_file():
        return {"status":"waiting_for_first_shadow_forecast","count":0,"latest":[]}
    df=pd.read_csv(p)
    if df.empty:return {"status":"waiting_for_first_shadow_forecast","count":0,"latest":[]}
    cols=[c for c in ("created_at","origin_date","horizon","target_date","forecast_usd_kg","p10_usd_kg","p90_usd_kg","model_hash","status") if c in df.columns]
    latest=df.tail(8)[cols].where(pd.notna(df.tail(8)[cols]),None).to_dict("records")
    return {"status":"active","count":len(df),"latest":latest}

def build_snapshot(protocol_path="config/prospective_holdout_v1.json",
                   model_lock_path="config/model_lock_v1.json",
                   price_csv=None,
                   wpic_csv="data/verified/platinum_supply_demand_pit_user_extracted.csv",
                   journal_csv="outputs/shadow/forecast_journal.csv"):
    protocol=_read_json(protocol_path,{})
    lock=_read_json(model_lock_path,{})
    if not protocol or not lock:raise ValueError("Protocol and model lock are required")
    market={"status":"unavailable","last_actual_date":None,"last_price_usd_kg":None,"instrument":"YAHOO_PL_F_FUTURES_INDICATIVE"}
    if price_csv and Path(price_csv).is_file():
        df=load_daily(price_csv)
        market.update({"status":"available","last_actual_date":df.Date.iloc[-1].date().isoformat(),
                       "last_price_usd_kg":float(df.Close.iloc[-1]*OZ_PER_KG)})
    horizons=[]
    for h in ("1","5","20","60","90"):
        item=lock["horizons"][h]
        horizons.append({"horizon_days":int(h),"model":item["model"],"feature_group":item["group"],
                         "interval_q90_abs_logreturn":float(item["q90_abs_logreturn"]),
                         "mode":"candidate" if item["model"]!="no_change" else "baseline",
                         "status":"locked_shadow"})
    return {
      "product":{"name":"Athmar Platinum Intelligence","mode":"SHADOW","environment":"research"},
      "market":market,
      "approval":{"protocol_id":protocol["protocol_id"],"status":"LOCKED",
        "origin_start":protocol["origin_start"],"origin_end":protocol["origin_end"],
        "score_not_before_utc":protocol["score_not_before_utc"],"metrics_revealed":False,
        "nominal_interval_coverage":protocol["nominal_interval_coverage"],
        "minimum_mature_origins_per_horizon":protocol["minimum_mature_origins_per_horizon"]},
      "horizons":horizons,
      "fundamentals":{"wpic":_latest_wpic(wpic_csv)},
      "journal":_journal(journal_csv),
      "integrity":{"prospective_holdout_metrics_exposed":False,
        "cftc_used_for_approval":False,
        "locked_model_source":"config/model_lock_v1.json"}
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--price-csv")
    p.add_argument("--out",default="outputs/platform/state.json")
    a=p.parse_args()
    state=build_snapshot(price_csv=a.price_csv)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(state,indent=2),encoding="utf-8")
    print(json.dumps(state,indent=2))
if __name__=="__main__":main()
