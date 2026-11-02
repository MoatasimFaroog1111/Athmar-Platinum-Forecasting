"""Final research gate before any approval decision.

Uses disjoint train/validation/calibration/test blocks per horizon, purges labels,
selects model on validation only, calibrates intervals on a later block, and
tests both point error and interval coverage on untouched data.
"""
import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from .daily import load_daily,OZ_PER_KG
from .point_in_time import asof_feature,load_release_csv

HORIZONS=(1,5,20,60,90)
LAG=20
def _model(name):
    if name=="ridge":return make_pipeline(SimpleImputer(strategy="median"),Ridge(alpha=1.0))
    if name=="boost":return make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=12,l2_regularization=2,random_state=42))
    raise KeyError(name)

def _dataset(frame,feature_names,h):
    logp=np.log(frame.Close.to_numpy(float)*OZ_PER_KG);ret=np.diff(logp);X=[];y=[]
    for i in range(LAG,len(logp)-h):
        vals=frame.iloc[i][feature_names].to_numpy(float) if feature_names else np.empty(0)
        X.append(np.r_[ret[i-LAG:i],vals]);y.append(logp[i+h]-logp[i])
    return np.asarray(X),np.asarray(y)

def _wilson(k,n,z=1.96):
    if n==0:return 0.0,0.0
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;m=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return max(0,c-m),min(1,c+m)

def evaluate(daily,features,source_verified=False,nominal=.90):
    bars=load_daily(daily);frame=bars[["Date","Close"]].copy()
    names=[]
    for name,path in features.items():
        rel=load_release_csv(path)
        if len(rel)<12:raise ValueError(f"{name}: <12 independent releases")
        frame=asof_feature(frame,rel,name);names.append(name)
    results={};passes=[]
    for h in HORIZONS:
        X,y=_dataset(frame,names,h);n=len(y)
        a,b,c=int(n*.50),int(n*.65),int(n*.80)
        # purge horizon around every boundary
        train_end=max(0,a-h);val_start=a;val_end=b-h;cal_start=b;cal_end=c-h;test_start=c
        if min(train_end,val_end-val_start,cal_end-cal_start,n-test_start)<50:raise ValueError(f"h{h}: insufficient blocks")
        candidates={"no_change":None,"ridge":"ridge","boost":"boost"};val={}
        for key,spec in candidates.items():
            if spec is None:pred=np.zeros(val_end-val_start)
            else:
                m=_model(spec);m.fit(X[:train_end],y[:train_end]);pred=m.predict(X[val_start:val_end])
            val[key]=float(np.mean(np.abs(y[val_start:val_end]-pred)))
        champ=min(val,key=val.get)
        fit_end=max(0,b-h)
        if champ=="no_change":
            cal_pred=np.zeros(cal_end-cal_start);test_pred=np.zeros(n-test_start)
        else:
            m=_model(champ);m.fit(X[:fit_end],y[:fit_end])
            cal_pred=m.predict(X[cal_start:cal_end]);test_pred=m.predict(X[test_start:])
        cal_abs=np.abs(y[cal_start:cal_end]-cal_pred)
        rank=min(len(cal_abs)-1,max(0,math.ceil((len(cal_abs)+1)*nominal)-1))
        q=float(np.sort(cal_abs)[rank])
        covered=np.abs(y[test_start:]-test_pred)<=q;k=int(covered.sum());total=len(covered)
        lo,hi=_wilson(k,total)
        mae=float(np.mean(np.abs(y[test_start:]-test_pred)));base=float(np.mean(np.abs(y[test_start:])))
        # Gate: point model must not be materially worse; coverage target must be inside
        # observed 95% Wilson interval and realized coverage >= nominal-0.03.
        point_ok=mae<=base*1.01
        cover_ok=(k/total)>=nominal-.03 and lo<=nominal<=hi
        passed=point_ok and cover_ok
        passes.append(passed)
        results[str(h)]={"champion":champ,"validation_mae":val,"test_mae":mae,"baseline_mae":base,
          "point_gate":point_ok,"calibration_size":len(cal_abs),"test_size":total,"nominal":nominal,
          "coverage":k/total,"coverage_wilson95":[lo,hi],"interval_halfwidth_logreturn":q,
          "coverage_gate":cover_ok,"horizon_pass":passed}
    source_gate=bool(source_verified)
    overall=source_gate and all(passes)
    return {"status":"PASS" if overall else "FAIL","source_availability_verified":source_gate,
      "feature_names":names,"horizons":results,
      "required":{"all_horizons_pass":True,"source_availability_verified":True},
      "approval_recommendation":"ELIGIBLE_FOR_HUMAN_REVIEW" if overall else "BLOCK_APPROVAL"}

def main():
    p=argparse.ArgumentParser();p.add_argument("--daily",required=True);p.add_argument("--features",required=True)
    p.add_argument("--source-verified",action="store_true");p.add_argument("--out",default="outputs/preapproval")
    a=p.parse_args();paths=json.loads(Path(a.features).read_text())
    result=evaluate(a.daily,paths,a.source_verified);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/"gate.json").write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result,indent=2))
if __name__=="__main__":main()
