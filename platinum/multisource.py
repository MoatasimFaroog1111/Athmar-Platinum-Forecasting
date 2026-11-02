"""Train a multi-source daily model only with verified point-in-time feature CSVs."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from .daily import load_daily,OZ_PER_KG
from .point_in_time import asof_feature,load_release_csv

def evaluate(csv,features,out="outputs/multisource"):
    if not features: raise ValueError("At least one independently verified fundamental or macro series required")
    bars=load_daily(csv)
    frame=bars[["Date","Close"]].copy()
    for name,path in features.items():
        if not name.isidentifier() or name in frame.columns: raise ValueError("Invalid metric identifier")
        releases=load_release_csv(path)
        if len(releases)<12:
            raise ValueError(f"{name}: at least 12 independent published observations required for model comparison")
        frame=asof_feature(frame,releases,name)
    if frame[list(features)].notna().any().sum()==0:
        raise ValueError("No historical released features available")
    price=np.log(frame.Close.to_numpy(dtype=float)*OZ_PER_KG)
    ret=np.diff(price)
    rows=[]
    names=list(features)
    for i in range(21,len(price)-1):
        vals=frame.iloc[i][names].to_numpy(dtype=float)
        rows.append((np.r_[ret[i-20:i],vals],price[i+1]-price[i]))
    X=np.vstack([x for x,y in rows]);y=np.asarray([y for x,y in rows])
    n=len(y);hold=int(n*.8)
    if hold<350 or n-hold<50:raise ValueError("Too few chronological samples")
    candidates={"no_change":None,
        "ridge":make_pipeline(SimpleImputer(strategy="median"),Ridge(alpha=1.0)),
        "boost":make_pipeline(SimpleImputer(strategy="median"),
           HistGradientBoostingRegressor(max_iter=60,max_leaf_nodes=10,random_state=42))}
    folds=[(int(hold*.55),int(hold*.65)),(int(hold*.67),int(hold*.77)),(int(hold*.8),int(hold*.9))]
    val={}
    for name in candidates:
        errors=[]
        for start,stop in folds:
            if name=="no_change":pred=np.zeros(stop-start)
            else:
                model=candidates[name]
                model.fit(X[:start-1],y[:start-1])
                pred=model.predict(X[start:stop])
            errors.append(float(np.mean(np.abs(y[start:stop]-pred))))
        val[name]=float(np.mean(errors))
    chosen=min(val,key=val.get)
    if chosen=="no_change":p=np.zeros(n-hold)
    else:
        model=candidates[chosen]
        model.fit(X[:hold-1],y[:hold-1])
        p=model.predict(X[hold:])
    baseline=float(np.abs(y[hold:]).mean())
    actual=float(np.abs(y[hold:]-p).mean())
    result={"status":"EXPERIMENTAL_NOT_PRODUCTION","feature_names":names,
      "observations":len(bars),"test_size":n-hold,
      "selection_validation_mae":val,"selected":chosen,"heldout_mae":actual,
      "heldout_baseline_mae":baseline,"beats_baseline":bool(actual<baseline),
      "verified_release_files":features,"forecast_to_2027":"NOT_CALIBRATED"}
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    (dest/"multisource_report.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--daily",required=True)
    ap.add_argument("--features",required=True,help="JSON file mapping feature names to verified release CSVs")
    ap.add_argument("--out",default="outputs/multisource")
    a=ap.parse_args()
    paths=json.loads(Path(a.features).read_text(encoding="utf-8"))
    print(json.dumps(evaluate(a.daily,paths,a.out),indent=2))
if __name__=="__main__":main()
