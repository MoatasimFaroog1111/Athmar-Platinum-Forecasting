import json
from pathlib import Path

NEW=("gold","silver","palladium")

def _j(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def test_new_metals_have_independent_locked_v1_protocols():
    ids=set()
    for metal in NEW:
        lock=_j(f"config/{metal}_model_lock_v1.json")
        protocol=_j(f"config/{metal}_prospective_holdout_v1.json")
        assert lock["metal"] == metal
        assert lock["protocol_id"] == protocol["protocol_id"]
        assert lock["protocol_id"] not in ids
        ids.add(lock["protocol_id"])
        assert lock["lock_start"] == protocol["origin_start"] == "2026-11-04"
        assert lock["governance"]["immutable"] is True
        assert protocol["governance"]["no_holdout_metrics_before_score_not_before"] is True
        assert protocol["source_policy"]["official_fundamentals_in_v1"] is False
        assert set(lock["horizons"]) == {"1","5","20","60","90"}

def test_target_metal_is_excluded_from_cross_market_features():
    for metal in NEW:
        lock=_j(f"config/{metal}_model_lock_v1.json")
        names=lock["feature_groups"]["market_cross"]
        assert metal not in names
        assert len(names) == len(set(names))
        assert {"dollar_index","zar_usd","us10y"} <= set(names)

def test_platinum_lock_remains_separate():
    platinum=_j("config/model_lock_v1.json")
    assert platinum["protocol_id"] == "ATHMAR_PLATINUM_APPROVAL_V1"
    for metal in NEW:
        lock=_j(f"config/{metal}_model_lock_v1.json")
        assert lock["protocol_id"] != platinum["protocol_id"]
