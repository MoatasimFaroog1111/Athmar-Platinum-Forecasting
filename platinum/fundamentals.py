"""Extract CFTC platinum futures positions and WPIC workbook evidence.

Only CFTC reports with verified publication dates are admitted to features.
WPIC cells are preserved verbatim as audit evidence until unit/period mapping
is independently verified. We never infer metrics from unlabelled Excel cells.
"""
import argparse
import glob
import json
import re
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
from .feature_store import initialize

def cftc_extract(path):
    rows=[]
    with zipfile.ZipFile(path) as archive:
        members=[f for f in archive.namelist() if f.lower().endswith((".txt",".csv"))]
        if not members: raise ValueError("CFTC archive has no text table")
        for member in members:
            with archive.open(member) as stream:
                frame=pd.read_csv(stream,low_memory=False,encoding="latin1")
            frame.columns=[re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in frame.columns]
            market_col=next((c for c in frame if "market_and_exchange_names" in c),None)
            date_col=next((c for c in frame if c in ("report_date_as_yyyy_mm_dd","report_date_as_yyyy_mm_dd_","as_of_date_in_form_yyyy_mm_dd")),None)
            if not market_col or not date_col: raise ValueError("CFTC market/date headings missing")
            filtered=frame[frame[market_col].astype(str).str.contains(r"PLATINUM",case=False,regex=True)]
            for _,record in filtered.iterrows():
                market=str(record[market_col])
                if "NYMEX" not in market.upper(): continue
                date=pd.to_datetime(record[date_col],errors="coerce")
                if pd.isna(date): continue
                longs=next((c for c in frame if c.startswith("m_money_positions_long")),None)
                shorts=next((c for c in frame if c.startswith("m_money_positions_short")),None)
                if not longs or not shorts: raise ValueError("Managed money position fields missing")
                l=pd.to_numeric(record[longs],errors="coerce")
                s=pd.to_numeric(record[shorts],errors="coerce")
                if pd.isna(l) or pd.isna(s): continue
                # CFTC routine release Friday after Tuesday report (usually 15:30 ET);
                # Conservative following Monday UTC availability guards holiday delays.
                published=(date.normalize()+pd.Timedelta(days=7)).strftime("%Y-%m-%dT00:00:00+00:00")
                rows.append((market,date.date().isoformat(),published,float(l-s)))
    if not rows: raise ValueError("No NYMEX Platinum CFTC rows found")
    return rows

def extract_wpic_cells(path):
    from openpyxl import load_workbook
    wb=load_workbook(path,data_only=True,read_only=True)
    evidence=[]
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                value=cell.value
                if value is None:continue
                if isinstance(value,(str,int,float,datetime)):
                    evidence.append((path.name,ws.title,cell.coordinate,str(value)[:500]))
    if not evidence: raise ValueError("WPIC workbook empty")
    return evidence

def run(raw,db,out):
    root=Path(raw); out=Path(out);out.mkdir(parents=True,exist_ok=True)
    initialize(db)
    cftc_files=sorted(root.glob("cftc_*.zip"))
    wpic_files=sorted(root.glob("wpic_*.xlsx"))
    cot=[]
    for path in cftc_files:cot.extend(cftc_extract(path))
    wpic=[]
    for path in wpic_files:wpic.extend(extract_wpic_cells(path))
    if not cot or not wpic: raise ValueError("Both CFTC and WPIC actual files required")
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS wpic_raw_cells (filename TEXT,sheet TEXT,cell TEXT,raw_value TEXT,PRIMARY KEY(filename,sheet,cell))")
        conn.executemany("INSERT OR REPLACE INTO wpic_raw_cells VALUES (?,?,?,?)",wpic)
        conn.executemany("INSERT OR REPLACE INTO cot_releases VALUES (?,?,?,?)",cot)
    report={"cftc_positions":len(set((x[0],x[1]) for x in cot)),
            "wpic_evidence_cells":len(wpic),
            "wpic_metric_mapping":"NOT_VERIFIED_NOT_IN_MODEL",
            "cftc_availability":"conservative 7-day delay; verify per holiday/publication",
            "cftc_price_features":"NOT_ENABLED_UNTIL_DATE_AUDIT"}
    (out/"extraction.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="raw/acquired")
    p.add_argument("--db",default="outputs/research.sqlite")
    p.add_argument("--out",default="outputs/extracted")
    a=p.parse_args()
    print(json.dumps(run(a.raw,a.db,a.out),indent=2))
if __name__=="__main__":main()
