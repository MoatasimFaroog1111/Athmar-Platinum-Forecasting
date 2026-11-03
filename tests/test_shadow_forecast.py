import pandas as pd
from platinum.shadow_forecast import JOURNAL_COLUMNS,_canonical_hash,verify_journal

def _row(prev,horizon):
    r={
      "created_at":"2026-11-03T08:00:00Z","origin_date":"2026-11-02","origin_close_usd_kg":32000.0,
      "horizon":horizon,"target_date":"2026-11-10","forecast_usd_kg":32000.0,
      "p10_usd_kg":30000.0,"p90_usd_kg":34000.0,"model":"no_change","feature_group":"price_only",
      "model_artifact_sha256":"NO_CHANGE_LOCKED_V1","model_lock_sha256":"abc",
      "status":"shadow_locked","outcome_scored":False,"previous_hash":prev,"record_hash":""
    }
    r["record_hash"]=_canonical_hash(r);return r

def test_shadow_journal_hash_chain_and_no_scoring():
    a=_row("GENESIS",1);b=_row(a["record_hash"],5)
    frame=pd.DataFrame([a,b],columns=JOURNAL_COLUMNS)
    assert verify_journal(frame)==b["record_hash"]
    assert not frame["outcome_scored"].any()

def test_shadow_journal_detects_tampering():
    a=_row("GENESIS",1);a["forecast_usd_kg"]=99999.0
    frame=pd.DataFrame([a],columns=JOURNAL_COLUMNS)
    try:
        verify_journal(frame)
        assert False
    except ValueError:
        pass
