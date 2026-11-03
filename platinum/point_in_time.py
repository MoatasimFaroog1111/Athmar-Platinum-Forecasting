"""Availability-safe fundamental observations; no invented release times."""
import pandas as pd

def validate_releases(frame):
    required={"period_end","available_at","value","source","unit"}
    if not required.issubset(frame.columns): raise ValueError("Missing release metadata")
    f=frame.copy()
    f["available_at"]=pd.to_datetime(f["available_at"],utc=True,errors="raise")
    f["period_end"]=pd.to_datetime(f["period_end"],utc=True,errors="raise")
    f["value"]=pd.to_numeric(f["value"],errors="raise")
    if f["available_at"].isna().any() or f["value"].isna().any(): raise ValueError("Incomplete releases")
    future_reference=f["available_at"]<f["period_end"]
    if future_reference.any():
        if "is_forecast" not in f.columns:
            raise ValueError("Release precedes period without forecast flag")
        flags=f["is_forecast"].astype(str).str.lower().map({"true":True,"false":False})
        flags=flags.fillna(f["is_forecast"] if f["is_forecast"].dtype==bool else False)
        if (~flags[future_reference].astype(bool)).any():
            raise ValueError("Actual observation released before period end")
    return f.sort_values("available_at")

def asof_feature(daily,releases,name):
    f=validate_releases(releases)
    d=daily.copy()
    d["Date"]=pd.to_datetime(d["Date"],utc=True)
    merged=pd.merge_asof(d.sort_values("Date"),f[["available_at","value"]],
        left_on="Date",right_on="available_at",direction="backward",allow_exact_matches=False)
    return merged.drop(columns=["available_at"]).rename(columns={"value":name})

def load_release_csv(path):
    return validate_releases(pd.read_csv(path))
