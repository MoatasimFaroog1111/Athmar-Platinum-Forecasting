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
    if (f["available_at"]<f["period_end"]).any(): raise ValueError("Release precedes period")
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
