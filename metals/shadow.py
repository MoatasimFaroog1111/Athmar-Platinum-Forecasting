"""Shadow forecasts for independently locked Gold, Silver and Palladium V1 systems."""
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
from metals.config import NEW_METALS
from metals.price_source import fetch_metal
from metals.market_features import run as fetch_features
from platinum.daily import OZ_PER_KG,load_daily
from platinum.point_in_time import asof_feature,load_release_csv
from platinum.nested_walkforward import _dataset,_model,LAG

HASH_VERSION="v2"
COLUMNS=["metal","created_at","origin_date","origin_close_usd_kg","horizon","target_date",
 "forecast_usd_kg","p10_usd_kg","p90_usd_kg","model","feature_group",
 "model_lock_sha256","status","outcome_scored","hash_version","legacy_record_hash",
 "previous_hash","record_hash"]
FLOAT_FIELDS={"origin_close_usd_kg","forecast_usd_kg","p10_usd_kg","p90_usd_kg"}

def _sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def _json(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def _frame(daily_path,feature_paths):
    bars=load_daily(daily_path);f=bars[["Date","Close"]].copy()
    for name,path in feature_paths.items():f=asof_feature(f,load_release_csv(path),name)
    return f

def _canon(key,value):
    if key in FLOAT_FIELDS:return format(float(value),".17g")
    if key=="horizon":return str(int(value))
    if key=="outcome_scored":
        return "true" if str(value).strip().lower() in ("true","1","yes") else "false"
    if value is None:return ""
    if isinstance(value,float) and np.isnan(value):return ""
    return str(value)

def _row_hash(row):
    keys=[k for k in COLUMNS if k!="record_hash"]
    payload="|".join(f"{k}={_canon(k,row.get(k,''))}" for k in keys)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _migrate_legacy(frame):
    if "hash_version" in frame.columns:
        return frame,False
    f=frame.copy()
    if "outcome_scored" in f.columns and f["outcome_scored"].astype(str).str.lower().isin(["true","1","yes"]).any():
        raise ValueError("Cannot migrate a journal containing scored outcomes")
    f["hash_version"]=HASH_VERSION
    f["legacy_record_hash"]=f["record_hash"].astype(str)
    prev="GENESIS";new_hashes=[];prevs=[]
    for row in f.to_dict("records"):
        row["previous_hash"]=prev
        row["hash_version"]=HASH_VERSION
        prevs.append(prev)
        h=_row_hash(row);new_hashes.append(h);prev=h
    f["previous_hash"]=prevs;f["record_hash"]=new_hashes
    return f[COLUMNS],True

def verify_journal(frame):
    missing=[c for c in COLUMNS if c not in frame.columns]
    if missing:raise ValueError(f"Journal missing v2 columns: {missing}")
    prev="GENESIS"
    for r in frame.to_dict("records"):
        if str(r["hash_version"])!=HASH_VERSION:raise ValueError("Unsupported journal hash version")
        if str(r["previous_hash"])!=prev:raise ValueError("Journal chain broken")
        if str(r["record_hash"])!=_row_hash(r):raise ValueError("Journal record hash invalid")
        if str(r["outcome_scored"]).lower() not in ("false","0"):raise ValueError("Scored outcome found in shadow journal")
        prev=str(r["record_hash"])
    return prev

def _live_vector(frame,names):
    logp=np.log(frame.Close.to_numpy(float)*OZ_PER_KG)
    if len(logp)<LAG+1:raise ValueError("Insufficient live target history")
    vals=frame.iloc[-1][names].to_numpy(float) if names else np.empty(0)
    return np.r_[np.diff(logp)[-LAG:],vals].reshape(1,-1)

def _predict_return(lock,h,live_frame):
    spec=lock["horizons"][str(h)]
    if spec["model"]=="no_change":return 0.0
    group=spec["group"]; names=lock["feature_groups"][group]
    frozen=lock["training_snapshot"]
    train_frame=_frame(frozen["daily_path"],frozen["feature_paths"])
    X,y,_,_=_dataset(train_frame,names,h,pd.Timestamp(lock["lock_start"],tz="UTC"))
    model=_model(spec["model"]);model.fit(X,y)
    return float(model.predict(_live_vector(live_frame,names))[0])

def generate(metal,work_root="outputs/metals/live",journal_root="data/shadow/metals"):
    if metal not in NEW_METALS:raise ValueError("Use platinum/shadow_forecast.py for Platinum V1")
    lock_path=Path(f"config/{metal}_model_lock_v1.json");lock=_json(lock_path)
    if not lock["governance"]["immutable"]:raise ValueError("Model lock is not immutable")
    price=fetch_metal(metal,Path(work_root)/metal/"prices")
    live_features=fetch_features(metal,Path(work_root)/metal/"features")
    expected=lock["feature_groups"]["market_cross"]
    if list(live_features.keys())!=expected:raise ValueError("Live feature order differs from frozen lock")
    live_frame=_frame(price["csv"],live_features)
    origin=live_frame.Date.iloc[-1];origin_date=origin.date().isoformat()
    if origin_date<lock["lock_start"]:raise ValueError("Origin predates prospective lock")
    origin_price=float(live_frame.Close.iloc[-1]*OZ_PER_KG)
    created=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    journal=Path(journal_root)/f"{metal}_forecast_journal.csv";journal.parent.mkdir(parents=True,exist_ok=True)
    migrated=False
    if journal.exists():
        existing=pd.read_csv(journal,dtype=str,keep_default_na=False)
        existing,migrated=_migrate_legacy(existing)
        prev=verify_journal(existing)
    else:
        existing=pd.DataFrame(columns=COLUMNS);prev="GENESIS"
    keys=set(zip(existing.get("origin_date",[]).astype(str),existing.get("horizon",[]).astype(str)))
    rows=[]
    for hs in ("1","5","20","60","90"):
        h=int(hs);spec=lock["horizons"][hs]
        pred_ret=_predict_return(lock,h,live_frame)
        point=origin_price*float(np.exp(pred_ret));q=float(spec["q90_abs_logreturn"])
        row={"metal":metal,"created_at":created,"origin_date":origin_date,"origin_close_usd_kg":origin_price,
          "horizon":h,"target_date":(pd.Timestamp(origin)+pd.offsets.BDay(h)).date().isoformat(),
          "forecast_usd_kg":point,"p10_usd_kg":point*float(np.exp(-q)),"p90_usd_kg":point*float(np.exp(q)),
          "model":spec["model"],"feature_group":spec["group"],"model_lock_sha256":_sha(lock_path),
          "status":"shadow_locked","outcome_scored":False,"hash_version":HASH_VERSION,"legacy_record_hash":"",
          "previous_hash":prev,"record_hash":""}
        if (origin_date,str(h)) in keys:continue
        row["record_hash"]=_row_hash(row);prev=row["record_hash"];rows.append(row)
    if rows or migrated:
        out=pd.concat([existing,pd.DataFrame(rows,columns=COLUMNS)],ignore_index=True) if rows else existing
        verify_journal(out);out.to_csv(journal,index=False)
    return {"metal":metal,"origin_date":origin_date,"new_records":len(rows),"journal":str(journal),
      "journal_hash_version":HASH_VERSION,"legacy_preview_migrated":migrated,
      "price_csv":price["csv"],"feature_paths":live_features,"prospective_metrics_scored":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--metal",choices=NEW_METALS);p.add_argument("--all",action="store_true")
    a=p.parse_args();targets=NEW_METALS if a.all else ((a.metal,) if a.metal else ())
    if not targets:raise SystemExit("Use --all or --metal")
    print(json.dumps([generate(m) for m in targets],indent=2))
if __name__=="__main__":main()
