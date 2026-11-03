from platinum.platform_snapshot import build_snapshot

def test_platform_snapshot_does_not_reveal_prospective_metrics():
    s=build_snapshot()
    assert s["product"]["mode"]=="SHADOW"
    assert s["approval"]["status"]=="LOCKED"
    assert s["approval"]["metrics_revealed"] is False
    assert s["integrity"]["prospective_holdout_metrics_exposed"] is False
    assert {x["horizon_days"] for x in s["horizons"]}=={1,5,20,60,90}
    assert next(x for x in s["horizons"] if x["horizon_days"]==90)["model"]=="ridge_1.0"
