"""Stage A: audited SQLite store and strictly point-in-time joins.

Fundamentals/CFTC are optional until actually extracted, never synthesized.
"""
import sqlite3
from pathlib import Path
import pandas as pd

DDL = """
CREATE TABLE IF NOT EXISTS price_bars (
 instrument TEXT NOT NULL, date TEXT NOT NULL, close_usd_kg REAL NOT NULL CHECK(close_usd_kg>0),
 source TEXT NOT NULL, ingested_at TEXT NOT NULL, PRIMARY KEY(instrument,date,source));
CREATE TABLE IF NOT EXISTS fundamental_releases (
 source TEXT NOT NULL, metric TEXT NOT NULL, period_end TEXT NOT NULL,
 published_at TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
 PRIMARY KEY(source,metric,period_end,published_at));
CREATE TABLE IF NOT EXISTS cot_releases (
 market TEXT NOT NULL, report_date TEXT NOT NULL, published_at TEXT NOT NULL,
 net_managed_money REAL NOT NULL,
 PRIMARY KEY(market,report_date,published_at));
CREATE TABLE IF NOT EXISTS model_runs (
 run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, model TEXT NOT NULL,
 horizon INTEGER NOT NULL, metric_json TEXT NOT NULL);
"""

def initialize(db):
    p = Path(db); p.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(p) as conn:
        conn.executescript(DDL)

def ingest_prices(db, prices, instrument, source, ingested_at, unit="USD/troy_oz"):
    from .daily import load_daily, OZ_PER_KG
    frame = load_daily(prices)
    factor = OZ_PER_KG if unit == "USD/troy_oz" else 1.0
    if unit not in ("USD/troy_oz","USD/kg"):
        raise ValueError("Unknown price unit")
    initialize(db)
    with sqlite3.connect(db) as conn:
        conn.executemany("INSERT OR REPLACE INTO price_bars VALUES (?,?,?,?,?)",
            [(instrument,d.date().isoformat(),float(v)*factor,source,ingested_at)
             for d,v in zip(frame.Date,frame.Close)])
    return len(frame)

def join_as_published(prices, releases, field):
    """Release timestamps must be UTC with actual publicly available time.

    One observation per date. Never backfill future releases into prior dates.
    """
    p=prices.copy(); r=releases.copy()
    p["Date"]=pd.to_datetime(p["Date"], utc=True)
    r["published_at"]=pd.to_datetime(r["published_at"], utc=True)
    if r["published_at"].isna().any() or r[field].isna().any():
        raise ValueError("Incomplete publication metadata")
    if p.Date.duplicated().any():
        raise ValueError("Duplicate pricing dates")
    # End of daily bar UTC, deliberately conservative; embargo availability is separate.
    p["availability_at"]=p.Date+pd.Timedelta(days=1)
    r=r.sort_values("published_at")
    merged=pd.merge_asof(p.sort_values("availability_at"),r[["published_at",field]],
                        left_on="availability_at",right_on="published_at",direction="backward")
    return merged.drop(columns=["availability_at"])
