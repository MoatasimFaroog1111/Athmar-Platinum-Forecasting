"""Multi-fold walk-forward with final untouched holdout and empirical intervals.

Training is price-only until independently audited WPIC/CFTC feature joins.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from .daily import load_daily,OZ_PER_KG
from .model_competition import make_dataset

HORIZONS=(1,5,20,60,90)
def models():
    return {"ridge":Ridge(alpha=1.0),
        "forest":RandomForestRegressor(n_estimators=60,max_depth=5,min_samples_leaf=5,random_state=42,n_jobs=1),
        "boost":HistGradientBoostingRegressor(max_iter=75,max_leaf_nodes=10,random_state=42)}
def evaluate(prices,horizons=HORIZONS):
    results={}
    for h in horizons:
        X,y,_=make_dataset(prices,h)
        n=len(y); hold=int(n*.8)
        if hold<450 or n-hold<35:raise ValueError("Not enough samples for independent holdout")
        folds=[]
        for end in (int(hold*.55),int(hold*.7),int(hold*.85)):
            start=end
            stop=min(start+max(25,int(hold*.1)),hold)
            train_end=start-h
            if train_end<100 or stop-start<20:raise ValueError("Invalid purge or fold")
            folds.append((train_end,start,stop))
        scores={"no_change":[]}
        for name in models():scores[name]=[]
        for train_end,start,stop in folds:
            scores["no_change"].append(float(np.abs(y[start:stop]).mean()))
            for name,m in models().items():
                m.fit(X[:train_end],y[:train_end])
                scores[name].append(float(np.abs(y[start:stop]-m.predict(X[start:stop])).mean()))
        mean={k:float(np.mean(v)) for k,v in scores.items()}
        champion=min(mean,key=mean.get)
        final_train=hold-h
        if final_train<100:raise ValueError("Insufficient purge")
        if champion=="no_change":pred=np.zeros_like(y[hold:])
        else:
            m=models()[champion];m.fit(X[:final_train],y[:final_train]);pred=m.predict(X[hold:])
        errors=y[hold:]-pred
        baseline=np.abs(y[hold:]).mean()
        test=float(np.abs(errors).mean())
        results[str(h)]={"selected_on":"pre_holdout_3_walkforward_folds",
            "validation_mae":mean,"champion":champion,"holdout_mae":test,
            "holdout_baseline_mae":float(baseline),"holdout_size":len(errors),
            "holdout_beats_baseline":bool(test<baseline),
            "holdout_residual_q10":float(np.quantile(errors,.1)),
            "holdout_residual_q90":float(np.quantile(errors,.9)),
            "interval_status":"empirical_unvalidated_cross_horizon",
            "purge":h}
    return results

def run(csv,instrument,out="outputs/validated"):
    f=load_daily(csv)
    prices=f.Close.to_numpy(dtype=float)*OZ_PER_KG
    results=evaluate(prices)
    last=f.Date.iloc[-1]
    dates=pd.bdate_range(last+pd.Timedelta(days=1),pd.Timestamp("2027-12-31",tz="UTC"))
    # For each day, show an explicitly labeled no-change baseline. Never
    # mislabel 100+ day projections as trained, calibrated model forecasts.
    rows=[{"target_date":d.date().isoformat(),"horizon_weekdays":i,
         "price_usd_kg":float(prices[-1]),"method":"last_observed_baseline",
         "p10_usd_kg":None,"p90_usd_kg":None,
         "status":"UNVALIDATED_LONG_HORIZON"} for i,d in enumerate(dates,1)]
    # Direct forecast horizons are held at baseline until final untarnished
    # holdout verifies a model advantage; no selection on holdout.
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/"daily_2027_baseline.csv",index=False)
    report={"instrument":instrument,"forecast_unit":"USD/kg","last_real_date":last.date().isoformat(),
        "n_rows":len(f),"folded_holdout":results,"daily_rows":len(rows),
        "production_approved":False,
        "limitations":["WPIC workbook only audited raw cells; not joined as model features",
        "CFTC values ingested but publication schedule needs independent verification",
        "No trustworthy calibrated 2027 daily probability bands yet",
        "Weekdays not exchange calendar"]}
    (out/"validation_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
def main():
    p=argparse.ArgumentParser();p.add_argument("--csv",required=True);p.add_argument("--instrument",required=True)
    p.add_argument("--out",default="outputs/validated");a=p.parse_args()
    print(json.dumps(run(a.csv,a.instrument,a.out),indent=2))
if __name__=="__main__":main()
