"""Stages B/C: leakage-aware direct-horizon benchmarks and experimental scenarios.

No calibration/production authorization is implied. Dates are weekdays only.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from .daily import load_daily, OZ_PER_KG

HORIZONS=(1,5,20,60,90)
WINDOW=20

def make_dataset(prices,horizon):
    logp=np.log(np.asarray(prices,dtype=float))
    rets=np.diff(logp)
    x=[]; y=[]; base=[]
    # at t, prior 20 log returns are observable; label close at t+h
    for t in range(WINDOW,len(logp)-horizon):
        hist=rets[t-WINDOW:t]
        x.append(np.r_[hist,hist[-5:].mean(),hist[-20:].std()])
        y.append(logp[t+horizon]-logp[t])
        base.append(t)
    if not x: raise ValueError("Insufficient observations for forecast horizon")
    return np.asarray(x),np.asarray(y),np.asarray(base)

def competition(prices, horizons=HORIZONS):
    results={}; champions={}
    for horizon in horizons:
        x,y,origins=make_dataset(prices,horizon)
        # Purged gap h separates train outcomes from test origin
        split=int(len(y)*0.8)
        train_end=split-horizon
        if train_end<150 or len(y)-split<25:
            raise ValueError("Insufficient independent chronological test observations")
        tx,ty=x[:train_end],y[:train_end]
        vx,vy=x[split:],y[split:]
        models={
            "ridge":Ridge(alpha=1.0),
            "random_forest":RandomForestRegressor(n_estimators=100,max_depth=6,min_samples_leaf=5,n_jobs=1,random_state=42),
            "hist_gradient_boost":HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,l2_regularization=2,random_state=42)
        }
        errors={"no_change":float(mean_absolute_error(vy,np.zeros_like(vy)))}
        for name,model in models.items():
            model.fit(tx,ty)
            errors[name]=float(mean_absolute_error(vy,model.predict(vx)))
        winner=min(errors,key=errors.get)
        results[str(horizon)]={"mae_log_return":errors,"best_model":winner,
          "test_size":len(vy),"purge_sessions":horizon,
          "beats_baseline":winner!="no_change"}
        champions[horizon]=winner
    return results,champions

def forecast(csv, instrument, out="outputs/multihorizon",unit="USD/troy_oz"):
    frame=load_daily(csv)
    if not instrument.strip(): raise ValueError("Explicit instrument identity required")
    if unit not in ("USD/troy_oz","USD/kg"): raise ValueError("Unsupported unit")
    prices=frame.Close.to_numpy(dtype=float)*(OZ_PER_KG if unit=="USD/troy_oz" else 1)
    scores,winners=competition(prices)
    logp=np.log(prices)
    # Only permit direct-horizon values at trained, evaluated horizons; long
    # daily path uses last-known/no-change baseline rather than recursive hallucination.
    preds={}
    for h,winner in winners.items():
        x,y,_=make_dataset(prices,h)
        if winner=="no_change": preds[h]=float(prices[-1]); continue
        model={"ridge":Ridge(alpha=1.0),
               "random_forest":RandomForestRegressor(n_estimators=100,max_depth=6,min_samples_leaf=5,n_jobs=1,random_state=42),
               "hist_gradient_boost":HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,l2_regularization=2,random_state=42)}[winner]
        model.fit(x,y)
        last_rets=np.diff(logp)[-WINDOW:]
        features=np.r_[last_rets,last_rets[-5:].mean(),last_rets.std()].reshape(1,-1)
        preds[h]=float(prices[-1]*np.exp(float(model.predict(features)[0])))
    last=frame.Date.iloc[-1]
    days=pd.bdate_range(last+pd.Timedelta(days=1),pd.Timestamp("2027-12-31",tz="UTC"))
    rows=[]
    for i,day in enumerate(days,1):
        # Exact horizons only; no false claim of a trained 400-day model
        rows.append({"forecast_created_at":pd.Timestamp.now(tz="UTC").isoformat(),
                     "target_date":day.date().isoformat(),"horizon_business_days":i,
                     "reference_instrument":instrument,"estimate_usd_kg":preds.get(i,float(prices[-1])),
                     "method":f"direct_{winners[i]}" if i in preds else "last_observed_baseline",
                     "p10_usd_kg":None,"p90_usd_kg":None,
                     "status":"EXPERIMENTAL_NOT_CALIBRATED"})
    p=Path(out); p.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(p/"daily_forecast_research.csv",index=False)
    report={"instrument":instrument,"unit":"USD/kg","last_actual_date":last.date().isoformat(),
            "data_rows":len(frame),"leaderboard":scores,"future_days":len(rows),
            "warnings":["Weekday dates are not an exchange holiday calendar.",
              "Beyond directly modeled horizons figures are last-observed-price baseline only.",
              "Models use price lags only until WPIC/CFTC are extracted and publication-joined.",
              "No calibrated prediction interval or production-grade forecast available."]}
    (p/"leaderboard.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--csv",required=True);parser.add_argument("--instrument",required=True)
    parser.add_argument("--out",default="outputs/multihorizon")
    a=parser.parse_args()
    print(json.dumps(forecast(a.csv,a.instrument,a.out),indent=2))

if __name__=="__main__": main()
