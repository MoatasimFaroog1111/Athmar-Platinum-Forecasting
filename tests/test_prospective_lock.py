from platinum.prospective_holdout import locked_status

def test_prospective_holdout_stays_locked_before_unlock(tmp_path):
    protocol=tmp_path/"p.json";model=tmp_path/"m.json"
    protocol.write_text('{"protocol_id":"x","origin_start":"2026-11-03","origin_end":"2027-07-30","score_not_before_utc":"2027-12-15T00:00:00Z"}')
    model.write_text('{"locked":true}')
    r=locked_status(protocol,model,now="2026-11-03T07:03:00")
    assert r["status"]=="LOCKED"
    assert r["metrics_revealed"] is False
