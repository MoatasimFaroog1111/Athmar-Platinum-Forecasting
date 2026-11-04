import pandas as pd
from metals.shadow import COLUMNS,HASH_VERSION,_row_hash,_migrate_legacy,verify_journal

def _v2_row(prev="GENESIS"):
    r={
      "metal":"gold","created_at":"2026-11-04T12:00:00Z","origin_date":"2026-11-04",
      "origin_close_usd_kg":130239.45613502039,"horizon":1,"target_date":"2026-11-05",
      "forecast_usd_kg":130239.45613502039,"p10_usd_kg":126863.44536233168,
      "p90_usd_kg":133705.30719783172,"model":"no_change","feature_group":"price_only",
      "model_lock_sha256":"abc","status":"shadow_locked","outcome_scored":False,
      "hash_version":HASH_VERSION,"legacy_record_hash":"","previous_hash":prev,"record_hash":""
    }
    r["record_hash"]=_row_hash(r)
    return r

def test_v2_hash_survives_csv_roundtrip(tmp_path):
    row=_v2_row()
    path=tmp_path/"journal.csv"
    pd.DataFrame([row],columns=COLUMNS).to_csv(path,index=False)
    reread=pd.read_csv(path,dtype=str,keep_default_na=False)
    assert verify_journal(reread)==row["record_hash"]

def test_legacy_preview_migration_preserves_old_hash_reference():
    old=_v2_row()
    old_hash=old["record_hash"]
    legacy={k:v for k,v in old.items() if k not in ("hash_version","legacy_record_hash")}
    frame=pd.DataFrame([legacy])
    migrated,changed=_migrate_legacy(frame)
    assert changed is True
    assert migrated.iloc[0]["legacy_record_hash"]==old_hash
    assert migrated.iloc[0]["hash_version"]==HASH_VERSION
    verify_journal(migrated)
