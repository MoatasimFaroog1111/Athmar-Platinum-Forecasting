"""Four-way chronological evaluation and split-conformal interval coverage.

Selection: early validation, interval calibration: separate later block, assessment:
final untouched block. This is single-session research ONLY. No future-year
coverage guarantee. Nonstationarity can invalidate conformal exchangeability.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from .daily import load_daily, OZ_PER_KG

def lag_matrix(prices, lag=20):
    p=np.log(np.asarray(prices,dtype=float))
    r=np.diff(p)
    x=[];y=[]
    for k in range(lag,len(r)):
        x.append(r[k-lag:k])
        y.append(r[k])
    return np.asarray(x),np.asarray(y)

def assess(prices,alpha=.1):
    x,y=lag_matrix(prices)
    n=len(y)
    a,b,c=(int(n*q) for q in (.55,.7,.82))
    if a<250 or b-a<80 or c-b<80 or n-c<80:raise ValueError("Insufficient independent time blocks")
    candidates={"no_change":None,"ridge":Ridge(alpha=1.0),
        "boost":HistGradientBoostingRegressor(max_iter=75,max_leaf_nodes=12,random_state=42)}
    validation={}
    for name,model in candidates.items():
        if model is None: predictions=np.zeros(b-a)
        else:model.fit(x[:a],y[:a]);predictions=model.predict(x[a:b])
        validation[name]=float(np.mean(np.abs(y[a:b]-predictions)))
    champion=min(validation,key=validation.get)
    if champion=="no_change": calibration=np.zeros(c-b);test=np.zeros(n-c)
    else:
        def maker():
            return Ridge(alpha=1.0) if champion=="ridge" else HistGradientBoostingRegressor(max_iter=75,max_leaf_nodes=12,random_state=42)
        model=maker();model.fit(x[:b],y[:b]);calibration=model.predict(x[b:c])
        final=maker();final.fit(x[:b],y[:b]);test=final.predict(x[c:])
    residual=np.abs(y[b:c]-calibration)
    q=np.quantile(residual,min(1.0,np.ceil((len(residual)+1)*(1-alpha))/len(residual)),method="higher")
    covered=(y[c:]>=test-q)&(y[c:]<=test+q)
    return {"selected":champion,"validation_mae":validation,"calibration_size":len(residual),
        "test_size":len(y[c:]),"nominal_coverage":1-alpha,
        "holdout_coverage":float(np.mean(covered)),
        "holdout_interval_halfwidth_logreturn":float(q),
        "holdout_mae_logreturn":float(np.mean(np.abs(y[c:]-test))),
        "holdout_nochange_mae_logreturn":float(np.mean(np.abs(y[c:]))),
        "actual_misses":int((~covered).sum()),
        "coverage_target_passed":bool(np.mean(covered)>=1-alpha),
        "coverage_status":"HISTORICAL_SINGLE_SESSION_ONLY_NOT_2027_CALIBRATION",
        "features_used":["lagged_daily_returns"],"fundamentals_used":False,
        "selection_calibration_test_disjoint":True}

def run(csv,out="outputs/coverage"):
    df=load_daily(csv)
    result=assess(df.Close.to_numpy(dtype=float)*OZ_PER_KG)
    result["last_price_date"]=df.Date.iloc[-1].date().isoformat()
    path=Path(out);path.mkdir(parents=True,exist_ok=True)
    (path/"holdout_coverage.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--csv",required=True)
    p.add_argument("--out",default="outputs/coverage");a=p.parse_args()
    print(json.dumps(run(a.csv,a.out),indent=2))
if __name__=="__main__":main()
