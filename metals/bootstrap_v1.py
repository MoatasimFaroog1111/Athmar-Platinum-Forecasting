"""One-time V1 bootstrap for Gold, Silver and Palladium.

Creates immutable pre-lock training snapshots, nested-walk-forward model locks and
prospective holdout protocols. It refuses to overwrite an existing V1 lock.
"""
import argparse, hashlib, json, shutil
from pathlib import Path
from metals.config import METALS,NEW_METALS,LOCK_START,ORIGIN_END,SCORE_NOT_BEFORE_UTC
from metals.price_source import fetch_metal
from metals.market_features import run as fetch_features
from platinum.nested_walkforward import select

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def bootstrap_metal(metal,work_root="outputs/metals/bootstrap"):
    if metal not in NEW_METALS: raise ValueError("Bootstrap is only for new metals")
    lock_path=Path(f"config/{metal}_model_lock_v1.json")
    protocol_path=Path(f"config/{metal}_prospective_holdout_v1.json")
    if lock_path.exists() or protocol_path.exists():
        raise RuntimeError(f"{metal} V1 already exists; refusing to overwrite immutable lock")

    work=Path(work_root)/metal; work.mkdir(parents=True,exist_ok=True)
    price=fetch_metal(metal,work/"prices")
    daily=Path(price["csv"])
    feature_map=fetch_features(metal,work/"features")
    nested=select(str(daily),{"market_cross":feature_map},LOCK_START)

    frozen=Path("data/locks")/metal/"v1"; feat_root=frozen/"features"
    feat_root.mkdir(parents=True,exist_ok=True)
    frozen_daily=frozen/f"{metal}_daily_prelock.csv"
    shutil.copy2(daily,frozen_daily)
    frozen_map={}
    for name,src in feature_map.items():
        dst=feat_root/f"{name}.csv";shutil.copy2(src,dst);frozen_map[name]=str(dst)
    (frozen/"feature_paths.json").write_text(json.dumps(frozen_map,indent=2),encoding="utf-8")

    protocol_id=f"ATHMAR_{metal.upper()}_APPROVAL_V1"
    protocol={
      "protocol_id":protocol_id,
      "locked_at_utc":"2026-11-04T12:00:00Z",
      "origin_start":LOCK_START,
      "origin_end":ORIGIN_END,
      "score_not_before_utc":SCORE_NOT_BEFORE_UTC,
      "horizons_business_days":[1,5,20,60,90],
      "nominal_interval_coverage":0.90,
      "minimum_mature_origins_per_horizon":100,
      "approval_rules":{
        "all_horizons_must_pass":True,
        "minimum_mae_improvement_vs_no_change":0.01,
        "coverage_wilson_95_ci_must_include_nominal":True,
        "realized_coverage_min":0.87,
        "realized_coverage_max":0.93
      },
      "governance":{
        "no_model_or_feature_tuning_after_lock":True,
        "no_holdout_metrics_before_score_not_before":True,
        "protocol_change_requires_new_future_holdout":True
      },
      "source_policy":{
        "target":price["manifest"]["instrument"],
        "target_status":"research_only_unlicensed_unverified_roll",
        "features":"Yahoo cross-market closes with next-UTC-day availability",
        "official_fundamentals_in_v1":False
      }
    }
    protocol_path.write_text(json.dumps(protocol,indent=2),encoding="utf-8")

    lock={
      "protocol_id":protocol_id,
      "metal":metal,
      "label":METALS[metal]["label"],
      "symbol":METALS[metal]["symbol"],
      "lock_start":LOCK_START,
      "feature_groups":{"market_cross":list(frozen_map.keys())},
      "horizons":nested["locked_candidates"],
      "nested_diagnostics":nested["horizons"],
      "training_snapshot":{
        "daily_path":str(frozen_daily),
        "daily_sha256":sha256(frozen_daily),
        "feature_paths":frozen_map,
        "feature_sha256":{k:sha256(v) for k,v in frozen_map.items()}
      },
      "governance":{
        "immutable":True,
        "post_lock_training_data_change_forbidden":True,
        "holdout_scoring_forbidden_before":SCORE_NOT_BEFORE_UTC
      }
    }
    lock_path.write_text(json.dumps(lock,indent=2),encoding="utf-8")
    return {
      "metal":metal,"protocol":str(protocol_path),"lock":str(lock_path),
      "selected":nested["locked_candidates"],"daily_sha256":lock["training_snapshot"]["daily_sha256"]
    }

def main():
    p=argparse.ArgumentParser();p.add_argument("--metal",choices=NEW_METALS);p.add_argument("--all",action="store_true")
    a=p.parse_args()
    targets=NEW_METALS if a.all else ((a.metal,) if a.metal else ())
    if not targets: raise SystemExit("Use --all or --metal")
    out=[bootstrap_metal(m) for m in targets]
    print(json.dumps(out,indent=2))

if __name__=="__main__":main()
