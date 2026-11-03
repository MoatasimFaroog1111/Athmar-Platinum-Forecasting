"""Nested expanding-window model/feature selection using PRE-LOCK data only.

The prospective approval holdout begins at a fixed origin date. Samples whose origin
or target reaches the lock date are excluded from every selection, fit, calibration,
and diagnostic calculation in this module.
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

HORIZONS=(1,5,20,60,90);LAG=20

def _model(spec):
    if spec.startswith("ridge_"):
        alpha=float(spec.split("_",1)[1])
        return make_pipeline(SimpleImputer(strategy="median"),Ridge(alpha=alpha))
    if spec=="boost":
        return make_pipeline(SimpleImputer(strategy="median"),
          HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=12,l2_regularization=2,random_state=42))
    raise KeyError(spec)

def _frame(daily,features):
    bars=load_daily(daily);f=bars[["Date","Close"]].copy()
    for name,path in features.items():
        rel=load_release_csv(path)
        if len(rel)<12:raise ValueError(f"{name}: <12 releases")
        f=asof_feature(f,rel,name)
    return f

def _dataset(frame,names,h,lock_start):
    logp=np.log(frame.Close.to_numpy(float)*OZ_PER_KG);ret=np.diff(logp)
    dates=pd.to_datetime(frame.Date,utc=True)
    X=[];y=[];orig=[];target=[]
    for i in range(LAG,len(logp)-h):
        origin=dates.iloc[i];dest=dates.iloc[i+h]
        if origin>=lock_start or dest>=lock_start:continue
        vals=frame.iloc[i][names].to_numpy(float) if names else np.empty(0)
        X.append(np.r_[ret[i-LAG:i],vals]);y.append(logp[i+h]-logp[i])
        orig.append(origin);target.append(dest)
    return np.asarray(X),np.asarray(y),pd.DatetimeIndex(orig),pd.DatetimeIndex(target)

def _candidate_predict(spec,trainX,trainY,testX):
    if spec["model"]=="no_change":return np.zeros(len(testX))
    m=_model(spec["model"]);m.fit(trainX,trainY);return m.predict(testX)

def _inner_score(X,y,h,candidate):
    n=len(y)
    starts=[int(n*q) for q in (.62,.74,.86)]
    scores=[]
    for start in starts:
        stop=min(n,start+max(30,int(n*.08)))
        train_end=start-h
        if train_end<180 or stop-start<20:continue
        pred=_candidate_predict(candidate,X[:train_end],y[:train_end],X[start:stop])
        scores.append(float(np.mean(np.abs(y[start:stop]-pred))))
    if len(scores)<2:return float("inf")
    return float(np.mean(scores))

def _outer_splits(n,h):
    # Four chronological evaluation blocks. Labels are purged by the horizon.
    starts=[int(n*q) for q in (.56,.67,.78,.89)]
    out=[]
    for start in starts:
        stop=min(n,start+max(35,int(n*.09)))
        train_end=start-h
        if train_end>=250 and stop-start>=25:out.append((train_end,start,stop))
    if len(out)<3:raise ValueError("Insufficient nested outer folds")
    return out

def select(daily,groups,lock_start):
    lock=pd.Timestamp(lock_start,tz="UTC")
    frames={name:_frame(daily,paths) for name,paths in groups.items()}
    results={};locked={}
    models=("ridge_0.1","ridge_1.0","ridge_10.0","boost")
    for h in HORIZONS:
        datasets={}
        for g,frame in frames.items():
            datasets[g]=_dataset(frame,list(groups[g]),h,lock)
        # all groups must resolve to the identical price-origin sample.
        ref_orig=next(iter(datasets.values()))[2]
        if any(not ref_orig.equals(v[2]) for v in datasets.values()):raise ValueError("Feature groups changed origins")
        candidates=[{"group":"price_only","model":"no_change"}]
        candidates += [{"group":g,"model":m} for g in groups for m in models]
        outer=[]
        for train_end,start,stop in _outer_splits(len(ref_orig),h):
            inner={}
            for c in candidates:
                if c["model"]=="no_change":
                    X,y,_,_=next(iter(datasets.values()))
                else:X,y,_,_=datasets[c["group"]]
                inner[f'{c["group"]}|{c["model"]}']=_inner_score(X[:start],y[:start],h,c)
            best=min(inner,key=inner.get);group,model=best.split("|",1)
            chosen={"group":group,"model":model}
            if model=="no_change":X,y,_,_=next(iter(datasets.values()))
            else:X,y,_,_=datasets[group]
            pred=_candidate_predict(chosen,X[:train_end],y[:train_end],X[start:stop])
            outer.append({"selected":best,"mae":float(np.mean(np.abs(y[start:stop]-pred))),
                          "baseline_mae":float(np.mean(np.abs(y[start:stop]))),
                          "start":start,"stop":stop})
        # Final candidate is selected only by inner walk-forward over ALL pre-lock history.
        full_scores={}
        for c in candidates:
            if c["model"]=="no_change":X,y,_,_=next(iter(datasets.values()))
            else:X,y,_,_=datasets[c["group"]]
            full_scores[f'{c["group"]}|{c["model"]}']=_inner_score(X,y,h,c)
        best=min(full_scores,key=full_scores.get);group,model=best.split("|",1)
        final={"group":group,"model":model}
        if model=="no_change":X,y,orig,target=next(iter(datasets.values()))
        else:X,y,orig,target=datasets[group]
        # Walk-forward residuals for interval calibration, still entirely pre-lock.
        residual=[];cal_folds=[]
        for train_end,start,stop in _outer_splits(len(y),h):
            pred=_candidate_predict(final,X[:train_end],y[:train_end],X[start:stop])
            residual.extend(np.abs(y[start:stop]-pred).tolist())
            cal_folds.append([start,stop])
        residual=np.asarray(residual)
        rank=min(len(residual)-1,max(0,math.ceil((len(residual)+1)*.90)-1))
        q=float(np.sort(residual)[rank])
        signature=hashlib.sha256(("|".join(map(str,orig.astype(str)))+f"|h={h}|lock={lock_start}").encode()).hexdigest()[:20]
        results[str(h)]={"outer_nested":outer,"final_inner_scores":full_scores,
            "locked_candidate":final,"calibration_q90_abs_logreturn":q,
            "calibration_residual_count":len(residual),"prelock_samples":len(y),
            "last_prelock_origin":orig[-1].isoformat(),"last_prelock_target":target[-1].isoformat(),
            "prelock_sample_signature":signature}
        locked[str(h)]={"group":group,"model":model,"q90_abs_logreturn":q,
                        "prelock_sample_signature":signature}
    return {"protocol":"NESTED_WALK_FORWARD_V1","lock_start":lock_start,
            "horizons":results,"locked_candidates":locked}

def main():
    p=argparse.ArgumentParser();p.add_argument("--daily",required=True);p.add_argument("--groups",required=True)
    p.add_argument("--lock-start",required=True);p.add_argument("--out",default="outputs/nested_lock_candidate.json")
    a=p.parse_args();groups=json.loads(Path(a.groups).read_text())
    result=select(a.daily,groups,a.lock_start)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
