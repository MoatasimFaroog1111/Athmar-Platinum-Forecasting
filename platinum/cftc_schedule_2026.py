"""Official 2026 CFTC release dates, with Eastern-time daylight saving conversion.
Source: https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm
The schedule is tentative. Verify historical publication before final training.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd

RELEASES_2026 = {
1:[5,9,16,23,30],2:[6,13,20,27],3:[6,13,20,27],4:[3,10,17,24],
5:[1,8,15,22,29],6:[5,12,22,26],7:[6,10,17,24,31],8:[7,14,21,28],
9:[4,11,18,25],10:[2,9,16,23,30],11:[6,16,20,30],12:[4,11,18,28]
}

def scheduled_releases_2026():
    tz=ZoneInfo("America/New_York")
    rows=[]
    for month, days in RELEASES_2026.items():
        for day in days:
            stamp=datetime(2026,month,day,15,30,tzinfo=tz).astimezone(timezone.utc)
            rows.append({"published_at":stamp.isoformat(),"source":"CFTC_OFFICIAL_TENTATIVE_2026_SCHEDULE"})
    return pd.DataFrame(rows).sort_values("published_at").reset_index(drop=True)

def associate_report_publication(report_dates):
    """Assign the earliest SCHEDULED release at least 3 calendar days after Tuesday.
    Exact historical release timestamps must later be confirmed; never silently
    treat a tentative date as verified historical evidence.
    """
    schedule=scheduled_releases_2026()
    result=[]
    for item in pd.to_datetime(report_dates,utc=True):
        possible=schedule[pd.to_datetime(schedule.published_at,utc=True) >= item+pd.Timedelta(days=3)]
        if item.year!=2026 or possible.empty:
            raise ValueError("No official 2026 scheduled CFTC release mapping")
        release=possible.iloc[0].published_at
        result.append(release)
    return result
