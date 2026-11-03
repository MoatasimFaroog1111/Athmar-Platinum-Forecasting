"""Governed prospective holdout scorer.

Before score_not_before_utc this module refuses to compute or reveal holdout metrics.
After unlock it uses the immutable locked model manifest and fixed feature groups.
Any protocol/model hash mismatch blocks scoring.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from .daily import load_daily,OZ_PER_KG
from .point_in_time import asof_feature,load_release_csv

def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _model(name):
    if name.startswith("ridge_"):
        return make_pipeline(SimpleImputer(strategy="median"),Ridge(alpha=float(name.split("_",1)[1])))
    if name=="boost":
        return make_pipeline(SimpleImputer(strategy="median"),
            HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=12,l2_regularization=2,random_state=42))
    if name=="no_change":return None
    raise KeyError(name)

def _wilson(k,n,z=1.96):
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;m=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return max(0,c-m),min(1,c+m)

def locked_status(protocol,model_lock,now=None):
    cfg=json.loads(Path(protocol).read_text());lock=json.loads(Path(model_lock).read_text())
    now=pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now,tz="UTC")
    unlock=pd.Timestamp(cfg["score_not_before_utc"])
    if now<unlock:
        return {"status":"LOCKED","protocol_id":cfg["protocol_id"],
                "origin_start":cfg["origin_start"],"origin_end":cfg["origin_end"],
                "score_not_before_utc":cfg["score_not_before_utc"],
                "metrics_revealed":False,"model_lock_sha256":_sha(model_lock)}
    return {"status":"UNLOCKED","metrics_revealed":False,"model_lock_sha256":_sha(model_lock)}

def main():
    p=argparse.ArgumentParser();p.add_argument("--protocol",required=True);p.add_argument("--model-lock",required=True)
    p.add_argument("--status-only",action="store_true")
    a=p.parse_args()
    status=locked_status(a.protocol,a.model_lock)
    # The implementation intentionally exposes status only until a future commit adds
    # post-unlock scoring review. This prevents accidental peeking during development.
    print(json.dumps(status,indent=2))
    if status["status"]!="LOCKED" and not a.status_only:
        raise SystemExit("Prospective scoring requires a separately reviewed post-unlock scorer commit")
if __name__=="__main__":main()
