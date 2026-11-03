"""Generate append-only shadow forecasts from the frozen V1 model artifacts.

This module NEVER scores outcomes and NEVER reads prospective approval metrics.
The 90d Ridge coefficients are frozen in config/model_artifact_v1_90d.json.
Other horizons use the locked no-change candidates selected by Nested Walk-Forward.
"""
import argparse, hashlib, json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from .daily import load_daily, OZ_PER_KG
from .point_in_time import asof_feature, load_release_csv

LAG = 20
JOURNAL_COLUMNS = [
    "created_at","origin_date","origin_close_usd_kg","horizon","target_date",
    "forecast_usd_kg","p10_usd_kg","p90_usd_kg","model","feature_group",
    "model_artifact_sha256","model_lock_sha256","status","outcome_scored",
    "previous_hash","record_hash"
]

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _canonical_hash(row):
    payload = {k: row[k] for k in JOURNAL_COLUMNS if k != "record_hash"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode()).hexdigest()

def verify_journal(frame):
    prev = "GENESIS"
    for row in frame.to_dict("records"):
        if str(row["previous_hash"]) != prev:
            raise ValueError("Shadow journal previous_hash chain is broken")
        expected = _canonical_hash({k: row[k] for k in JOURNAL_COLUMNS})
        if str(row["record_hash"]) != expected:
            raise ValueError("Shadow journal record_hash is invalid")
        prev = str(row["record_hash"])
    return prev

def _feature_frame(daily, feature_paths):
    frame = daily[["Date","Close"]].copy()
    for name, path in feature_paths.items():
        rel = load_release_csv(path)
        frame = asof_feature(frame, rel, name)
    return frame

def _latest_90d_return(frame, artifact, feature_paths):
    feature_names = artifact["input_feature_order"][LAG:]
    if feature_names != list(feature_paths.keys()):
        raise ValueError("90d feature order does not match frozen artifact")
    logp = np.log(frame.Close.to_numpy(float) * OZ_PER_KG)
    if len(logp) < LAG + 1:
        raise ValueError("Insufficient price history for frozen model")
    x = np.r_[np.diff(logp)[-LAG:], frame.iloc[-1][feature_names].to_numpy(float)].astype(float)
    med = np.asarray(artifact["imputer_statistics"], dtype=float)
    coef = np.asarray(artifact["ridge_coef"], dtype=float)
    if not (len(x) == len(med) == len(coef)):
        raise ValueError("Frozen model vector length mismatch")
    x = np.where(np.isfinite(x), x, med)
    if not np.isfinite(x).all():
        raise ValueError("Frozen imputer could not resolve all missing values")
    return float(artifact["ridge_intercept"] + np.dot(coef, x))

def _target_date(origin, horizon):
    return (pd.Timestamp(origin) + pd.offsets.BDay(int(horizon))).date().isoformat()

def generate(daily_csv, feature_paths_json, model_lock_path, artifact_path, journal_path):
    lock = _load_json(model_lock_path)
    artifact = _load_json(artifact_path)
    feature_paths = _load_json(feature_paths_json)

    if lock["protocol_id"] != "ATHMAR_PLATINUM_APPROVAL_V1":
        raise ValueError("Unexpected model lock protocol")
    locked90 = lock["horizons"]["90"]
    if locked90["model"] != artifact["model"] or locked90["group"] != artifact["feature_group"]:
        raise ValueError("Frozen artifact does not match model lock")
    if abs(float(locked90["q90_abs_logreturn"]) - float(artifact["q90_abs_logreturn"])) > 1e-12:
        raise ValueError("Frozen interval does not match model lock")

    daily = load_daily(daily_csv)
    origin = daily.Date.iloc[-1]
    origin_price = float(daily.Close.iloc[-1] * OZ_PER_KG)
    if origin.date().isoformat() < lock["lock_start"]:
        raise ValueError("Shadow forecast origin precedes prospective lock")

    frame = _feature_frame(daily, feature_paths)
    pred90 = _latest_90d_return(frame, artifact, feature_paths)
    artifact_sha = _sha(artifact_path)
    lock_sha = _sha(model_lock_path)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

    journal = Path(journal_path)
    journal.parent.mkdir(parents=True, exist_ok=True)
    if journal.is_file():
        existing = pd.read_csv(journal, dtype={"previous_hash":str,"record_hash":str})
        missing = [c for c in JOURNAL_COLUMNS if c not in existing.columns]
        if missing:
            raise ValueError(f"Shadow journal missing columns: {missing}")
        tail_hash = verify_journal(existing)
    else:
        existing = pd.DataFrame(columns=JOURNAL_COLUMNS)
        tail_hash = "GENESIS"

    existing_keys = set(zip(existing.get("origin_date",[]).astype(str), existing.get("horizon",[]).astype(str)))
    new_rows = []
    for h in ("1","5","20","60","90"):
        spec = lock["horizons"][h]
        horizon = int(h)
        pred_log_return = pred90 if horizon == 90 else 0.0
        point = origin_price * float(np.exp(pred_log_return))
        q = float(spec["q90_abs_logreturn"])
        row = {
            "created_at": created_at,
            "origin_date": origin.date().isoformat(),
            "origin_close_usd_kg": origin_price,
            "horizon": horizon,
            "target_date": _target_date(origin, horizon),
            "forecast_usd_kg": point,
            "p10_usd_kg": point * float(np.exp(-q)),
            "p90_usd_kg": point * float(np.exp(q)),
            "model": spec["model"],
            "feature_group": spec["group"],
            "model_artifact_sha256": artifact_sha if horizon == 90 else "NO_CHANGE_LOCKED_V1",
            "model_lock_sha256": lock_sha,
            "status": "shadow_locked",
            "outcome_scored": False,
            "previous_hash": tail_hash,
            "record_hash": "",
        }
        key = (row["origin_date"], str(horizon))
        if key in existing_keys:
            continue
        row["record_hash"] = _canonical_hash(row)
        tail_hash = row["record_hash"]
        new_rows.append(row)

    if new_rows:
        combined = pd.concat([existing, pd.DataFrame(new_rows, columns=JOURNAL_COLUMNS)], ignore_index=True)
        verify_journal(combined)
        combined.to_csv(journal, index=False)
    latest = new_rows if new_rows else existing.tail(5).to_dict("records")
    result = {
        "status": "APPENDED" if new_rows else "ALREADY_RECORDED",
        "origin_date": origin.date().isoformat(),
        "new_records": len(new_rows),
        "journal_records": len(existing) + len(new_rows),
        "latest": latest,
        "prospective_metrics_scored": False,
    }
    print(json.dumps(result, indent=2))
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--daily", required=True)
    p.add_argument("--features", required=True)
    p.add_argument("--model-lock", default="config/model_lock_v1.json")
    p.add_argument("--artifact", default="config/model_artifact_v1_90d.json")
    p.add_argument("--journal", default="data/shadow/forecast_journal.csv")
    a = p.parse_args()
    generate(a.daily, a.features, a.model_lock, a.artifact, a.journal)

if __name__ == "__main__":
    main()
