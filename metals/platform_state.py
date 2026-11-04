"""Build one dashboard payload for Platinum, Gold, Silver and Palladium."""
import argparse,json
from pathlib import Path
import pandas as pd
from metals.config import METALS,NEW_METALS
from platinum.daily import OZ_PER_KG,load_daily
from platinum.point_in_time import load_release_csv

def _json(p):return json.loads(Path(p).read_text(encoding="utf-8"))

def _journal(path):
    p=Path(path)
    if not p.exists():return {"status":"waiting_for_first_shadow_forecast","count":0,"latest":[],"latest_by_horizon":{}}
    df=pd.read_csv(p)
    if "outcome_scored" in df.columns and df["outcome_scored"].astype(str).str.lower().isin(["true","1","yes"]).any():
        raise ValueError("Scored holdout outcomes cannot enter dashboard state")
    latest_by={}
    for h,g in df.groupby("horizon"):
        r=g.iloc[-1];latest_by[str(int(h))]={k:(float(r[k]) if k.endswith("_usd_kg") else str(r[k]))
          for k in ("created_at","origin_date","target_date","forecast_usd_kg","p10_usd_kg","p90_usd_kg","record_hash")}
    return {"status":"active","count":len(df),"latest":df.tail(10).where(pd.notna(df.tail(10)),None).to_dict("records"),
      "latest_by_horizon":latest_by}

def _drivers(paths):
    out={}
    for name,path in paths.items():
        f=load_release_csv(path)
        if not f.empty:out[name]=float(f.iloc[-1].value)
    return out

def new_metal_state(metal,work_root="outputs/metals/live",journal_root="data/shadow/metals"):
    lock=_json(f"config/{metal}_model_lock_v1.json");protocol=_json(f"config/{metal}_prospective_holdout_v1.json")
    price_path=Path(work_root)/metal/"prices"/f"{metal}_daily_futures.csv"
    feature_path=Path(work_root)/metal/"features"/"feature_paths.json"
    market={"status":"unavailable","last_actual_date":None,"last_price_usd_kg":None,
      "instrument":f"YAHOO_{METALS[metal]['symbol']}_FUTURES_INDICATIVE"}
    if price_path.exists():
        d=load_daily(price_path);market.update({"status":"available","last_actual_date":d.Date.iloc[-1].date().isoformat(),
          "last_price_usd_kg":float(d.Close.iloc[-1]*OZ_PER_KG)})
    fmap=_json(feature_path) if feature_path.exists() else {}
    journal=_journal(Path(journal_root)/f"{metal}_forecast_journal.csv")
    horizons=[]
    for hs in ("1","5","20","60","90"):
        spec=lock["horizons"][hs]
        horizons.append({"horizon_days":int(hs),"model":spec["model"],"feature_group":spec["group"],
          "interval_q90_abs_logreturn":float(spec["q90_abs_logreturn"]),
          "mode":"baseline" if spec["model"]=="no_change" else "candidate","status":"locked_shadow",
          "latest_forecast":journal["latest_by_horizon"].get(hs)})
    return {"metal":{"key":metal,"label":METALS[metal]["label"],"symbol":METALS[metal]["symbol"]},
      "product":{"name":"Athmar Precious Metals Intelligence","mode":"SHADOW","environment":"production-shadow"},
      "market":market,
      "approval":{"protocol_id":protocol["protocol_id"],"status":"LOCKED","origin_start":protocol["origin_start"],
        "origin_end":protocol["origin_end"],"score_not_before_utc":protocol["score_not_before_utc"],
        "metrics_revealed":False,"nominal_interval_coverage":protocol["nominal_interval_coverage"],
        "minimum_mature_origins_per_horizon":protocol["minimum_mature_origins_per_horizon"]},
      "horizons":horizons,
      "context":{"title":"Cross-market Drivers","status":"market_only_v1","metrics":_drivers(fmap),
        "footnote":"Yahoo research futures/macro closes; next-UTC-day availability. No official fundamental dataset is claimed in V1."},
      "journal":journal,
      "integrity":{"prospective_holdout_metrics_exposed":False,"journal_outcomes_scored":False,
        "locked_model_source":f"config/{metal}_model_lock_v1.json","official_fundamentals_in_v1":False}}

def platinum_state(path="web/data/live-state.json"):
    s=_json(path);wpic=s["fundamentals"]["wpic"]
    return {"metal":{"key":"platinum","label":"Platinum","symbol":"PL=F"},"product":{"name":"Athmar Precious Metals Intelligence",
      "mode":s["product"]["mode"],"environment":s["product"]["environment"]},"market":s["market"],"approval":s["approval"],
      "horizons":s["horizons"],"context":{"title":"WPIC Fundamentals","status":wpic.get("status","unavailable"),
        "metrics":wpic.get("metrics",{}),"footnote":"Exact-date WPIC vintages; next-UTC-day availability; no reconstructed values."},
      "journal":s["journal"],"integrity":s["integrity"]}

def build(out,work_root="outputs/metals/live"):
    metals={"platinum":platinum_state()}
    for m in NEW_METALS:metals[m]=new_metal_state(m,work_root)
    payload={"default_metal":"platinum","metal_order":["platinum","gold","silver","palladium"],"metals":metals}
    p=Path(out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    return payload

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",default="web/data/metals-state.json");p.add_argument("--work-root",default="outputs/metals/live")
    a=p.parse_args();print(json.dumps(build(a.out,a.work_root),indent=2))
if __name__=="__main__":main()
