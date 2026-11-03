"""CFTC Tuesday positions cannot be joined until verified publication timestamps."""
import pandas as pd

def require_verified_calendar(positions,calendar):
    required={"report_date","published_at","verified_source"}
    if not required.issubset(calendar.columns): raise ValueError("Verified publication calendar missing")
    c=calendar.copy()
    c["report_date"]=pd.to_datetime(c["report_date"],utc=True)
    c["published_at"]=pd.to_datetime(c["published_at"],utc=True)
    if c["published_at"].isna().any() or c["verified_source"].isna().any(): raise ValueError("Incomplete calendar")
    if c["report_date"].duplicated().any(): raise ValueError("Duplicate CFTC publication mapping")
    p=positions.copy()
    p["report_date"]=pd.to_datetime(p["report_date"],utc=True)
    merged=p.merge(c,on="report_date",how="left",validate="many_to_one")
    if merged.published_at.isna().any(): raise ValueError("Missing verified CFTC dates")
    if (merged.published_at<merged.report_date).any(): raise ValueError("Publication before report")
    return merged
